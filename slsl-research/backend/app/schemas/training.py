from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TrainingPreview(BaseModel):
    dataset_id: int
    dataset_name: str
    provenance: str
    dataset_version: str
    train_count: int
    val_count: int
    test_count: int
    vocabulary_size: int
    schema_compatible: bool
    warnings: list[str]
    estimated_params: int


class StartTrainingRequest(BaseModel):
    dataset_id: int
    name: str = "New Training Run"
    training_mode: str = "fresh"
    source_model_id: Optional[int] = None
    epochs: int = Field(default=20, ge=1, le=100)
    batch_size: int = Field(default=4, ge=1, le=16)
    learning_rate: float = Field(default=0.001, gt=0)
    cnn_channels: int = Field(default=32)
    hidden_size: int = Field(default=32)
    model_name: str = "SLSL CTC Model"


class TrainingJobResponse(BaseModel):
    id: int
    name: str
    status: str
    dataset_id: Optional[int]
    model_id: Optional[int]
    training_mode: str
    current_epoch: int
    total_epochs: int
    train_loss: Optional[float]
    val_loss: Optional[float]
    val_wer: Optional[float]
    message: str
    pid: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    config: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    id: int
    name: str
    version: str
    status: str
    architecture: str
    dataset_id: Optional[int]
    dataset_version: Optional[str]
    provenance: str
    training_job_id: Optional[int]
    validation_metrics: dict[str, Any] = Field(default_factory=dict)
    vocabulary: list[str] = Field(default_factory=list)
    emotion_available: bool
    is_archived: bool
    created_at: datetime
    notes: str = ""


class ResetPreviewRequest(BaseModel):
    archive_models: bool = True
    clear_jobs: bool = True
    remove_synthetic_datasets: bool = False
    delete_checkpoints: bool = False


class ResetExecuteRequest(ResetPreviewRequest):
    confirmation: str
    confirmation_delete: str = ""
