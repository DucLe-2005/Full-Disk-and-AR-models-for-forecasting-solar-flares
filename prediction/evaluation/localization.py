"""Compare flare-event active-region positions with proposed hulls."""

from __future__ import annotations

import datetime
import math
import re
from bisect import bisect_left
from pathlib import Path

import cv2 as cv
import numpy as np
import pandas as pd
from PIL import Image

from prediction.pipeline.stages.region_proposal import apply_full_disk_contour, draw_hulls


EVENT_POSITION_PATTERN = re.compile(
    r"^(?P<latitude_hemisphere>[NS])(?P<latitude>\d{1,2})"
    r"(?P<longitude_hemisphere>[EW])(?P<longitude>\d{1,2})"
    r"\(\s*(?P<active_region>\d+)\s*\)$"
)
IMAGE_SIZE = 512
CDELT = 0.600000023842
HPCCENTER = 4096.0 / 2.0
DOWNSAMPLE_FACTOR = 8.0
RSUN_METERS = 696000000.0
DSUN_METERS = 149597870691.0
EVENT_WINDOW = datetime.timedelta(hours=24)


def parse_event_position(value: str) -> dict | None:
    """Parse a GOES location such as ``S22E79( 4405 )``."""
    match = EVENT_POSITION_PATTERN.fullmatch(str(value).strip())
    if match is None:
        return None

    latitude = float(match["latitude"])
    longitude = float(match["longitude"])
    if match["latitude_hemisphere"] == "S":
        latitude *= -1
    if match["longitude_hemisphere"] == "E":
        longitude *= -1

    return {
        "ar_number": f"AR{match['active_region']}",
        "longitude_deg": longitude,
        "latitude_deg": latitude,
    }


def convert_hg_hcc(hglon_deg: float, hglat_deg: float) -> tuple[float, float]:
    """Convert heliographic longitude/latitude to heliocentric Cartesian x/y."""
    b0_deg = 0.0
    l0_deg = 0.0
    longitude = math.radians(hglon_deg - l0_deg)
    latitude = math.radians(hglat_deg)
    cos_b0 = math.cos(math.radians(b0_deg))
    sin_b0 = math.sin(math.radians(b0_deg))

    x = RSUN_METERS * math.cos(latitude) * math.sin(longitude)
    y = RSUN_METERS * (
        math.sin(latitude) * cos_b0
        - math.cos(latitude) * math.cos(longitude) * sin_b0
    )
    return x, y


def convert_hcc_hpc(x: float, y: float) -> tuple[float, float]:
    """Convert heliocentric Cartesian x/y to helioprojective arcseconds."""
    z_squared = RSUN_METERS**2 - x**2 - y**2
    z = math.sqrt(z_squared) if z_squared >= 0 else 0.0
    zeta = DSUN_METERS - z
    distance = math.sqrt(x**2 + y**2 + zeta**2)
    hpc_x = math.degrees(math.atan2(x, zeta)) * 3600
    hpc_y = math.degrees(math.asin(y / distance)) * 3600
    return hpc_x, hpc_y


def convert_hgs_to_pixels(
    longitude_deg: float,
    latitude_deg: float,
) -> tuple[int, int]:
    """Use the original HGS -> HCC -> HPC -> 512px conversion."""
    hcc_x, hcc_y = convert_hg_hcc(longitude_deg, latitude_deg)
    hpc_x, hpc_y = convert_hcc_hpc(hcc_x, hcc_y)
    pixel_x = HPCCENTER + hpc_x / CDELT
    pixel_y = HPCCENTER - hpc_y / CDELT
    return int(pixel_x / DOWNSAMPLE_FACTOR), int(pixel_y / DOWNSAMPLE_FACTOR)


