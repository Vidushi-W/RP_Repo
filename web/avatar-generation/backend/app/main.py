"""LankaSigns API scaffold. No inference, upload, or generation endpoints."""
from fastapi import FastAPI
from app.api.routes import router
app = FastAPI(title="LankaSigns Avatar Research API", version="0.1.0")
app.include_router(router, prefix="/api")
