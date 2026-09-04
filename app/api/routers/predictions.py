from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.job import CreateJobRangeRequest, CreateJobRequest, JobRangeResponse, JobResponse
from app.core.dependencies import get_job_service
from app.services.job_service import JobService

router = APIRouter()


@router.post("/jobs")
def create_job(
    request: CreateJobRequest,
    service: JobService = Depends(get_job_service),
):
    try:
        result = service.create_job(payload=request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job = result["job"]
    if job is None:
        return {
            "status": result["status"],
            "prediction_id": result["prediction_id"],
            "requested_at": result["requested_at"],
        }

    return {
        "job_id": job.id,
        "status": result["status"],
        "job_status": job.status.value,
        "created_at": job.created_at,
        "requested_at": result["requested_at"],
        "payload": job.payload,
    }


@router.post("/jobs/range", response_model=JobRangeResponse)
def create_jobs_for_range(
    request: CreateJobRangeRequest,
    service: JobService = Depends(get_job_service),
) -> JobRangeResponse:
    try:
        result = service.create_jobs_for_range(payload=request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
