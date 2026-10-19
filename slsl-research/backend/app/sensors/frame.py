"""Common synchronized two-glove sensor frame (22 features)."""

from dataclasses import dataclass

FEATURE_NAMES = [
    "left_flex_1", "left_flex_2", "left_flex_3", "left_flex_4", "left_flex_5",
    "left_acc_x_g", "left_acc_y_g", "left_acc_z_g",
    "left_gyro_x_dps", "left_gyro_y_dps", "left_gyro_z_dps",
    "right_flex_1", "right_flex_2", "right_flex_3", "right_flex_4", "right_flex_5",
    "right_acc_x_g", "right_acc_y_g", "right_acc_z_g",
    "right_gyro_x_dps", "right_gyro_y_dps", "right_gyro_z_dps",
]
NUM_FEATURES = 22


@dataclass(frozen=True)
class SensorFrame:
    timestamp_ms: float
    features: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.features) != NUM_FEATURES:
            raise ValueError(f"Expected {NUM_FEATURES} features, got {len(self.features)}")
