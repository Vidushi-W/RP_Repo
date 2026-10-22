"""Read-only bridge to existing trained assets. No admin routes or training imports."""

import io
import os
import sqlite3
import sys
import threading
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pandas as pd
from . import config

sys.path.insert(0, str(config.ADMIN / "backend"))
from app.core.config import SENSOR_COLUMNS, settings

# Resolve paths relative to the admin backend, independent of service launch directory.
for key in (
    "data_dir",
    "artifacts_dir",
    "sentence_model_dir",
    "translation_model_dir",
    "sinhala_voice_dir",
):
    path = getattr(settings, key)
    if not path.is_absolute():
        setattr(settings, key, (config.ADMIN / "backend" / path).resolve())


def validate_csv(raw):
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise ValueError("This file could not be read as a CSV.") from exc
    if set(df.columns) != set(SENSOR_COLUMNS) or len(df.columns) != 23:
        raise ValueError(
            "Use a motion-only CSV with timestamp_ms and all 22 glove sensor channels. No answer labels."
        )
    if not 4 <= len(df) <= 15000:
        raise ValueError("Use 4 to 15,000 frames (up to five minutes at 50 Hz).")
    try:
        values = df[SENSOR_COLUMNS].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("All sensor values must be numeric.") from exc
    if not np.isfinite(values).all():
        raise ValueError("Sensor values must be finite, with no blanks.")
    times = values[:, 0]
    if (
        not (np.diff(times) > 0).all()
        or not 60 <= times[-1] - times[0] <= 300000
        or times[0] < 0
    ):
        raise ValueError(
            "Use strictly increasing nonnegative timestamps covering 60 ms to five minutes."
        )
    return df[SENSOR_COLUMNS].to_csv(index=False).encode()


def current_bundle():
    exported = os.getenv("MODEL_BUNDLE_DIR", "").strip()
    if exported:
        path = (config.ROOT / exported).resolve()
        return path, dict(id=path.name, version="exported")
    db = config.ADMIN / "backend" / "slsl_studio.db"
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT id,version,bundle_path FROM ml_models WHERE is_archived=0 ORDER BY CASE WHEN status='active' THEN 0 ELSE 1 END,id DESC LIMIT 1"
        ).fetchone()
    if not row or not row["bundle_path"]:
        raise ValueError(
            "No trained model is available. Train it in the admin studio first."
        )
    path = (settings.artifacts_dir / row["bundle_path"]).resolve()
    if not path.is_relative_to(settings.artifacts_dir.resolve()):
        raise ValueError("Invalid model bundle path.")
    return path, dict(id=row["id"], version=row["version"])


# Client-only limits; do not alter the admin process or its environment file.
_timeout = int(os.getenv("LOCAL_AI_TIMEOUT_SECONDS", "240"))
if not 30 <= _timeout <= 600:
    raise ValueError("LOCAL_AI_TIMEOUT_SECONDS must be between 30 and 600.")
settings.sentence_timeout_seconds = _timeout
settings.speech_timeout_seconds = _timeout


class Pipeline:
    def __init__(self):
        self.bundle = None
        self.key = None

    def run(self, csv_path, update, output):
        update(stage="motion")
        import torch
        from app.ml.inference import load_bundle, recognize_from_csv
        from app.ml.local_sentence import generate_spoken_sentence
        from app.ml.expression_rules import analyze_expression

        torch.set_num_threads(2)
        directory, model = current_bundle()
        key = (str(directory), (directory / "model.pt").stat().st_mtime_ns)
        if self.key != key:
            self.bundle = load_bundle(directory)
            self.key = key
        update(stage="motion", model=model)
        recognized = recognize_from_csv(csv_path, self.bundle)
        words = recognized.predicted_signs
        expression = analyze_expression(words)
        update(
            stage="sentence",
            words=words,
            expression=expression,
            decoder_score=recognized.decoder_score,
        )
        sentence = generate_spoken_sentence(
            words, uncertain=recognized.decoder_score < 0.25
        )
        update(sentence=asdict(sentence))
        if not sentence.text:
            update(stage="done", notice=sentence.message)
            return
        self.resume(
            {"sentence": asdict(sentence), "expression": expression}, update, output
        )

    def resume(self, row, update, output):
        from app.ml.sinhala_speech import translate_sentence, synthesize_sinhala

        sinhala = row.get("sinhala")
        if not sinhala:
            update(stage="translation")
            sinhala = translate_sentence(row["sentence"]["text"])
        update(stage="voice", sinhala=sinhala)
        audio = synthesize_sinhala(sinhala, row.get("expression", {}).get("label"))
        output.write_bytes(audio)
        update(stage="done", audio_ready=True, error=None)
