"""Neural network architectures."""

import torch
import torch.nn as nn


class CnnBiLstmBackbone(nn.Module):
    def __init__(self, input_size: int = 22, cnn_channels: int = 32, hidden_size: int = 32) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(input_size, cnn_channels, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.Conv1d(cnn_channels, cnn_channels, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2),
        )
        self.lstm = nn.LSTM(cnn_channels, hidden_size, num_layers=1, batch_first=True, bidirectional=True)
        self.time_reduction = 2

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = self.conv(x)
        x = x.transpose(1, 2)
        x, _ = self.lstm(x)
        return x


class CtcSignModel(nn.Module):
    def __init__(self, num_classes: int, input_size: int = 22, cnn_channels: int = 32, hidden_size: int = 32) -> None:
        super().__init__()
        self.backbone = CnnBiLstmBackbone(input_size, cnn_channels, hidden_size)
        self.classifier = nn.Linear(hidden_size * 2, num_classes)
        self.time_reduction = 2

    def forward(self, x: torch.Tensor, input_lengths: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.backbone(x)
        logits = self.classifier(features)
        if input_lengths is None:
            input_lengths = torch.full((x.shape[0],), x.shape[1], dtype=torch.long, device=x.device)
        output_lengths = torch.clamp(input_lengths // self.time_reduction, min=1)
        return logits, output_lengths
