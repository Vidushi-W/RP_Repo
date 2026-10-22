from typing import Any, Optional

from pydantic import BaseModel, Field


class PlaygroundStatus(BaseModel):
    active_model: Optional[dict[str, Any]] = None
    hardware_connected: bool = False
    hardware_message: str = ""


class RecognitionMessage(BaseModel):
    filename: str
    validation: dict[str, Any]
    english: str
    gloss_sequence: list[str]
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None
    emotion_source: str = ""
    emotion_message: str = ""
    decoder_score: float
    decoder_score_label: str
    uncertain: bool
    sentence_status: str
    sentence_message: str
    model_id: int
    model_name: str
    model_version: str
    inference_ms: float
    timestamp: float
    feedback: Optional[dict[str, Any]] = None
    no_ground_truth_used: bool = True


class DictionaryResponse(BaseModel):
    model_id: int
    model_name: str
    model_version: str
    provenance: str
    entries: list[dict[str, Any]]
    sentence_patterns: list[dict[str, Any]]
    disclaimer: str


class LiveSessionCreate(BaseModel):
    source_type: str = Field(default="csv_playback", pattern="^(csv_playback|hardware_gloves)$")


class LiveSessionResponse(BaseModel):
    session_id: str
    source_type: str
    status: str = "idle"


class LiveSpeedRequest(BaseModel):
    speed: float = Field(ge=0.25, le=4.0)


class LiveFinalizeResponse(BaseModel):
    message: dict[str, Any]
