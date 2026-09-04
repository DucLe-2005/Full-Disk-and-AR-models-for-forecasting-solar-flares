from __future__ import annotations

import datetime
import logging
from pathlib import Path

from prediction.pipeline.stages.download import (
    MagnetogramNotFoundError,
    download_from_helioviewer,
    jp2_to_jpg_conversion,
)


DATA_ROOT = Path("data")
START_AT = datetime.datetime(2025, 1, 1, 0, 0, 0)
DAYS_TO_DOWNLOAD = 365
HMI_MAGNETOGRAM_SOURCE_ID = 19
logger = logging.getLogger(__name__)


def download_2025_magnetograms() -> dict[str, int]:
    """Download 365 midnight 4k HMI magnetograms for 2025 and convert them to JPG.

    Output for each date is stored in:
    data/YYYY/MM/DD/00/00/00/jp2/
    data/YYYY/MM/DD/00/00/00/jpg/
    """

    counts = {
        "downloaded_or_existing": 0,
        "converted": 0,
        "skipped_existing_jpg": 0,
        "missing": 0,
        "failed": 0,
    }

    for day_offset in range(DAYS_TO_DOWNLOAD):
        dt = START_AT + datetime.timedelta(days=day_offset)
        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        timestamp_dir = (
            DATA_ROOT
            / f"{dt.year}"
            / f"{dt.month:02d}"
            / f"{dt.day:02d}"
            / f"{dt.hour:02d}"
            / f"{dt.minute:02d}"
            / f"{dt.second:02d}"
        )
        jpg_dir = timestamp_dir / "jpg"

        try:
            jp2_path = download_from_helioviewer(
                date=dt,
                basedir=DATA_ROOT,
                include_time_components=True,
                check_existing_prediction=False,
                source_id=HMI_MAGNETOGRAM_SOURCE_ID,
            )
            counts["downloaded_or_existing"] += 1

            jpg_path = jpg_dir / f"{jp2_path.stem}.jpg"
            if jpg_path.exists():
                counts["skipped_existing_jpg"] += 1
                logger.debug("JPG already exists for %s: %s", timestamp, jpg_path)
            else:
                jp2_to_jpg_conversion(
                    jp2_path=jp2_path,
                    jpg_dir=jpg_dir,
                    resize=False,
                )
                counts["converted"] += 1
        except MagnetogramNotFoundError as exc:
            counts["missing"] += 1
            logger.warning("No magnetogram available for %s: %s", timestamp, exc)
        except Exception as exc:
            counts["failed"] += 1
            logger.exception("Failed to download or convert magnetogram for %s", timestamp)

    return counts


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    counts = download_2025_magnetograms()
    logger.info("2025 magnetogram download summary: %s", counts)


if __name__ == "__main__":
    main()
