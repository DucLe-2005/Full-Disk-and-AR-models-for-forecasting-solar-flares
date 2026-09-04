from __future__ import annotations

import argparse
from datetime import datetime
import logging

from app.core.logging import configure_logging

DEFAULT_START_TIME = "2020-01-01 00:00:00"
DEFAULT_END_TIME = "2025-12-31 23:00:00"
logger = logging.getLogger(__name__)


def _parse_time(value: str, *, end_of_day: bool = False) -> datetime:
    normalized = value.strip().replace("T", " ").replace("Z", "")
    if len(normalized) == 10:
        hour = "23" if end_of_day else "00"
        normalized = f"{normalized} {hour}:00:00"
    if len(normalized) == 16:
        normalized = f"{normalized}:00"

    return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S").replace(
        minute=0,
        second=0,
        microsecond=0,
    )


def _format_time(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def queue_backfill_jobs(start_time: str, end_time: str) -> dict:
    from app.api.repositories.job_repository import JobRepository
    from app.api.repositories.prediction_repository import PredictionRepository
    from app.core.database import SessionLocal
    from app.services.job_service import JobService

    start_at = _parse_time(start_time)
    end_at = _parse_time(end_time, end_of_day=True)

    db = SessionLocal()
    try:
        service = JobService(
            job_repo=JobRepository(db),
            prediction_repo=PredictionRepository(db),
        )
        return service.create_jobs_for_range(
            payload={
                "start_time": _format_time(start_at),
                "end_time": _format_time(end_at),
            }
        )
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Queue hourly prediction jobs for a historical date range. "
            "The worker service will process the queued jobs normally."
        )
    )
    parser.add_argument(
        "--start-time",
        default=DEFAULT_START_TIME,
        help=f"Backfill start time. Defaults to {DEFAULT_START_TIME}.",
    )
    parser.add_argument(
        "--end-time",
        default=DEFAULT_END_TIME,
        help=f"Backfill end time. Defaults to {DEFAULT_END_TIME}.",
    )
    return parser


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()

    from app.core.schema import create_database_schema

    create_database_schema()
    result = queue_backfill_jobs(args.start_time, args.end_time)

    logger.info(
        "Backfill queue complete: status=%s range=%s to %s total_hours=%s queued=%s "
        "predictions_skipped=%s jobs_skipped=%s",
        result["status"], result["start_requested_at"], result["end_requested_at"],
        result["total_hours"], result["queued_count"], result["prediction_exists_count"],
        result["job_exists_count"],
    )


if __name__ == "__main__":
    main()
