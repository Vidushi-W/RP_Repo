"""Model bundle loading and sensor-only inference."""

from __future__ import annotations

import json
import pickle
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from app.ml.decoder import torch_greedy_decode
from app.ml.emotion import extract_motion_features
from app.ml.models import CtcSignModel
from app.ml.preprocessing import NormalizationConfig, resample_recording, smooth_features
from app.ml.vocabulary import BLANK_TOKEN, load_vocabulary
from app.sensors.csv_source import load_csv_to_recording
from app.sensors.frame import SensorRecording


@dataclass
class RecognitionResult:
    predicted_signs: list[str]
    decoder_score: float
    inference_ms: float


@dataclass
class EmotionResult:
    available: bool
    predicted_emotion: str | None
    confidence: float | None
    source: str
    message: str


@dataclass
class LoadedBundle:
    bundle_dir: Path
    model: CtcSignModel
    vocab: dict
    norm: NormalizationConfig
    model_config: dict
    emotion_model: object | None
    emotion_metadata: dict


def load_bundle(bundle_dir: Path) -> LoadedBundle:
    required = ["model.pt", "vocabulary.json", "preprocessing.json", "model_config.json"]
    for name in required:
        if not (bundle_dir / name).exists():
            raise ValueError(f"Bundle missing required file: {name}")

    vocab = load_vocabulary(bundle_dir / "vocabulary.json")
    norm = NormalizationConfig.load(bundle_dir / "preprocessing.json")
    model_config = json.loads((bundle_dir / "model_config.json").read_text(encoding="utf-8"))
    model = CtcSignModel(
        num_classes=model_config.get("num_classes", len(vocab["labels"])),
        cnn_channels=model_config.get("cnn_channels", 32),
        hidden_size=model_config.get("hidden_size", 32),
    )
    state = torch.load(bundle_dir / "model.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()

    emotion_model = None
    emotion_metadata: dict = {}
    return LoadedBundle(
        bundle_dir=bundle_dir,
        model=model,
        vocab=vocab,
        norm=norm,
        model_config=model_config,
        emotion_model=emotion_model,
        emotion_metadata=emotion_metadata,
    )


def preprocess_sensor(sensor: SensorRecording, norm: NormalizationConfig) -> tuple[torch.Tensor, int]:
    x = smooth_features(resample_recording(sensor, norm.target_sample_rate_hz).to_feature_matrix())
    x = norm.normalize(x)
    tensor = torch.from_numpy(x.astype(np.float32)).unsqueeze(0)
    return tensor, x.shape[0]


def recognize_sensor(sensor: SensorRecording, bundle: LoadedBundle) -> RecognitionResult:
    """Run CTC recognition on sensor features only — no labels or metadata."""
    start = time.perf_counter()
    tensor, length = preprocess_sensor(sensor, bundle.norm)
    in_len = torch.tensor([length])
    id_to_label = {
        int(k): v for k, v in bundle.vocab["id_to_label"].items() if v != BLANK_TOKEN
    }
    blank_index = int(bundle.model_config.get("blank_index", 0))
    with torch.no_grad():
        logits, out_lens = bundle.model(tensor, input_lengths=in_len)
        pred, score = torch_greedy_decode(
            logits[0, : int(out_lens[0])], blank_index=blank_index, id_to_label=id_to_label
        )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return RecognitionResult(predicted_signs=pred, decoder_score=score, inference_ms=elapsed_ms)


def recognize_from_csv(csv_path: Path, bundle: LoadedBundle) -> RecognitionResult:
    sensor = load_csv_to_recording(csv_path)
    return recognize_sensor(sensor, bundle)


def predict_emotion(sensor: SensorRecording, bundle: LoadedBundle) -> EmotionResult:
    return EmotionResult(available=False, predicted_emotion=None, confidence=None,
                         source="disabled", message="Emotion recognition is disabled.")


def gloss_to_english(gloss_tokens: list[str]) -> str:
    from app.ml.sentence_generator import generate_english_sentence

    return generate_english_sentence(gloss_tokens).english
