"""In-memory live input sessions for CSV playback and future hardware adapters."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.ml.inference import LoadedBundle, load_bundle, predict_emotion, recognize_sensor
from app.ml.preprocessing import motion_magnitudes
from app.ml.sentence_generator import generate_english_sentence
from app.sensors.csv_source import CsvPlaybackSource, load_csv_to_recording
from app.sensors.frame import SensorFrame, SensorRecording
from app.services.feedback_service import FeedbackService


REST_FRAMES = 12
REST_MAGNITUDE = 0.35
MIN_FRAMES_FOR_INFERENCE = 30
FRAMES_PER_TICK = 5


@dataclass
class LiveSession:
    id: str
    source_type: str
    speed: float = 1.0
    status: str = "idle"
    buffer: list[SensorFrame] = field(default_factory=list)
    playback: CsvPlaybackSource | None = None
    filename: str = ""
    elapsed_ms: float = 0.0
    last_provisional_signs: list[str] = field(default_factory=list)
    rest_frame_count: int = 0
    finalized_messages: list[dict[str, Any]] = field(default_factory=list)
    bundle: LoadedBundle | None = None
    uncertainty_threshold: float = 0.25


class LiveSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, LiveSession] = {}

    def create(self, source_type: str = "csv_playback") -> LiveSession:
        session = LiveSession(id=str(uuid.uuid4()), source_type=source_type)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> LiveSession | None:
        return self._sessions.get(session_id)

    def attach_bundle(self, session_id: str, bundle_dir) -> None:
        session = self._require(session_id)
        session.bundle = load_bundle(bundle_dir)

    def upload_csv(self, session_id: str, data: bytes, filename: str) -> dict[str, Any]:
        session = self._require(session_id)
        recording = load_csv_to_recording(data, source_name=filename)
        session.playback = CsvPlaybackSource(data, speed=session.speed, source_name=filename)
        session.filename = filename
        session.buffer = []
        session.status = "idle"
        session.elapsed_ms = 0.0
        duration = recording.duration_ms
        rate = 0.0
        if len(recording.frames) >= 2 and duration > 0:
            rate = len(recording.frames) / (duration / 1000.0)
        return {
            "filename": filename,
            "frame_count": len(recording.frames),
            "duration_ms": duration,
            "sample_rate_hz": rate,
        }

    def set_speed(self, session_id: str, speed: float) -> None:
        session = self._require(session_id)
        session.speed = max(0.25, min(speed, 4.0))
        if session.playback:
            session.playback.speed = session.speed

    def start(self, session_id: str) -> None:
        session = self._require(session_id)
        if not session.playback:
            raise ValueError("Upload a CSV recording before starting playback.")
        session.status = "playing"
        session.playback.resume()

    def pause(self, session_id: str) -> None:
        session = self._require(session_id)
        session.status = "paused"
        if session.playback:
            session.playback.pause()

    def resume(self, session_id: str) -> None:
        session = self._require(session_id)
        if session.playback:
            session.playback.resume()
        session.status = "playing"

    def stop(self, session_id: str) -> None:
        session = self._require(session_id)
        session.status = "stopped"
        if session.playback:
            session.playback.stop()

    def reset(self, session_id: str) -> None:
        session = self._require(session_id)
        session.buffer = []
        session.elapsed_ms = 0.0
        session.last_provisional_signs = []
        session.rest_frame_count = 0
        session.status = "idle"
        if session.playback:
            session.playback.reset()

    def tick(self, session_id: str) -> dict[str, Any]:
        session = self._require(session_id)
        if session.status != "playing" or not session.playback:
            return self._status_payload(session, provisional=None)

        new_frames: list[SensorFrame] = []
        for _ in range(FRAMES_PER_TICK):
            frame = session.playback.next_frame()
            if frame is None:
                session.status = "stopped"
                break
            new_frames.append(frame)
            session.buffer.append(frame)
            session.elapsed_ms = frame.timestamp_ms

        if new_frames:
            self._update_rest_counter(session, new_frames)

        provisional = None
        if len(session.buffer) >= MIN_FRAMES_FOR_INFERENCE and session.bundle:
            provisional = self._provisional_inference(session)

        if session.rest_frame_count >= REST_FRAMES and len(session.buffer) >= MIN_FRAMES_FOR_INFERENCE:
            final = self.finalize(session_id)
            return {**self._status_payload(session, provisional=None), "auto_finalized": final}

        return self._status_payload(session, provisional=provisional)

    def finalize(self, session_id: str) -> dict[str, Any]:
        session = self._require(session_id)
        if not session.bundle or len(session.buffer) < MIN_FRAMES_FOR_INFERENCE:
            raise ValueError("Insufficient buffered frames for final recognition.")
        recording = SensorRecording(frames=list(session.buffer), source_name=session.filename or "live")
        recognition = recognize_sensor(recording, session.bundle)
        emotion = predict_emotion(recording, session.bundle)
        sentence = generate_english_sentence(
            recognition.predicted_signs,
            decoder_score=recognition.decoder_score,
            uncertainty_threshold=session.uncertainty_threshold,
        )
        uncertain = recognition.decoder_score < session.uncertainty_threshold
        feedback = FeedbackService.on_uncertain_recognition(recognition.decoder_score, session.uncertainty_threshold) if uncertain else None

        message = {
            "english": sentence.english,
            "gloss_sequence": recognition.predicted_signs,
            "emotion": emotion.predicted_emotion,
            "emotion_confidence": emotion.confidence,
            "emotion_source": emotion.source,
            "decoder_score": recognition.decoder_score,
            "decoder_score_label": "uncalibrated_decoder_score",
            "inference_ms": recognition.inference_ms,
            "is_provisional": False,
            "sentence_status": sentence.status,
            "uncertain": uncertain,
            "feedback": feedback.__dict__ if feedback else None,
            "timestamp": time.time(),
        }
        session.finalized_messages.append(message)
        session.buffer = []
        session.last_provisional_signs = []
        session.rest_frame_count = 0
        return message

    def _provisional_inference(self, session: LiveSession) -> dict[str, Any]:
        recording = SensorRecording(frames=list(session.buffer), source_name="provisional")
        recognition = recognize_sensor(recording, session.bundle)
        signs = recognition.predicted_signs
        if signs == session.last_provisional_signs:
            signs_display = signs
        else:
            session.last_provisional_signs = list(signs)
            signs_display = signs
        sentence = generate_english_sentence(signs, recognition.decoder_score, session.uncertainty_threshold)
        return {
            "gloss_sequence": signs_display,
            "english": sentence.english if sentence.status != "uncertain" else " ".join(signs_display),
            "decoder_score": recognition.decoder_score,
            "is_provisional": True,
            "lookahead_note": (
                "BiLSTM uses bidirectional context; provisional prediction may change as more frames arrive."
            ),
        }

    def _update_rest_counter(self, session: LiveSession, frames: list[SensorFrame]) -> None:
        rec = SensorRecording(frames=frames)
        feats = rec.to_feature_matrix()
        if feats.shape[0] == 0:
            return
        left, right = motion_magnitudes(feats)
        motion = (left + right) / 2.0
        if float(motion[-1]) < REST_MAGNITUDE:
            session.rest_frame_count += len(frames)
        else:
            session.rest_frame_count = 0

    def _status_payload(self, session: LiveSession, provisional: dict | None) -> dict[str, Any]:
        motion = {"left": [], "right": [], "timestamps_ms": []}
        if session.buffer:
            tail = session.buffer[-80:]
            rec = SensorRecording(frames=tail)
            feats = rec.to_feature_matrix()
            ts = rec.timestamps()
            left, right = motion_magnitudes(feats)
            motion = {
                "timestamps_ms": ts,
                "left": left.tolist(),
                "right": right.tolist(),
            }
        return {
            "session_id": session.id,
            "status": session.status,
            "source_type": session.source_type,
            "filename": session.filename,
            "elapsed_ms": session.elapsed_ms,
            "buffer_frames": len(session.buffer),
            "speed": session.speed,
            "motion": motion,
            "provisional": provisional,
            "finalized_messages": session.finalized_messages,
        }

    def _require(self, session_id: str) -> LiveSession:
        session = self.get(session_id)
        if not session:
            raise ValueError("Live session not found")
        return session


live_session_store = LiveSessionStore()
