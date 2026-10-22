"""LankaSigns health and registry-constrained semantic animation selection API."""
from fastapi import FastAPI
from app.api.routes import router
from app.api.semantic_routes import router as semantic_router
from app.api.audio_routes import router as audio_router
app = FastAPI(title="LankaSigns Avatar Research API", version="0.1.0")
app.include_router(router, prefix="/api")
app.include_router(semantic_router, prefix="/api")
app.include_router(audio_router, prefix="/api")
