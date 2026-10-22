"""MongoDB API for Component 3 kinematic practice attempts."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from pymongo import MongoClient
from pymongo.errors import PyMongoError


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "slsl_research_db").strip()
COLLECTION_NAME = "component3_kinematic_attempts"
mongo_client: MongoClient[dict[str, Any]] | None = None
if MONGODB_URI:
    mongo_client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        appname="component-3-slsl",
    )

app = FastAPI(title="Component 3 SLSL Learning API", version="0.2.0")


class AttemptMetrics(BaseModel):
    dtw_distance: float | None = Field(default=None, ge=0)
    similarity_score: float | None = Field(default=None, ge=0, le=100)
    analysis_latency_ms: float = Field(ge=0)
    ml_prediction: str | None = Field(default=None, max_length=80)
    ml_confidence: float | None = Field(default=None, ge=0, le=1)


class RemediationRecommendation(BaseModel):
    recommended_exercise: str = Field(min_length=1, max_length=160)
    trigger_reason: str = Field(min_length=1, max_length=240)


class KinematicPoseFrame(BaseModel):
    """One sampled frame of wrist-origin, unit-scale hand landmarks."""

    frame_index: int = Field(ge=0, le=119)
    hands: list[list[list[float]]] = Field(min_length=1, max_length=2)

    @field_validator("hands")
    @classmethod
    def validate_hand_landmark_shapes(cls, hands: list[list[list[float]]]):
        for hand in hands:
            if len(hand) != 21 or any(len(point) != 3 for point in hand):
                raise ValueError("Each hand must contain 21 XYZ landmarks")
            if any(not all(math.isfinite(value) for value in point) for point in hand):
                raise ValueError("Landmark coordinates must be finite")
        return hands


class KinematicObservation(BaseModel):
    """Bounded normalized pose evidence retained for diagnosed errors only."""

    feature_schema: str = Field(pattern=r"^wrist_origin_unit_scale_xyz_v1$")
    frames: list[KinematicPoseFrame] = Field(min_length=1, max_length=120)


class AttemptDocument(BaseModel):
    """The single persisted schema used by MongoDB and the local fallback."""

    user_id: str = Field(min_length=1, max_length=80)
    sign_id: str = Field(min_length=1, max_length=80)
    timestamp: str = Field(min_length=20, max_length=40)
    hands_detected: int = Field(ge=0, le=2)
    expected_hands: int | None = Field(default=None, ge=1, le=2)
    status: Literal["COMPLETED", "SKIPPED_MISSING_HAND", "INSUFFICIENT_DATA"]
    metrics: AttemptMetrics
    finger_angles: dict[str, float] = Field(default_factory=dict)
    detected_error_codes: list[str] = Field(default_factory=list, max_length=20)
    remediation_recommended: RemediationRecommendation | None = None
    kinematic_observation: KinematicObservation | None = None


def _database():
    if mongo_client is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB is not configured. Set MONGODB_URI in web/skill remediation/.env.",
        )
    try:
        mongo_client.admin.command("ping")
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="MongoDB connection failed.") from error
    return mongo_client[DATABASE_NAME]


@app.get("/health")
def health() -> dict[str, str]:
    """Report API and MongoDB availability without revealing credentials."""
    database = _database()
    return {
        "status": "ok",
        "database": database.name,
        "collection": COLLECTION_NAME,
    }


@app.post("/api/attempts", status_code=201)
def save_attempt(attempt: AttemptDocument) -> dict[str, str]:
    """Persist a scored or skipped practice attempt in the dedicated collection."""
    database = _database()
    document = attempt.model_dump()
    try:
        collection = database[COLLECTION_NAME]
        collection.create_index([("user_id", 1), ("timestamp", -1)])
        inserted = collection.insert_one(document)
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="Could not save attempt to MongoDB.") from error
    return {"id": str(inserted.inserted_id), "status": "saved"}


@app.get("/api/users/{user_id}/attempts")
def get_recent_attempts(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch newest attempts used to evaluate recurring kinematic errors."""
    if not 1 <= limit <= 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50")
    database = _database()
    try:
        records = database[COLLECTION_NAME].find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        return [
            {"id": str(record.pop("_id")), **record}
            for record in records
        ]
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="Could not load attempt history.") from error
