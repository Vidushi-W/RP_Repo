"""CSV recording and playback adapters."""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Union

import pandas as pd

from app.core.config import FEATURE_COLUMNS, SENSOR_COLUMNS
from app.sensors.base import PlaybackSensorSource, SensorSource
from app.sensors.frame import SensorFrame, SensorRecording


def load_csv_to_recording(path_or_file: Union[str, Path, BinaryIO, bytes], source_name: str = "csv") -> SensorRecording:
    if isinstance(path_or_file, (bytes, bytearray)):
        path_or_file = BytesIO(path_or_file)
    df = pd.read_csv(path_or_file)
    missing = [c for c in SENSOR_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing sensor columns: {missing}")
    df = df[SENSOR_COLUMNS].sort_values("timestamp_ms").drop_duplicates("timestamp_ms", keep="first")
    frames = [
        SensorFrame(timestamp_ms=float(row["timestamp_ms"]), features=tuple(float(row[c]) for c in FEATURE_COLUMNS))
        for _, row in df.iterrows()
    ]
    return SensorRecording(frames=frames, source_name=source_name)


class CsvRecordingSource(SensorSource):
    def __init__(self, filepath: Union[str, Path, BinaryIO, bytes], source_name: str | None = None) -> None:
        self.filepath = str(filepath) if not isinstance(filepath, (bytes, bytearray)) else "upload"
        self._recording = load_csv_to_recording(filepath, source_name=source_name or self.filepath)

    def source_type(self) -> str:
        return "csv_recording"

    def read_recording(self) -> SensorRecording:
        return self._recording


class CsvPlaybackSource(PlaybackSensorSource):
    def __init__(self, filepath: Union[str, Path, BinaryIO, bytes], speed: float = 1.0, source_name: str | None = None) -> None:
        recording = load_csv_to_recording(filepath, source_name=source_name or str(filepath))
        super().__init__(recording, speed=speed)


class HardwareSensorSource(SensorSource):
    def source_type(self) -> str:
        return "hardware_gloves"

    def read_recording(self) -> SensorRecording:
        raise NotImplementedError("Physical glove adapter is not connected.")

    @staticmethod
    def is_available() -> bool:
        return False
