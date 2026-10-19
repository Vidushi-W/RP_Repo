"""CTC training loop and metrics."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from app.core.config import FEATURE_COLUMNS, RANDOM_SEED, SENSOR_COLUMNS
from app.ml.data_loader import RecordingSequenceDataset, collate_sequences
from app.ml.decoder import torch_greedy_decode
from app.ml.metrics import word_error_rate as token_wer
from app.ml.emotion import train_emotion_model
from app.ml.models import CtcSignModel
from app.ml.preprocessing import NormalizationConfig, fit_normalization, resample_recording, smooth_features
from app.ml.vocabulary import BLANK_TOKEN, build_vocabulary, save_vocabulary
from app.models.dataset import Recording
from app.sensors.csv_source import load_csv_to_recording


@dataclass
class TrainingConfig:
    dataset_id: int
    dataset_version: str
    provenance: str
    epochs: int = 20
    batch_size: int = 4
    learning_rate: float = 0.001
    cnn_channels: int = 32
    hidden_size: int = 32
    patience: int = 5
    random_seed: int = RANDOM_SEED
    training_mode: str = "fresh"
    source_bundle_path: str | None = None
    torch_threads: int = 2


def validate_time_resolution(recordings: list[Recording]) -> list[str]:
    warnings = []
    for rec in recordings:
        if not rec.ordered_sign_labels:
            warnings.append(f"{rec.recording_id}: missing gloss labels")
            continue
        n_labels = len([t for t in rec.ordered_sign_labels.split("|") if t.strip()])
        if rec.frame_count // 2 < n_labels * 2:
            warnings.append(f"{rec.recording_id}: may lack time resolution for {n_labels} labels")
    return warnings


def run_training(
    train_recs: list[Recording],
    val_recs: list[Recording],
    config: TrainingConfig,
    bundle_dir: Path,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    torch.manual_seed(config.random_seed)
    torch.set_num_threads(config.torch_threads)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    signs = set()
    for rec in train_recs + val_recs:
        signs.update(t.strip() for t in rec.ordered_sign_labels.split("|") if t.strip())
    vocab = build_vocabulary(sorted(signs))
    save_vocabulary(vocab, bundle_dir / "vocabulary.json")

    from app.core.config import settings

    train_sensors = [load_csv_to_recording(settings.data_dir / r.file_path) for r in train_recs]
    norm = fit_normalization(train_sensors)
    norm.save(bundle_dir / "preprocessing.json")

    train_ds = RecordingSequenceDataset(train_recs, vocab["label_to_id"], norm)
    val_ds = RecordingSequenceDataset(val_recs, vocab["label_to_id"], norm)
    if len(train_ds) == 0:
        raise ValueError("No valid training sequences after filtering.")

    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True, collate_fn=collate_sequences)
    val_loader = DataLoader(val_ds, batch_size=config.batch_size, shuffle=False, collate_fn=collate_sequences)

    model = CtcSignModel(
        num_classes=len(vocab["labels"]),
        cnn_channels=config.cnn_channels,
        hidden_size=config.hidden_size,
    )
    if config.training_mode == "finetune" and config.source_bundle_path:
        state = torch.load(Path(config.source_bundle_path) / "model.pt", map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=False)

    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = torch.nn.CTCLoss(blank=0, zero_infinity=True)
    id_to_label = {int(k): v for k, v in vocab["id_to_label"].items() if v != BLANK_TOKEN}

    best_val = float("inf")
    best_state = None
    stale = 0
    history: list[dict] = []
    start = time.time()

    for epoch in range(1, config.epochs + 1):
        if cancel_check and cancel_check():
            return {"status": "cancelled", "history": history}

        model.train()
        train_losses = []
        for x, y, in_lens, tgt_lens in train_loader:
            logits, out_lens = model(x, input_lengths=in_lens)
            log_probs = F.log_softmax(logits, dim=-1).transpose(0, 1)
            max_out = int(out_lens.max().item())
            loss = criterion(log_probs[:max_out], y, out_lens, tgt_lens)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))

        model.eval()
        val_losses = []
        all_wer = []
        with torch.no_grad():
            for x, y, in_lens, tgt_lens in val_loader:
                logits, out_lens = model(x, input_lengths=in_lens)
                log_probs = F.log_softmax(logits, dim=-1).transpose(0, 1)
                max_out = int(out_lens.max().item())
                val_losses.append(float(criterion(log_probs[:max_out], y, out_lens, tgt_lens).item()))
            for item in val_ds.items:
                tensor = item.features.unsqueeze(0)
                in_len = torch.tensor([item.input_length])
                logits, ol = model(tensor, input_lengths=in_len)
                pred, _ = torch_greedy_decode(logits[0, : int(ol[0])], blank_index=0, id_to_label=id_to_label)
                ref = [vocab["id_to_label"][str(t)] for t in item.targets.tolist()]
                all_wer.append(token_wer(ref, pred))

        avg_train = float(np.mean(train_losses)) if train_losses else 0.0
        avg_val = float(np.mean(val_losses)) if val_losses else 0.0
        avg_wer = float(np.mean(all_wer)) if all_wer else 1.0
        entry = {"epoch": epoch, "train_loss": avg_train, "val_loss": avg_val, "val_wer": avg_wer}
        history.append(entry)
        if progress_callback:
            progress_callback(entry)

        if avg_val < best_val:
            best_val = avg_val
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
            torch.save(best_state, bundle_dir / "model.pt")
        else:
            stale += 1
            if stale >= config.patience:
                break

    if best_state:
        model.load_state_dict(best_state)

    model_config = {
        "architecture": "ctc_cnn_bilstm",
        "cnn_channels": config.cnn_channels,
        "hidden_size": config.hidden_size,
        "num_classes": len(vocab["labels"]),
        "blank_index": 0,
    }
    (bundle_dir / "model_config.json").write_text(json.dumps(model_config, indent=2), encoding="utf-8")
    feature_schema = {"columns": SENSOR_COLUMNS, "feature_columns": FEATURE_COLUMNS, "units": {"flex": "0-1", "acc": "g", "gyro": "dps"}}
    (bundle_dir / "feature_schema.json").write_text(json.dumps(feature_schema, indent=2), encoding="utf-8")
    (bundle_dir / "training_settings.json").write_text(json.dumps(config.__dict__, indent=2, default=str), encoding="utf-8")

    emotion_result = {"trained": False, "message": "Emotion model unavailable"}
    emo_labels = [r.emotion_label for r in train_recs if r.emotion_label in {"neutral", "angry"}]
    if emo_labels:
        emo_recs = [load_csv_to_recording(settings.data_dir / r.file_path) for r in train_recs if r.emotion_label in {"neutral", "angry"}]
        emo_model, emo_meta = train_emotion_model(emo_recs, emo_labels, random_state=config.random_seed)
        if emo_model:
            from app.ml.emotion import save_emotion_bundle
            save_emotion_bundle(emo_model, bundle_dir / "emotion_model.pkl", {"source": "prototype_motion_model", **emo_meta.__dict__})
            emotion_result = emo_meta.__dict__

    metrics = {
        "best_val_loss": best_val,
        "final_val_wer": history[-1]["val_wer"] if history else None,
        "epochs_trained": len(history),
        "duration_seconds": time.time() - start,
    }
    (bundle_dir / "validation_results.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (bundle_dir / "bundle_manifest.json").write_text(
        json.dumps({"version": "1.0", "model_type": "ctc_cnn_bilstm", "dataset_id": config.dataset_id}, indent=2),
        encoding="utf-8",
    )
    return {"status": "completed", "history": history, "metrics": metrics, "emotion": emotion_result, "bundle_dir": str(bundle_dir)}
