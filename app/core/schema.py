from app.core.database import Base, engine
from app.models.pipeline_job import PipelineJob
from app.models.prediction import PredictionRecord


def create_database_schema() -> None:
    Base.metadata.create_all(bind=engine)