def prepare_event_regions(events: pd.DataFrame) -> pd.DataFrame:
    """Parse event timestamps and positions, retaining valid active regions only."""
    prepared = events.copy()
    prepared["event_start"] = pd.to_datetime(
        prepared["event_start"],
        format="%Y/%m/%d %H:%M:%S",
        errors="coerce",
    )
    parsed_positions = prepared["event_position"].map(parse_event_position)
    valid = prepared["event_start"].notna() & parsed_positions.notna()
    prepared = prepared.loc[valid].copy()
    parsed_positions = parsed_positions.loc[valid]

    parsed_frame = pd.DataFrame(parsed_positions.tolist(), index=prepared.index)
    prepared = prepared.join(parsed_frame)
    return prepared.sort_values("event_start", ignore_index=True)


def prepare_2025_mx_event_regions(events: pd.DataFrame) -> pd.DataFrame:
    """Filter the catalog to 2025 M/X events, then parse their AR locations."""
    m_x_events = events.loc[
        events["event_start"].str.startswith("2025/", na=False)
        & events["event_goes"].str.match(r"^[MX]", na=False)
    ].copy()
    return prepare_event_regions(m_x_events)


def active_regions_in_window(
    events: pd.DataFrame,
    timestamp: datetime.datetime,
) -> list[dict]:
    """Return one event position per active region in the next 24 hours."""
    event_times = events["event_start"].tolist()
    start_index = bisect_left(event_times, timestamp)
    end_index = bisect_left(event_times, timestamp + EVENT_WINDOW)
    window_events = events.iloc[start_index:end_index]
    return window_events.drop_duplicates("ar_number", keep="first").to_dict("records")


def active_region_hull_distances(
    ar_points: list[tuple[str, tuple[int, int]]],
    hulls: list[tuple[int, np.ndarray]],
) -> list[tuple[str, int | None, float, bool]]:
    """Return the nearest proposal distance for every actual active region."""
    if not ar_points:
        return []
    if not hulls:
        return [(ar_name, None, np.nan, False) for ar_name, _ in ar_points]

    results = []
    for ar_name, ar_point in ar_points:
        distances = []
        for hull_id, hull_points in hulls:
            signed_distance = cv.pointPolygonTest(
                np.asarray(hull_points, dtype=np.float32),
                (float(ar_point[0]), float(ar_point[1])),
                measureDist=True,
            )
            distances.append((hull_id, max(0.0, -signed_distance)))

        closest_hull_id, distance = min(distances, key=lambda item: item[1])
        results.append((ar_name, closest_hull_id, distance, distance == 0.0))
    return results


def proximity_score(distances: list[tuple[str, int | None, float, bool]]) -> float:
    """Mean nearest-proposal distance in pixels. Lower is better."""
    values = [row[2] for row in distances if not np.isnan(row[2])]
    return round(float(np.mean(values)), 2) if values else np.nan


def collocation_ratio(distances: list[tuple[str, int | None, float, bool]]) -> float:
    """Fraction of actual active regions covered by at least one proposal."""
    if not distances:
        return np.nan
    return round(sum(row[3] for row in distances) / len(distances), 2)


def project_actual_regions(
    timestamp: datetime.datetime,
    actual_regions: list[dict],
) -> pd.DataFrame:
    """Project cataloged active-region locations into 512px image coordinates."""
    actual_details = pd.DataFrame(actual_regions).copy()
    if actual_details.empty:
        return actual_details

    actual_details[["pixel_x", "pixel_y"]] = actual_details.apply(
        lambda row: convert_hgs_to_pixels(
            row["longitude_deg"],
            row["latitude_deg"],
        ),
        axis=1,
        result_type="expand",
    )
    return actual_details


def proposed_region_true_labels(
    proposed_regions: list[dict],
    actual_details: pd.DataFrame,
) -> dict[int, int]:
    """Label a proposal positive when it contains an actual M/X active region."""
    labels = {}
    for region in proposed_regions:
        polygon = np.asarray(region["polygon_resized_xy"], dtype=np.float32)
        labels[region["region_rank"]] = int(any(
            cv.pointPolygonTest(
                polygon,
                (float(row.pixel_x), float(row.pixel_y)),
                measureDist=False,
            ) >= 0
            for row in actual_details.itertuples(index=False)
        ))
    return labels


