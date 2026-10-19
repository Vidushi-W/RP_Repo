from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import datasets, health, system
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
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
