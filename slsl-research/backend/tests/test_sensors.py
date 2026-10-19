from app.sensors.csv_source import HardwareSensorSource as HardwareGloveSource
from app.sensors.frame import NUM_FEATURES, SensorFrame


def test_sensor_frame_shape():
    frame = SensorFrame(timestamp_ms=0.0, features=tuple(0.0 for _ in range(NUM_FEATURES)))
    assert len(frame.features) == NUM_FEATURES


def test_hardware_not_available():
    assert HardwareGloveSource.is_available() is False
