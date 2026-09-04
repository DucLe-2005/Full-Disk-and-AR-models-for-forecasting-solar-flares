import logging

from fastapi import FastAPI

import app.api.routers.health as health
import app.api.routers.history as history
import app.api.routers.predictions as predictions
from app.core.schema import create_database_schema
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
create_database_schema()
logger.info("Database schema is ready")

app = FastAPI(title="Solar Flare Prediction API")

app.include_router(health.router)
app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
app.include_router(history.router, prefix="/history", tags=["history"])
