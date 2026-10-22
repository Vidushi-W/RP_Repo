"""Optional inference adapter for the trained kinematic error classifier."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from backend.ml_features import FEATURE_NAMES, extract_features


def load_error_classifier(path: Path):
    """Load a trained bundle, or return None so the template app still runs."""
    if not path.exists():
        return None
    try:
        import joblib
    except ImportError as error:
        raise RuntimeError("Install the project requirements to use the saved classifier.") from error
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or "pipeline" not in bundle or "sign_ids" not in bundle:
        raise ValueError("Classifier bundle is invalid; retrain it with python -m backend.train_model")
    return bundle


def predict_sequence(bundle, frames: list[np.ndarray], sign_id: str) -> dict | None:
    """Predict each captured single-hand frame, then vote for a stable attempt label."""
    if bundle is None:
        return None
    if sign_id not in bundle["sign_ids"]:
        return {"label": "UNSUPPORTED_SIGN", "confidence": None}
    frame_features = []
    for frame in frames:
        hands = np.asarray(frame, dtype=np.float32).reshape(-1, 21, 3)
        if len(hands) != 1:
            continue
        frame_features.append(extract_features(hands[0]))
    if not frame_features:
        return {"label": "NO_SINGLE_HAND_DATA", "confidence": None}
    rows = [dict(zip(FEATURE_NAMES, features.tolist())) | {"sign_id": sign_id} for features in frame_features]
    batch = pd.DataFrame(rows)
    pipeline = bundle["pipeline"]
    frame_labels = pipeline.predict(batch)
    labels, counts = np.unique(frame_labels, return_counts=True)
    winning_label = str(labels[int(np.argmax(counts))])
    confidence = None
    if hasattr(pipeline, "predict_proba"):
        probabilities = pipeline.predict_proba(batch)
        class_index = list(pipeline.classes_).index(winning_label)
        confidence = float(np.mean(probabilities[:, class_index]))
    return {
        "label": winning_label,
        "confidence": confidence,
        "frames_classified": len(frame_features),
        "vote_fraction": float(np.max(counts) / len(frame_labels)),
    }
