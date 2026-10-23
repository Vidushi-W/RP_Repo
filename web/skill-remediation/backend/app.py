"""MongoDB API for Component 3 kinematic practice attempts."""

from __future__ import annotations

import math
import os
import base64
import binascii
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import cv2
import mediapipe as mp
import numpy as np

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, PyMongoError
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from backend.attempt_store import AttemptStore
from backend.extract_references import _recover_two_crop_hands
from backend.metrics import compare_pose_sequences
from backend.ml_classifier import load_error_classifier, predict_sequence
from backend.normalization import normalize_landmarks
from backend.remediation_engine import recommend_from_history
from backend.reference_loader import load_reference_sequences


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "slsl_research_db").strip()
COLLECTION_NAME = "component3_kinematic_attempts"
mongo_client: MongoClient[dict[str, Any]] | None = None
MONGODB_INIT_FAILED = False
if MONGODB_URI:
    try:
        mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            appname="component-3-slsl",
        )
    except (PyMongoError, ConfigurationError):
        # An Atlas SRV URI may fail during DNS resolution before the API starts.
        # The web app can still run using its local SQLite attempt store.
        MONGODB_INIT_FAILED = True
        print("MongoDB could not be initialized (network/DNS unavailable); local SQLite fallback remains available.")

app = FastAPI(title="Component 3 SLSL Learning API", version="0.2.0")
WEB_DIR = ROOT / "frontend" / "web"
REFERENCE_DIR = ROOT / "references"
MODEL_PATH = ROOT / "kinematic_error_classifier.pkl"
HAND_MODEL_PATH = ROOT / "hand_landmarker.task"
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="learning-assets")


@app.get("/", include_in_schema=False)
def learning_page():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/lesson")
def get_lesson():
    references = load_reference_sequences()
    requirements_path = REFERENCE_DIR / "sign_requirements.json"
    requirements = json.loads(requirements_path.read_text(encoding="utf-8")) if requirements_path.exists() else {}
    signs = []
    for sign_id in sorted(references):
        folder = REFERENCE_DIR / sign_id
        sources = sorted(
            (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".avi"}),
            key=lambda path: (0 if path.suffix.lower() in {".mp4", ".mov", ".avi"} else 1, path.name.lower()),
        ) if folder.exists() else []
        expected_hands = requirements.get(sign_id, {}).get("expected_hands", len(references[sign_id][0][0]))
        signs.append({
            "id": sign_id,
            "word": sign_id.replace("-sign", "").replace("-", " ").upper(),
            "hands": int(expected_hands),
            "media_url": f"/api/references/{sign_id}" if sources else None,
            "media_type": "video" if sources and sources[0].suffix.lower() in {".mp4", ".mov", ".avi"} else "image",
            "has_reference": bool(sources),
        })
    if not signs:
        raise HTTPException(status_code=503, detail="No processed sign references are available.")
    try:
        classifier = load_error_classifier(MODEL_PATH)
    except (OSError, ValueError, RuntimeError):
        classifier = None
    user_id = os.getenv("SLSL_USER_ID", "student_01").strip() or "student_01"
    return {"signs": signs, "ml_enabled": classifier is not None, "ml_signs": classifier.get("sign_ids", []) if classifier else [], "user_id": user_id}


@app.get("/api/references/{sign_id}")
def get_reference_media(sign_id: str):
    if not sign_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid sign id")
    folder = REFERENCE_DIR / sign_id
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail="Reference media not found")
    sources = sorted(
        (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".avi"}),
        key=lambda path: (0 if path.suffix.lower() in {".mp4", ".mov", ".avi"} else 1, path.name.lower()),
    )
    if not sources:
        raise HTTPException(status_code=404, detail="No source demonstration is available")
    return FileResponse(sources[0])


class BrowserAnalysisRequest(BaseModel):
    sign_id: str = Field(min_length=1, max_length=80)
    user_id: str = Field(default="student_01", min_length=1, max_length=80)
    frames: list[str] = Field(min_length=5, max_length=60)

    @field_validator("frames")
    @classmethod
    def validate_frame_payloads(cls, frames: list[str]):
        if any(len(frame) > 350_000 for frame in frames):
            raise ValueError("Each camera sample must be 350 KB or smaller")
        return frames


