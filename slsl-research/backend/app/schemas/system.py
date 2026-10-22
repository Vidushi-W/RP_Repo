from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "slsl-ai-studio-backend"


class TrainingJobSummary(BaseModel):
    id: int
    name: str
    status: str
    message: str
    updated_at: Optional[datetime] = None


class EvaluationSummary(BaseModel):
    id: int
    name: str
    status: str
    summary: str
    sequence_accuracy: Optional[float] = None
    created_at: Optional[datetime] = None


class ModelSummary(BaseModel):
    id: int
    name: str
    version: str
    status: str


class ActivityItem(BaseModel):
    id: int
    event_type: str
    message: str
    created_at: datetime


class SystemStatusResponse(BaseModel):
    backend_healthy: bool = True
    database_ready: bool = True
    dataset_count: int = 0
    model_count: int = 0
    active_model: Optional[ModelSummary] = None
    latest_training_job: Optional[TrainingJobSummary] = None
    latest_evaluation: Optional[EvaluationSummary] = None
    recent_activity: list[ActivityItem] = Field(default_factory=list)
    setup_complete: bool = False
    hardware_gloves_connected: bool = False
    features: dict[str, str] = Field(default_factory=dict)