def mark_actual_region_matches(
    actual_details: pd.DataFrame,
    proposed_regions: list[dict],
) -> pd.DataFrame:
    """Mark actual regions that are inside at least one proposal polygon."""
    details = actual_details.copy()
    if details.empty:
        return details

    details["matched"] = [
        any(
            cv.pointPolygonTest(
                np.asarray(region["polygon_resized_xy"], dtype=np.float32),
                (float(row.pixel_x), float(row.pixel_y)),
                measureDist=False,
            ) >= 0
            for region in proposed_regions
        )
        for row in details.itertuples(index=False)
    ]
    return details


def save_localization_overlay(
    image_path: str,
    proposed_regions: list[dict],
    details: pd.DataFrame,
    output_path: str,
) -> None:
    """Save the final-hulls image with actual active-region points added."""
    with Image.open(image_path) as image:
        image_array = np.asarray(image.convert("L"))
    original_resized = cv.resize(
        image_array,
        (IMAGE_SIZE, IMAGE_SIZE),
        interpolation=cv.INTER_AREA,
    )
    final_hulls = draw_hulls(
        hulls=[region["polygon_resized_xy"] for region in proposed_regions],
        image_shape=(IMAGE_SIZE, IMAGE_SIZE),
        draw_ids=True,
    )
    final_hulls = apply_full_disk_contour(
        original_hmi=original_resized,
        region_image=final_hulls,
    )
    overlay = cv.cvtColor(final_hulls, cv.COLOR_GRAY2BGR)

    for row in details.itertuples(index=False):
        point = (int(row.pixel_x), int(row.pixel_y))
        if 0 <= point[0] < IMAGE_SIZE and 0 <= point[1] < IMAGE_SIZE:
            color = (0, 255, 0) if row.matched else (0, 0, 255)
            cv.circle(overlay, point, 5, color, thickness=-1)
            cv.putText(
                overlay,
                row.ar_number,
                (point[0] + 7, point[1] - 7),
                cv.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv.LINE_AA,
            )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv.cvtColor(overlay, cv.COLOR_BGR2RGB)).save(destination)


def evaluate_magnetogram(
    timestamp: datetime.datetime,
    actual_regions: list[dict],
    proposed_regions: list[dict],
) -> tuple[dict, pd.DataFrame]:
    """Evaluate proposal coverage for one magnetogram."""
    actual_details = project_actual_regions(timestamp, actual_regions)
    ar_points = [
        (region["ar_number"], (region["pixel_x"], region["pixel_y"]))
        for region in actual_details.to_dict("records")
    ]
    hulls = [
        (region["region_rank"], np.asarray(region["polygon_resized_xy"]))
        for region in proposed_regions
    ]
    distances = active_region_hull_distances(ar_points, hulls)
    details = pd.DataFrame(
        distances,
        columns=["ar_number", "closest_proposal", "distance_pixels", "matched"],
    )
    if not details.empty:
        details = details.merge(
            actual_details[
                [
                    "ar_number",
                    "event_id",
                    "event_start",
                    "event_goes",
                    "event_position",
                    "pixel_x",
                    "pixel_y",
                ]
            ],
            on="ar_number",
            how="left",
        )
        details.insert(0, "timestamp", timestamp.strftime("%Y-%m-%d %H:%M:%S"))

    matched_count = sum(row[3] for row in distances)
    return {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "num_actual_ars": len(actual_regions),
        "num_proposals": len(proposed_regions),
        "num_matched_ars": matched_count,
        "proximity_score": proximity_score(distances),
        "collocation_ratio": collocation_ratio(distances),
    }, details