def _browser_feedback(label: str | None) -> str:
    messages = {
        "NORMAL": "No trained hand-position error was detected. Keep practicing the reference sign!",
        "ERR_PINKY_FLEX": "Your little finger may need a small adjustment. Watch the example and try again.",
        "ERR_INDEX_EXT": "Check your index finger position against the example, then try again.",
        "ERR_WRIST_ROTATION": "Try turning your hand a little to match the example.",
        "UNSUPPORTED_SIGN": "Your sign was compared with the reference. Keep practicing and try again!",
        "NO_SINGLE_HAND_DATA": "Keep one hand clearly visible in the camera while you sign.",
    }
    return messages.get(label or "", "Your attempt was compared with the reference. You can try again whenever you like.")


@app.post("/api/analyze")
def analyze_browser_attempt(request: BrowserAnalysisRequest):
    started = time.perf_counter()
    references = load_reference_sequences()
    if request.sign_id not in references:
        raise HTTPException(status_code=404, detail="This sign does not have a processed reference.")
    required_hands = len(references[request.sign_id][0][0])
    if not HAND_MODEL_PATH.exists():
        raise HTTPException(status_code=503, detail="The hand tracking model is missing. See the setup guide.")

    image_frames = []
    for encoded in request.frames:
        try:
            image_data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise HTTPException(status_code=422, detail="A camera sample could not be decoded.") from error
        image = cv2.imdecode(np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=422, detail="A camera sample is not a valid image.")
        image_frames.append(image)

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.15,
        min_hand_presence_confidence=0.15,
        min_tracking_confidence=0.15,
    )
    live_frames = []
    with vision.HandLandmarker.create_from_options(options) as detector:
        for frame_index, bgr in enumerate(image_frames):
            timestamp_ms = (frame_index + 1) * 200
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            detection = detector.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms
            )
            detected_hands = list(detection.hand_landmarks or [])
            if required_hands == 2 and len(detected_hands) < 2:
                detected_hands = _recover_two_crop_hands(
                    bgr, detector, timestamp_ms + 1, full_frame_hands=detected_hands
                )
            hands = []
            if len(detected_hands) == required_hands:
                for hand in detected_hands:
                    points = np.asarray([[point.x, point.y, point.z] for point in hand], dtype=np.float32)
                    hands.append(normalize_landmarks(points))
            live_frames.append(np.stack(hands) if hands else np.empty((0, 21, 3), dtype=np.float32))

    count_distribution = Counter(len(frame) for frame in live_frames)
    visible_counts = Counter({count: amount for count, amount in count_distribution.items() if count > 0})
    expected_frames = [frame for frame in live_frames if len(frame) == required_hands]
    if len(expected_frames) >= 5:
        # Ignore empty and partial detections if enough frames contain the
        # reference's required number of hands to score the attempt.
        dominant_hands = required_hands
        consistent_frames = expected_frames
    elif visible_counts:
        dominant_hands = max(visible_counts, key=lambda count: (visible_counts[count], count))
        consistent_frames = [frame for frame in live_frames if len(frame) == dominant_hands]
        expected_count = len(expected_frames)
        if dominant_hands != required_hands:
            visibility_tip = (
                "Keep both hands inside the camera view, apart enough to distinguish, and try again."
                if required_hands == 2
                else "Keep one hand inside the camera view and try again."
            )
            message = (
                f"I could see {dominant_hands} hand(s) in {len(consistent_frames)} of {len(live_frames)} samples; "
                f"this example needs {required_hands}. {visibility_tip}"
            )
            return {"status": "HAND_COUNT_MISMATCH", "message": message, "hands_detected": dominant_hands, "expected_hands": required_hands, "expected_hand_samples": expected_count, "sample_count": len(live_frames)}
        message = (
            f"I detected the required {required_hands} hands in only {expected_count} of {len(live_frames)} samples. "
            "Hold the sign clearly in view for the whole capture, then try again."
        )
        return {"status": "INSUFFICIENT_DATA", "message": message, "hands_detected": dominant_hands, "expected_hands": required_hands, "expected_hand_samples": expected_count, "sample_count": len(live_frames)}
    else:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "I couldn't detect any hands in the camera samples. Move into the frame, improve the light, and keep both hands visible while you sign.",
            "hands_detected": 0,
            "expected_hands": required_hands,
            "expected_hand_samples": 0,
            "sample_count": len(live_frames),
        }

    best = None
    for reference in references[request.sign_id]:
        compared = compare_pose_sequences(consistent_frames, reference)
        if compared and (best is None or compared["similarity"] > best["similarity"]):
            best = compared
    if best is None:
        raise HTTPException(status_code=422, detail="Could not compare this attempt with the reference.")

    classifier = None
    try:
        classifier = load_error_classifier(MODEL_PATH)
    except (OSError, ValueError, RuntimeError):
        pass
    prediction = predict_sequence(classifier, consistent_frames, request.sign_id)
    label = prediction.get("label") if prediction else None
    elapsed_ms = max(0.0, (time.perf_counter() - started) * 1000.0)
    result = {
        "status": "COMPLETED",
        "sign_id": request.sign_id,
        "hands_detected": dominant_hands,
        "expected_hands": required_hands,
        "similarity_score": float(best["similarity"]),
        "similarity_label": "Reference pose similarity (prototype)",
        "ml_prediction": label,
        "ml_feedback": _browser_feedback(label),
        "ml_available": prediction is not None and label not in {"UNSUPPORTED_SIGN", "NO_SINGLE_HAND_DATA"},
        "frames_analyzed": len(consistent_frames),
        "analysis_latency_ms": elapsed_ms,
        "message": _browser_feedback(label) if prediction else "Your attempt was compared with the reference. The error diagnosis model is unavailable for this sign.",
    }

    error_codes = [label] if label and label.startswith("ERR_") else []
    document = {
        "user_id": request.user_id,
        "sign_id": request.sign_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "hands_detected": dominant_hands,
        "expected_hands": required_hands,
        "status": "COMPLETED",
        "metrics": {
            "dtw_distance": float(best["distance"]),
            "similarity_score": float(best["similarity"]),
            "analysis_latency_ms": elapsed_ms,
            "ml_prediction": label,
            "ml_confidence": None,
        },
        "detected_error_codes": error_codes,
    }
    try:
        recent_attempts = AttemptStore().recent(request.user_id, limit=4)
    except (OSError, ValueError):
        recent_attempts = []
    recommendations = recommend_from_history([*recent_attempts, document])
    if recommendations:
        recommendation = recommendations[0]
        document["remediation_recommended"] = {
            "recommended_exercise": recommendation["exercise"],
            "trigger_reason": f"Repeated {recommendation['error_code']} diagnosis across {recommendation['attempt_count']} recent attempts",
        }
        result["recommendation"] = recommendation["exercise"]
    if error_codes and dominant_hands == 1:
        document["kinematic_observation"] = {
            "feature_schema": "wrist_origin_unit_scale_xyz_v1",
            "frames": [{"frame_index": index, "hands": frame.astype(float).tolist()} for index, frame in enumerate(consistent_frames[:120])],
        }
    try:
        AttemptStore().record(document)
        result["saved"] = True
    except (OSError, ValueError, KeyError):
        result["saved"] = False
    if mongo_client is not None:
        try:
            database = _database()
            collection = database[COLLECTION_NAME]
            collection.create_index([("user_id", 1), ("timestamp", -1)])
            collection.insert_one(document)
            result["saved_to_mongodb"] = True
        except (HTTPException, PyMongoError):
            result["saved_to_mongodb"] = False
    else:
        result["saved_to_mongodb"] = False
    return result


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
            detail=(
                "MongoDB could not be reached during startup. Check your network/DNS and MONGODB_URI in web/skill-remediation/.env."
                if MONGODB_INIT_FAILED
                else "MongoDB is not configured. Set MONGODB_URI in web/skill-remediation/.env."
            ),
        )
    try:
        mongo_client.admin.command("ping")
    except (PyMongoError, ConfigurationError) as error:
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
