"""Sensor source adapter interfaces."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator

from app.sensors.frame import SensorFrame


class SensorSource(ABC):
    """Produces normalized SensorFrame objects from CSV, playback, or hardware."""

    @abstractmethod
    def source_type(self) -> str:
        ...

    @abstractmethod
    def iter_frames(self) -> Iterator[SensorFrame]:
        ...

    async def stream_frames(self) -> AsyncIterator[SensorFrame]:
        for frame in self.iter_frames():
            yield frame

    def close(self) -> None:
        pass


class CsvRecordingSource(SensorSource):
    """CSV file recording adapter — implementation deferred to Step 2."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath

    def source_type(self) -> str:
        return "csv_recording"

    def iter_frames(self) -> Iterator[SensorFrame]:
        raise NotImplementedError("CSV import is not implemented in Step 1.")


class CsvPlaybackSource(SensorSource):
    """Timed CSV playback adapter — implementation deferred to Step 2."""

    def __init__(self, filepath: str, speed: float = 1.0) -> None:
        self.filepath = filepath
        self.speed = speed

    def source_type(self) -> str:
        return "csv_playback"

    def iter_frames(self) -> Iterator[SensorFrame]:
        raise NotImplementedError("CSV playback is not implemented in Step 1.")


class HardwareGloveSource(SensorSource):
    """Future physical glove adapter — not connected."""

    def source_type(self) -> str:
        return "hardware_gloves"

    def iter_frames(self) -> Iterator[SensorFrame]:
        raise NotImplementedError("Physical glove adapter is not connected.")

    @staticmethod
    def is_available() -> bool:
        return False
