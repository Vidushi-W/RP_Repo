"""Reproducible synthetic two-glove sensor data generator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import FEATURE_COLUMNS, NOMINAL_SAMPLE_RATE_HZ, RANDOM_SEED, SENSOR_COLUMNS, VOCABULARY
from app.ml.preprocessing import validate_dataframe
from app.sensors.csv_source import load_csv_to_recording

SENTENCE_PATTERNS = [
    (["I", "NEED", "WATER"], "I need water.", "neutral"),
    (["I", "WANT", "FOOD"], "I want food.", "neutral"),
    (["YOU", "GO", "HOME"], "You go home.", "neutral"),
    (["I", "NEED", "HELP"], "I need help.", "neutral"),
    (["YOU", "STOP"], "You stop.", "neutral"),
]

SIGN_PROFILES: dict[str, dict] = {}
for i, sign in enumerate(VOCABULARY):
    phase = 2 * np.pi * i / len(VOCABULARY)
    SIGN_PROFILES[sign] = {
        "left_flex": np.clip(0.2 + 0.6 * np.sin(phase + np.arange(5) * 0.5), 0, 1),
        "right_flex": np.clip(0.2 + 0.6 * np.cos(phase + np.arange(5) * 0.5), 0, 1),
        "left_acc": np.array([0.2 * np.sin(phase), 0.3 * np.cos(phase), 0.8 + 0.1 * i]),
        "right_acc": np.array([0.15 * np.cos(phase), 0.25 * np.sin(phase), 0.7 + 0.1 * i]),
        "left_gyro": 20 * np.array([np.sin(phase), np.cos(phase), np.sin(phase / 2)]),
        "right_gyro": 20 * np.array([np.cos(phase), np.sin(phase), np.cos(phase / 2)]),
    }


def _smoothstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


@dataclass
class SyntheticConfig:
    seed: int = RANDOM_SEED
    total_recordings: int = 400
    train_ratio: float = 0.7
    val_ratio: float = 0.15


def _generate_sequence(rng: np.random.Generator, signs: list[str], emotion: str, signer: str) -> pd.DataFrame:
    signer_num = int(signer.split("_")[-1]) if signer.split("_")[-1].isdigit() else 1
    scale = 0.9 + 0.04 * signer_num
    interval = 1000.0 / NOMINAL_SAMPLE_RATE_HZ
    timestamps: list[float] = []
    rows: list[np.ndarray] = []
    t = 0.0

    def segment(profile: dict, n: int, amp: float = 1.0) -> np.ndarray:
        tt = np.linspace(0, 1, n)
        env = _smoothstep(np.sin(np.pi * tt) ** 0.8)
        motion = 1.35 if emotion == "angry" else 1.0
        lf = profile["left_flex"] * scale
        rf = profile["right_flex"] * scale
        out = np.concatenate([
            np.clip(lf * env[:, None] + rng.normal(0, 0.02, (n, 5)), 0, 1),
            profile["left_acc"] * motion * env[:, None] + rng.normal(0, 0.03, (n, 3)),
            profile["left_gyro"] * motion * env[:, None] + rng.normal(0, 5, (n, 3)),
            np.clip(rf * env[:, None] + rng.normal(0, 0.02, (n, 5)), 0, 1),
            profile["right_acc"] * motion * env[:, None] + rng.normal(0, 0.03, (n, 3)),
            profile["right_gyro"] * motion * env[:, None] + rng.normal(0, 5, (n, 3)),
        ], axis=1)
        return out * amp

    rest = segment(SIGN_PROFILES["STOP"], rng.integers(8, 14), amp=0.2)
    for row in rest:
        timestamps.append(t)
        rows.append(row)
        t += interval
    prev = rest[-1]
    for sign in signs:
        trans_n = int(rng.integers(10, 16))
        sign_n = int(rng.integers(30, 45))
        trans = (prev * 0.25 + segment(SIGN_PROFILES[sign], trans_n)[0] * 0.25)
        for i in range(trans_n):
            alpha = i / max(trans_n - 1, 1)
            timestamps.append(t)
            rows.append(prev * (1 - alpha) + trans * alpha)
            t += interval
        body = segment(SIGN_PROFILES[sign], sign_n)
        for row in body:
            timestamps.append(t)
            rows.append(row)
            t += interval
        prev = body[-1]
        gap = segment(SIGN_PROFILES["STOP"], 8, amp=0.15)
        for row in gap:
            timestamps.append(t)
            rows.append(row)
            t += interval
        prev = gap[-1]

    data = np.stack(rows, axis=0)
    df = pd.DataFrame(data, columns=FEATURE_COLUMNS)
    df.insert(0, "timestamp_ms", timestamps)
    return df[SENSOR_COLUMNS]


def generate_synthetic_package(output_dir: Path, config: SyntheticConfig) -> dict:
    rng = np.random.default_rng(config.seed)
    eval_rng = np.random.default_rng(config.seed + 10_000)
    recordings_dir = output_dir / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict] = []
    rid = 1
    per_pattern = max(1, config.total_recordings // len(SENTENCE_PATTERNS))

    for signs, sentence, base_emotion in SENTENCE_PATTERNS:
        for i in range(per_pattern):
            if rid > config.total_recordings:
                break
            emotion = base_emotion if i % 6 else "angry"
            signer = f"SYNTHETIC_SIGNER_{(i % 6) + 1:02d}"
            if i < per_pattern * config.train_ratio:
                split = "train"
                gen_rng = rng
            elif i < per_pattern * (config.train_ratio + config.val_ratio):
                split = "val"
                gen_rng = rng
            else:
                split = "test"
                gen_rng = eval_rng
            rec_id = f"sequence_{rid:04d}"
            df = _generate_sequence(gen_rng, signs, emotion, signer)
            report = validate_dataframe(df)
            if not report.valid:
                raise ValueError(f"Generated invalid recording {rec_id}: {report.errors}")
            rel = f"recordings/{rec_id}.csv"
            df.to_csv(output_dir / rel, index=False)
            manifest_rows.append({
                "recording_id": rec_id,
                "filepath": rel,
                "signer_id": signer,
                "provenance": "synthetic",
                "ordered_sign_labels": "|".join(signs),
                "emotion_label": emotion,
                "reference_english_sentence": sentence,
                "split": split,
            })
            rid += 1

    manifest_path = output_dir / "manifest.csv"
    pd.DataFrame(manifest_rows).to_csv(manifest_path, index=False)
    meta = {"seed": config.seed, "count": len(manifest_rows), "note": "Artificial prototype patterns, not genuine SLSL recordings."}
    (output_dir / "generator_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def content_hash_for_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
