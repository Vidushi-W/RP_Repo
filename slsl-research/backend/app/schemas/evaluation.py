from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class EvalCompatibilityPreview(BaseModel):
    model_id: int
    model_name: str
    model_version: str
    model_provenance: str
    training_dataset_id: Optional[int]
    training_dataset_version: Optional[str]
    dataset_id: int
    dataset_name: str
    dataset_version: str
    dataset_provenance: str
    split: str
    split_counts: dict[str, int]
    recommended_split: str
    compatible: bool
    schema_compatible: bool
    vocabulary_warnings: list[str]
    signer_analysis: dict[str, Any]
    warnings: list[str]


class StartEvaluationRequest(BaseModel):
    model_id: int
    dataset_id: int
    split: str = Field(default="test", pattern="^(test|val|train)$")
    name: str = "Evaluation Run"
    uncertainty_threshold: float = Field(default=0.25, ge=0.0, le=1.0)


class EvaluationRunResponse(BaseModel):
    id: int
    name: str
    status: str
    model_id: Optional[int]
    dataset_id: Optional[int]
    dataset_version: Optional[str]
    split_used: str
    provenance: str
    summary: str
    message: str
    sequence_accuracy: Optional[float]
    word_error_rate: Optional[float]
    metrics: dict[str, Any]
    config: dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime]


class EvaluationResultsResponse(BaseModel):
    run: EvaluationRunResponse
    aggregate: dict[str, Any]
    emotion: dict[str, Any]
    predictions: list[dict[str, Any]]
    limitations: list[str]


class CompareEvaluationsResponse(BaseModel):
    runs: list[EvaluationRunResponse]
    comparison: dict[str, Any]
