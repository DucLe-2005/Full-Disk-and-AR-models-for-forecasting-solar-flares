from typing import Any

from pydantic import BaseModel


class CreateJobRequest(BaseModel):
    helioviewer_date: str


class CreateJobRangeRequest(BaseModel):
    start_time: str
    end_time: str


class QueuedRangeJob(BaseModel):
    job_id: str
    requested_at: str


class JobRangeResponse(BaseModel):
    status: str
    start_requested_at: str
    end_requested_at: str
    total_hours: int
    queued_count: int
    prediction_exists_count: int
    job_exists_count: int
    returned_jobs_count: int
    queued_jobs: list[QueuedRangeJob]


class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    requested_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    prediction_id: str | None = None
    error_message: str | None = None
    payload: dict[str, Any]
