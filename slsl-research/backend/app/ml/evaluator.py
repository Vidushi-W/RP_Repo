"""Batch evaluation on held-out recordings — labels compared after inference."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.ml.inference import (
    LoadedBundle,
    gloss_to_english,
    load_bundle,
    predict_emotion,
    recognize_from_csv,
)
from app.ml.metrics import (
    aggregate_wer,
    emotion_classification_metrics,
    exact_sequence_accuracy,
    sequence_metrics,
)
from app.models.dataset import Recording
from app.sensors.csv_source import load_csv_to_recording


def parse_gloss_labels(gloss: str) -> list[str]:
    return [t.strip() for t in gloss.split("|") if t.strip()]


@dataclass
class EvalConfig:
    model_id: int
    dataset_id: int
    dataset_version: str
    split: str = "test"
    uncertainty_threshold: float = 0.25


def evaluate_recordings(
    bundle_dir: Path,
    recordings: list[Recording],
    config: EvalConfig,
    output_dir: Path,
) -> dict[str, Any]:
    bundle = load_bundle(bundle_dir)
    predictions: list[dict[str, Any]] = []
    wer_list: list[float] = []
    exact_flags: list[bool] = []
    latencies: list[float] = []
    emotion_true: list[str] = []
    emotion_pred: list[str] = []

    for rec in recordings:
        csv_path = settings.data_dir / rec.file_path
        recognition = recognize_from_csv(csv_path, bundle)
        ref_signs = parse_gloss_labels(rec.ordered_sign_labels)
        metrics = sequence_metrics(ref_signs, recognition.predicted_signs)
        wer_list.append(metrics.word_error_rate)
        exact_flags.append(metrics.exact_match)
        latencies.append(recognition.inference_ms)

        sensor = load_csv_to_recording(csv_path, source_name=rec.recording_id)
        emotion = predict_emotion(sensor, bundle)
        ref_emotion = rec.emotion_label if rec.emotion_label in {"neutral", "angry"} else None
        if ref_emotion and emotion.available and emotion.predicted_emotion:
            emotion_true.append(ref_emotion)
            emotion_pred.append(emotion.predicted_emotion)

        high_uncertainty = recognition.decoder_score < config.uncertainty_threshold
        emotion_mismatch = (
            ref_emotion is not None
            and emotion.available
            and emotion.predicted_emotion is not None
            and ref_emotion != emotion.predicted_emotion
        )

        predictions.append({
            "recording_id": rec.recording_id,
            "signer_id": rec.signer_id,
            "provenance": rec.provenance,
            "split": rec.split,
            "reference_signs": ref_signs,
            "predicted_signs": recognition.predicted_signs,
            "reference_english": rec.reference_english_sentence or None,
            "generated_english": gloss_to_english(recognition.predicted_signs),
            "reference_emotion": ref_emotion,
            "predicted_emotion": emotion.predicted_emotion,
            "emotion_confidence": emotion.confidence,
            "emotion_source": emotion.source,
            "decoder_score": recognition.decoder_score,
            "decoder_score_label": "uncalibrated_decoder_score",
            "high_uncertainty": high_uncertainty,
            "emotion_mismatch": emotion_mismatch,
            "inference_ms": recognition.inference_ms,
            "exact_match": metrics.exact_match,
            "word_error_rate": metrics.word_error_rate,
            "insertions": metrics.insertions,
            "deletions": metrics.deletions,
            "substitutions": metrics.substitutions,
            "alignment": [
                {"op": s.op, "ref": s.ref, "pred": s.pred} for s in metrics.alignment
            ],
        })

    aggregate = {
        "word_error_rate": aggregate_wer(wer_list),
        "exact_sequence_accuracy": exact_sequence_accuracy(exact_flags),
        "total_insertions": sum(p["insertions"] for p in predictions),
        "total_deletions": sum(p["deletions"] for p in predictions),
        "total_substitutions": sum(p["substitutions"] for p in predictions),
        "mean_inference_ms": float(sum(latencies) / len(latencies)) if latencies else 0.0,
        "median_inference_ms": float(sorted(latencies)[len(latencies) // 2]) if latencies else 0.0,
        "recording_count": len(predictions),
        "high_uncertainty_count": sum(1 for p in predictions if p["high_uncertainty"]),
        "uncertainty_threshold": config.uncertainty_threshold,
    }

    emotion_metrics = emotion_classification_metrics(emotion_true, emotion_pred)
    results = {
        "config": config.__dict__,
        "aggregate": aggregate,
        "emotion": emotion_metrics,
        "predictions": predictions,
        "limitations": [
            "Decoder scores are uncalibrated and must not be interpreted as correctness probabilities.",
            "Sign boundaries are not estimated; only ordered gloss sequences are evaluated.",
            "Generated English is a simple gloss concatenation, not a full translation model.",
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
