"""Load sensor recordings for training — sensor features only, no labels in tensors."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset

from app.core.config import settings
from app.ml.preprocessing import NormalizationConfig, resample_recording, smooth_features
from app.ml.vocabulary import encode_labels
from app.models.dataset import Recording
from app.sensors.csv_source import load_csv_to_recording


@dataclass
class SequenceItem:
    features: torch.Tensor
    targets: torch.Tensor
    input_length: int
    target_length: int
    recording_id: str


class RecordingSequenceDataset(Dataset):
    def __init__(
        self,
        recordings: list[Recording],
        label_to_id: dict[str, int],
        norm: NormalizationConfig,
        min_output_frames_per_label: int = 2,
    ) -> None:
        self.items: list[SequenceItem] = []
        for rec in recordings:
            if not rec.ordered_sign_labels:
                continue
            path = settings.data_dir / rec.file_path
            sensor = load_csv_to_recording(path, source_name=rec.recording_id)
            resampled = resample_recording(sensor, norm.target_sample_rate_hz)
            x = smooth_features(resampled.to_feature_matrix())
            x = norm.normalize(x)
            targets = encode_labels(rec.ordered_sign_labels, label_to_id)
            if not targets:
                continue
            min_frames = len(targets) * min_output_frames_per_label
            if x.shape[0] // 2 < min_frames:
                raise ValueError(
                    f"Recording {rec.recording_id} has insufficient time resolution "
                    f"({x.shape[0]} frames) for {len(targets)} labels (need >= {min_frames * 2})."
                )
            self.items.append(
                SequenceItem(
                    features=torch.from_numpy(x.astype(np.float32)),
                    targets=torch.tensor(targets, dtype=torch.long),
                    input_length=x.shape[0],
                    target_length=len(targets),
                    recording_id=rec.recording_id,
                )
            )

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> SequenceItem:
        return self.items[idx]


def collate_sequences(batch: list[SequenceItem]):
    features = [b.features for b in batch]
    targets = [b.targets for b in batch]
    input_lengths = torch.tensor([b.input_length for b in batch], dtype=torch.long)
    target_lengths = torch.tensor([b.target_length for b in batch], dtype=torch.long)
    padded_x = pad_sequence(features, batch_first=True)
    padded_y = pad_sequence(targets, batch_first=True, padding_value=0)
    return padded_x, padded_y, input_lengths, target_lengths
