import datetime
from bisect import bisect_left
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMAGE_ROOT = REPOSITORY_ROOT / "data/2025"
EVENTS_PATH = REPOSITORY_ROOT / "data/events.csv"
DATASET_PATH = REPOSITORY_ROOT / "data/evaluation_2025/dataset.csv"
WINDOW = datetime.timedelta(hours=24)


def _m_x_flare_peak_times() -> list[datetime.datetime]:
    """Return full UTC peak datetimes for M/X events in ``events.csv``."""
    events = pd.read_csv(EVENTS_PATH)
    m_x_events = events[
        events["event_goes"].fillna("").str.upper().str.startswith(("M", "X"))
    ].copy()
    event_start_times = pd.to_datetime(
        m_x_events["event_start"],
        format="%Y/%m/%d %H:%M:%S",
        errors="coerce",
    )
    peak_offsets = pd.to_timedelta(m_x_events["event_peak"], errors="coerce")
    event_peak_times = event_start_times.dt.normalize() + peak_offsets
    event_peak_times = event_peak_times.where(
        event_peak_times >= event_start_times,
        event_peak_times + pd.Timedelta(days=1),
    ).dropna()
    return sorted(timestamp.to_pydatetime() for timestamp in event_peak_times)


def create_24h_labels() -> pd.DataFrame:
    """Create `dataset.csv` with labels for existing 2025 HMI JPGs.

    `true_label` is 1 when an M- or X-class flare peaks in the
    interval [magnetogram timestamp, timestamp + 24 hours), otherwise 0.
    """
    if not EVENTS_PATH.is_file():
        raise FileNotFoundError(f"Event catalog not found: {EVENTS_PATH}")

    flare_times = _m_x_flare_peak_times()
    image_paths = sorted(IMAGE_ROOT.glob("*/*/*/*/*/jpg/HMI.m*.jpg"))
    records = []

    for image_path in image_paths:
        timestamp = datetime.datetime.strptime(
            image_path.stem.removeprefix("HMI.m"),
            "%Y.%m.%d_%H.%M.%S",
        )
        next_event_index = bisect_left(flare_times, timestamp)
        has_flare = (
            next_event_index < len(flare_times)
            and flare_times[next_event_index] < timestamp + WINDOW
        )
        records.append(
            {
                "image_path": image_path.relative_to(REPOSITORY_ROOT).as_posix(),
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "true_label": int(has_flare),
            }
        )

    dataset = pd.DataFrame(records, columns=["image_path", "timestamp", "true_label"])
    dataset.sort_values("timestamp", inplace=True, ignore_index=True)
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(DATASET_PATH, index=False)
    return dataset
