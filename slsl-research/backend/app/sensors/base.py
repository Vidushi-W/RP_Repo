"""Sensor source adapter interfaces."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator, Optional

from app.sensors.frame import SensorFrame, SensorRecording


class SensorSource(ABC):
    @abstractmethod
    def source_type(self) -> str:
        ...

    @abstractmethod
    def read_recording(self) -> SensorRecording:
        ...

    def iter_frames(self) -> Iterator[SensorFrame]:
        return iter(self.read_recording().frames)

    async def stream_frames(self) -> AsyncIterator[SensorFrame]:
        for frame in self.iter_frames():
            yield frame

    def close(self) -> None:
        pass


class PlaybackSensorSource(SensorSource):
    def __init__(self, recording: SensorRecording, speed: float = 1.0) -> None:
        self._recording = recording
        self.speed = speed
        self._index = 0
        self._paused = False
        self._stopped = False

    def read_recording(self) -> SensorRecording:
        return self._recording

    def source_type(self) -> str:
        return "csv_playback"

    def reset(self) -> None:
        self._index = 0
        self._paused = False
        self._stopped = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stopped = True

    def next_frame(self) -> Optional[SensorFrame]:
        if self._stopped or self._index >= len(self._recording.frames):
            return None
        frame = self._recording.frames[self._index]
        self._index += 1
        return frame
