from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import datasets, evaluation, health, playground, system, training
from app.api.routes import settings as settings_routes
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.training_service import TrainingService

@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        TrainingService(db).mark_interrupted_jobs()
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.api_prefix
app.include_router(health.router, prefix=api)
app.include_router(system.router, prefix=api)
app.include_router(datasets.router, prefix=api)
app.include_router(training.router, prefix=api)
app.include_router(evaluation.router, prefix=api)
app.include_router(playground.router, prefix=api)
app.include_router(settings_routes.router, prefix=api)
