"""Sensor validation, resampling, and normalization configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import FEATURE_COLUMNS, NOMINAL_SAMPLE_RATE_HZ, SENSOR_COLUMNS
from app.sensors.frame import SensorFrame, SensorRecording


@dataclass
class ValidationReport:
    valid: bool
    errors: list[str]
    warnings: list[str]
    frame_count: int = 0
    duration_ms: float = 0.0
    estimated_sample_rate_hz: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "frame_count": self.frame_count,
            "duration_ms": self.duration_ms,
            "estimated_sample_rate_hz": self.estimated_sample_rate_hz,
        }


@dataclass
class NormalizationConfig:
    feature_mean: list[float]
    feature_std: list[float]
    target_sample_rate_hz: float = NOMINAL_SAMPLE_RATE_HZ
    fitted_on_split: str = "train"

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> NormalizationConfig:
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_mean": self.feature_mean,
            "feature_std": self.feature_std,
            "target_sample_rate_hz": self.target_sample_rate_hz,
            "fitted_on_split": self.fitted_on_split,
        }

    def normalize(self, x: np.ndarray) -> np.ndarray:
        mean = np.array(self.feature_mean, dtype=np.float32)
        std = np.array(self.feature_std, dtype=np.float32)
        std = np.where(std < 1e-6, 1.0, std)
        return (x - mean) / std


def validate_dataframe(df: pd.DataFrame) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [c for c in SENSOR_COLUMNS if c not in df.columns]
    if missing:
        return ValidationReport(False, [f"Missing columns: {missing}"], warnings)
    if df.empty:
        return ValidationReport(False, ["Recording is empty"], warnings)
    for col in SENSOR_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f"Column {col} must be numeric")
    if df[SENSOR_COLUMNS[1:]].isna().any().any():
        errors.append("NaN values detected in sensor channels")
    sorted_df = df.sort_values("timestamp_ms").drop_duplicates("timestamp_ms", keep="first")
    if not sorted_df["timestamp_ms"].is_monotonic_increasing:
        warnings.append("Timestamps were not monotonic; sorted during validation")
    duration = float(sorted_df["timestamp_ms"].iloc[-1] - sorted_df["timestamp_ms"].iloc[0]) if len(sorted_df) > 1 else 0.0
    if duration <= 0 and len(sorted_df) > 1:
        errors.append("Invalid timestamp range")
    intervals = np.diff(sorted_df["timestamp_ms"].to_numpy(dtype=np.float64)) if len(sorted_df) > 1 else np.array([20.0])
    median = float(np.median(intervals)) if len(intervals) else 20.0
    hz = 1000.0 / median if median > 0 else 0.0
    if hz < 10 or hz > 120:
        warnings.append(f"Unusual estimated sample rate: {hz:.1f} Hz")
    flex_cols = [c for c in FEATURE_COLUMNS if "flex" in c]
    if ((sorted_df[flex_cols] < -0.05) | (sorted_df[flex_cols] > 1.05)).any().any():
        warnings.append("Some flex values fall outside expected 0–1 range")
    return ValidationReport(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        frame_count=len(sorted_df),
        duration_ms=duration,
        estimated_sample_rate_hz=hz,
    )


def validate_recording(recording: SensorRecording) -> ValidationReport:
    rows = [f.as_dict() for f in recording.frames]
    return validate_dataframe(pd.DataFrame(rows)[SENSOR_COLUMNS])


def resample_recording(recording: SensorRecording, target_hz: float = NOMINAL_SAMPLE_RATE_HZ) -> SensorRecording:
    if not recording.frames:
        return recording
    ts = recording.timestamps()
    feats = recording.to_feature_matrix()
    step = 1000.0 / target_hz
    grid = np.arange(ts[0], ts[-1] + step * 0.5, step)
    resampled = np.zeros((len(grid), feats.shape[1]), dtype=np.float32)
    for i in range(feats.shape[1]):
        resampled[:, i] = np.interp(grid, ts, feats[:, i])
    frames = [SensorFrame(timestamp_ms=float(t), features=tuple(resampled[j])) for j, t in enumerate(grid)]
    return SensorRecording(frames=frames, source_name=recording.source_name, metadata=recording.metadata)


def smooth_features(x: np.ndarray, window: int = 3) -> np.ndarray:
    if len(x) < window:
        return x
    kernel = np.ones(window, dtype=np.float32) / window
    out = np.zeros_like(x)
    pad = window // 2
    for i in range(x.shape[1]):
        padded = np.pad(x[:, i], (pad, pad), mode="edge")
        out[:, i] = np.convolve(padded, kernel, mode="valid")
    return out


def fit_normalization(train_recordings: list[SensorRecording], target_hz: float = NOMINAL_SAMPLE_RATE_HZ) -> NormalizationConfig:
    mats = []
    for rec in train_recordings:
        x = resample_recording(rec, target_hz).to_feature_matrix()
        mats.append(smooth_features(x))
    stacked = np.concatenate(mats, axis=0)
    std = stacked.std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    return NormalizationConfig(
        feature_mean=stacked.mean(axis=0).astype(float).tolist(),
        feature_std=std.astype(float).tolist(),
        target_sample_rate_hz=target_hz,
        fitted_on_split="train",
    )


def downsample_series(timestamps: np.ndarray, values: np.ndarray, max_points: int = 300) -> tuple[list[float], list[float]]:
    if len(timestamps) <= max_points:
        return timestamps.tolist(), values.tolist()
    idx = np.linspace(0, len(timestamps) - 1, max_points).astype(int)
    return timestamps[idx].tolist(), values[idx].tolist()


def motion_magnitudes(features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    left = np.linalg.norm(features[:, 5:8], axis=1) + 0.01 * np.linalg.norm(features[:, 8:11], axis=1)
    right = np.linalg.norm(features[:, 16:19], axis=1) + 0.01 * np.linalg.norm(features[:, 19:22], axis=1)
    return left, right
