from datetime import datetime, timedelta

from app.api.repositories.job_repository import JobRepository
from app.api.schemas.job import JobResponse
from app.api.repositories.prediction_repository import PredictionRepository
from app.models.pipeline_job import PipelineJob


class JobService:
    RANGE_RETURN_LIMIT = 100

    def __init__(self, job_repo: JobRepository, prediction_repo: PredictionRepository):
        self.job_repo = job_repo
        self.prediction_repo = prediction_repo

    def create_job(self, payload: dict | None = None) -> dict:
        payload = payload or {}
        requested_at = self._parse_requested_at(payload)
        requested_at = self.prediction_repo.normalize_requested_at(requested_at)
        normalized_payload = {
            **payload,
            "helioviewer_date": self._format_requested_at(requested_at),
        }

        existing_prediction = self.prediction_repo.get_for_requested_at(requested_at)
        if existing_prediction is not None:
            return {
                "status": "prediction_exists",
                "prediction_id": existing_prediction.id,
                "requested_at": requested_at,
                "job": None,
            }

        active_job = self.job_repo.get_active_job_for_requested_at(requested_at)
        if active_job is not None:
            return {
                "status": "job_exists",
                "prediction_id": None,
                "requested_at": requested_at,
                "job": active_job,
            }

        job = self.job_repo.create_job(
            payload=normalized_payload,
            requested_at=requested_at,
        )
        return {
            "status": "queued",
            "prediction_id": None,
            "requested_at": requested_at,
            "job": job,
        }

    def create_jobs_for_range(self, payload: dict | None = None) -> dict:
        payload = payload or {}
        start_datetime = self._parse_datetime_value(payload.get("start_time"), "start_time")
        end_datetime = self._parse_datetime_value(payload.get("end_time"), "end_time")

        start_at = self.prediction_repo.normalize_requested_at(start_datetime)
        end_at = self.prediction_repo.normalize_requested_at(end_datetime)
        if end_at < start_at:
            raise ValueError("end_time must be greater than or equal to start_time")

        requested_times = self._iter_hours(start_at, end_at)
        existing_requested_times = self.prediction_repo.list_requested_at_between(
            start_at,
            end_at,
        )
        active_job_requested_times = self.job_repo.list_active_job_requested_at_between(
            start_at,
            end_at,
        )

        job_payloads: list[tuple[dict, datetime]] = []
        for requested_at in requested_times:
            if requested_at in existing_requested_times:
                continue
            if requested_at in active_job_requested_times:
                continue
            job_payloads.append(
                (
                    {
                        "helioviewer_date": self._format_requested_at(requested_at),
                        "range_start_time": self._format_requested_at(start_at),
                        "range_end_time": self._format_requested_at(end_at),
                        "request_type": "range_backfill",
                    },
                    requested_at,
                )
            )

        queued_jobs = self.job_repo.create_jobs(job_payloads) if job_payloads else []
        returned_jobs = queued_jobs[: self.RANGE_RETURN_LIMIT]

        return {
            "status": "queued" if queued_jobs else "already_covered",
            "start_requested_at": self._format_requested_at(start_at),
            "end_requested_at": self._format_requested_at(end_at),
            "total_hours": len(requested_times),
            "queued_count": len(queued_jobs),
            "prediction_exists_count": len(existing_requested_times),
            "job_exists_count": len(active_job_requested_times - existing_requested_times),
            "returned_jobs_count": len(returned_jobs),
            "queued_jobs": [
                {
                    "job_id": job.id,
                    "requested_at": self._format_requested_at(job.requested_at),
                }
                for job in returned_jobs
                if job.requested_at is not None
            ],
        }

    def get_job(self, job_id: str) -> JobResponse | None:
        job = self.job_repo.get_job(job_id)
        if job is None:
            return None
        return self._to_response(job)

    def _to_response(self, job: PipelineJob) -> JobResponse:
        return JobResponse(
            job_id=job.id,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            requested_at=(
                job.requested_at.isoformat()
                if job.requested_at is not None
                else None
            ),
            started_at=job.started_at.isoformat() if job.started_at is not None else None,
            finished_at=job.finished_at.isoformat() if job.finished_at is not None else None,
            prediction_id=job.prediction_id,
            error_message=job.error_message,
            payload=job.payload,
        )

    def _parse_requested_at(self, payload: dict) -> datetime:
        helioviewer_date = payload.get("helioviewer_date")
        return self._parse_datetime_value(helioviewer_date, "helioviewer_date")

    def _parse_datetime_value(self, value: object, field_name: str) -> datetime:
        if not value:
            raise ValueError(f"{field_name} is required")
        return datetime.strptime(
            str(value).strip().replace("T", " ").replace("Z", ""),
            "%Y-%m-%d %H:%M:%S",
        )

    def _iter_hours(self, start_hour: datetime, end_hour: datetime) -> list[datetime]:
        hours: list[datetime] = []
        current = start_hour
        while current <= end_hour:
            hours.append(current)
            current += timedelta(hours=1)
        return hours

    def _format_requested_at(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
