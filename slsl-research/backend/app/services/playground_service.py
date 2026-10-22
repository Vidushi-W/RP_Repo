"""Playground recognition — sensor-only inference, no ground-truth access."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recognition import RecognitionMessage
from app.ml.inference import load_bundle, predict_emotion, recognize_sensor
from app.ml.preprocessing import validate_recording
from app.ml.sentence_generator import generate_english_sentence, list_sentence_patterns
from app.ml.vocabulary import BLANK_TOKEN
from app.repositories.dataset import DatasetRepository
from app.repositories.system import SystemRepository
from app.sensors.csv_source import HardwareSensorSource, load_csv_to_recording
from app.services.feedback_service import FeedbackService
from app.services.model_registry import ModelRegistryService


class PlaygroundService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.system_repo = SystemRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.model_registry = ModelRegistryService(db)

    def get_status(self) -> dict[str, Any]:
        active = self.system_repo.active_model()
        return {
            "active_model": self._model_summary(active) if active else None,
            "hardware_connected": HardwareSensorSource.is_available(),
            "hardware_message": (
                "No device connected. Configure ESP32 serial/BLE/Wi-Fi when hardware details are available."
                if not HardwareSensorSource.is_available()
                else "Hardware gloves connected."
            ),
        }

    def recognize_upload(
        self,
        file_bytes: bytes,
        filename: str,
        model_id: int | None = None,
        uncertainty_threshold: float = 0.25,
    ) -> dict[str, Any]:
        model, bundle_dir = self._resolve_model(model_id)
        sensor = load_csv_to_recording(file_bytes, source_name=filename)
        validation = validate_recording(sensor)

        bundle = load_bundle(bundle_dir)
        recognition = recognize_sensor(sensor, bundle)
        emotion = predict_emotion(sensor, bundle)
        sentence = generate_english_sentence(
            recognition.predicted_signs,
            decoder_score=recognition.decoder_score,
            uncertainty_threshold=uncertainty_threshold,
        )
        uncertain = recognition.decoder_score < uncertainty_threshold
        feedback = FeedbackService.on_uncertain_recognition(recognition.decoder_score, uncertainty_threshold) if uncertain else None

        display_english = sentence.english
        if sentence.status in {"uncertain", "fallback", "empty"} and not sentence.pattern_matched:
            if uncertain or not recognition.predicted_signs:
                display_english = " | ".join(recognition.predicted_signs) if recognition.predicted_signs else ""

        result = {
            "filename": filename,
            "validation": validation.to_dict(),
            "english": display_english,
            "gloss_sequence": recognition.predicted_signs,
            "emotion": emotion.predicted_emotion,
            "emotion_confidence": emotion.confidence,
            "emotion_source": emotion.source,
            "emotion_message": emotion.message,
            "decoder_score": recognition.decoder_score,
            "decoder_score_label": "uncalibrated_decoder_score",
            "uncertain": uncertain,
            "sentence_status": sentence.status,
            "sentence_message": sentence.message,
            "model_id": model.id,
            "model_name": model.name,
            "model_version": model.version,
            "inference_ms": recognition.inference_ms,
            "timestamp": time.time(),
            "feedback": feedback.__dict__ if feedback else None,
            "no_ground_truth_used": True,
        }
        self._save_message(result)
        return result

    def list_history(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(RecognitionMessage).order_by(RecognitionMessage.created_at.desc()).limit(limit)
        )
        return [self._message_to_dict(r) for r in rows]

    def clear_history(self) -> int:
        count = len(self.db.scalars(select(RecognitionMessage)).all())
        for row in self.db.scalars(select(RecognitionMessage)):
            self.db.delete(row)
        self.db.commit()
        return count

    def _save_message(self, payload: dict[str, Any]) -> None:
        msg = RecognitionMessage(
            source="playground",
            filename=payload["filename"],
            model_id=payload["model_id"],
            model_name=payload["model_name"],
            model_version=payload["model_version"],
            english=payload["english"],
            gloss_sequence_json=json.dumps(payload["gloss_sequence"]),
            emotion=payload.get("emotion"),
            decoder_score=payload.get("decoder_score"),
            inference_ms=payload.get("inference_ms"),
            uncertain=payload.get("uncertain", False),
            payload_json=json.dumps(payload),
        )
        self.db.add(msg)
        self.dataset_repo.add_activity("recognition", f"Recognized upload '{payload['filename']}'")
        self.db.commit()

    def _message_to_dict(self, row: RecognitionMessage) -> dict[str, Any]:
        payload = json.loads(row.payload_json or "{}")
        payload.setdefault("id", row.id)
        payload.setdefault("gloss_sequence", json.loads(row.gloss_sequence_json or "[]"))
        payload.setdefault("timestamp", row.created_at.timestamp() if row.created_at else 0)
        return payload

    def get_dictionary(self, model_id: int | None = None) -> dict[str, Any]:
        model, bundle_dir = self._resolve_model(model_id)
        bundle = load_bundle(bundle_dir)
        vocab = bundle.vocab
        labels = [l for l in vocab.get("labels", []) if l != BLANK_TOKEN]
        patterns = list_sentence_patterns()

        examples: dict[str, list[dict[str, Any]]] = {g: [] for g in labels}
        support_counts: dict[str, int] = {g: 0 for g in labels}
        if model.dataset_id:
            for rec in self.dataset_repo.list_recordings(model.dataset_id):
                glosses = [t.strip() for t in rec.ordered_sign_labels.split("|") if t.strip()]
                for g in glosses:
                    if g in support_counts:
                        support_counts[g] += 1
                        if len(examples[g]) < 3:
                            examples[g].append({
                                "recording_id": rec.recording_id,
                                "dataset_id": model.dataset_id,
                                "split": rec.split,
                                "provenance": rec.provenance,
                                "ordered_sign_labels": rec.ordered_sign_labels,
                            })

        entries = []
        for gloss in sorted(labels):
            related_patterns = [p for p in patterns if gloss in p["gloss_sequence"]]
            entries.append({
                "gloss": gloss,
                "english_concept": gloss.title(),
                "supported_patterns": related_patterns,
                "support_count": support_counts.get(gloss, 0),
                "provenance": model.provenance,
                "validation_status": (
                    "prototype_synthetic" if model.provenance == "synthetic" else "real_annotation"
                ),
                "example_recordings": examples.get(gloss, []),
                "reliability_note": "Vocabulary membership does not guarantee reliable recognition.",
            })

        return {
            "model_id": model.id,
            "model_name": model.name,
            "model_version": model.version,
            "provenance": model.provenance,
            "entries": entries,
            "sentence_patterns": patterns,
            "disclaimer": (
                "Dictionary shows model vocabulary and sentence mappings — not proof of learned sensor motions."
            ),
        }

    def _resolve_model(self, model_id: int | None) -> tuple[Any, Path]:
        if model_id:
            model = self.model_registry.get_model(model_id)
        else:
            model = self.system_repo.active_model()
        if not model or model.is_archived:
            raise ValueError("No model available. Train and activate a model first.")
        if not model.bundle_path:
            raise ValueError("Model bundle not found.")
        bundle_dir = settings.artifacts_dir / model.bundle_path
        return model, bundle_dir

    def _model_summary(self, model) -> dict[str, Any]:
        return {
            "id": model.id,
            "name": model.name,
            "version": model.version,
            "provenance": model.provenance,
            "emotion_available": model.emotion_available,
        }
