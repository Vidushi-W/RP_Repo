"""Separate lightweight emotion classifier."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from app.sensors.frame import SensorRecording


@dataclass
class EmotionTrainResult:
    trained: bool
    classes: list[str]
    message: str


def extract_motion_features(recording: SensorRecording) -> np.ndarray:
    x = recording.to_feature_matrix()
    if len(x) == 0:
        return np.zeros(6, dtype=np.float32)
    left_acc = x[:, 5:8]
    right_acc = x[:, 16:19]
    left_gyro = x[:, 8:11]
    right_gyro = x[:, 19:22]
    acc_mag = np.linalg.norm(left_acc, axis=1) + np.linalg.norm(right_acc, axis=1)
    gyro_mag = np.linalg.norm(left_gyro, axis=1) + np.linalg.norm(right_gyro, axis=1)
    acc_diff = np.diff(acc_mag, prepend=acc_mag[:1])
    return np.array([
        float(np.mean(acc_mag)),
        float(np.std(acc_mag)),
        float(np.max(acc_mag)),
        float(np.mean(np.abs(acc_diff))),
        float(np.mean(gyro_mag)),
        float(np.std(gyro_mag)),
    ], dtype=np.float32)


def train_emotion_model(recordings: list[SensorRecording], labels: list[str], random_state: int = 42) -> tuple[RandomForestClassifier | None, EmotionTrainResult]:
    valid_pairs = [(r, l) for r, l in zip(recordings, labels) if l in {"neutral", "angry"}]
    if len(valid_pairs) < 4:
        return None, EmotionTrainResult(False, [], "Insufficient labelled emotion data in training split.")
    X = np.stack([extract_motion_features(r) for r, _ in valid_pairs], axis=0)
    y = np.array([l for _, l in valid_pairs])
    if len(set(y)) < 2:
        return None, EmotionTrainResult(False, list(set(y)), "Need both neutral and angry labels in training data.")
    model = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=random_state, n_jobs=1)
    model.fit(X, y)
    return model, EmotionTrainResult(True, list(model.classes_), "Emotion model trained on motion features only.")


def save_emotion_bundle(model: RandomForestClassifier, path: Path, metadata: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(model, f)
    (path.parent / "emotion_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
