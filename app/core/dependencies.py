from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.api.repositories.job_repository import JobRepository
from app.api.repositories.prediction_repository import PredictionRepository
from app.services.job_service import JobService
from app.services.prediction_service import PredictionService


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(JobRepository(db), PredictionRepository(db))


def get_prediction_service(db: Session = Depends(get_db)) -> PredictionService:
    return PredictionService(PredictionRepository(db))
