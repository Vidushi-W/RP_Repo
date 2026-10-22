"""Application settings loaded from environment variables."""

import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent

SENSOR_COLUMNS = [
    "timestamp_ms",
    "left_flex_1", "left_flex_2", "left_flex_3", "left_flex_4", "left_flex_5",
    "left_acc_x_g", "left_acc_y_g", "left_acc_z_g",
    "left_gyro_x_dps", "left_gyro_y_dps", "left_gyro_z_dps",
    "right_flex_1", "right_flex_2", "right_flex_3", "right_flex_4", "right_flex_5",
    "right_acc_x_g", "right_acc_y_g", "right_acc_z_g",
    "right_gyro_x_dps", "right_gyro_y_dps", "right_gyro_z_dps",
]
FEATURE_COLUMNS = [c for c in SENSOR_COLUMNS if c != "timestamp_ms"]
NOMINAL_SAMPLE_RATE_HZ = 50
RANDOM_SEED = 42

VOCABULARY = ["I", "YOU", "NEED", "WANT", "WATER", "FOOD", "HELP", "GO", "HOME", "STOP"]

MANIFEST_CANONICAL_COLUMNS = {
    "recording_id": ["recording_id", "id", "sample_id"],
    "filepath": ["filepath", "file", "file_path", "path"],
    "signer_id": ["signer_id", "signer"],
    "provenance": ["provenance", "source_type", "source"],
    "ordered_sign_labels": ["ordered_sign_labels", "sign_labels", "labels", "gloss_sequence"],
    "emotion_label": ["emotion_label", "emotion"],
    "reference_english_sentence": ["reference_english_sentence", "sentence_reference", "english_sentence"],
    "split": ["split", "dataset_split"],
    "collection_date": ["collection_date", "recorded_at", "date"],
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_ROOT / ".env"), env_prefix="SLSL_", extra="ignore")

    app_name: str = "SLSL AI Studio"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'slsl_studio.db').as_posix()}"
    data_dir: Path = PROJECT_ROOT / "data"
    artifacts_dir: Path = PROJECT_ROOT / "artifacts"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_bytes: int = 50 * 1024 * 1024
    sentence_model_dir: Path = PROJECT_ROOT / "local_models" / "qwen2.5-0.5b-instruct"
    sentence_timeout_seconds: int = 120
    translation_model_dir: Path = PROJECT_ROOT / 'local_models' / 'm2m100-418m'
    sinhala_voice_dir: Path = PROJECT_ROOT / 'local_models' / 'dilu-sinhala'
    speech_timeout_seconds: int = 120

    @property
    def cors_origins_list(self) -> list[str]:
        value = self.cors_origins.strip()
        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def datasets_dir(self) -> Path:
        return self.data_dir / "datasets"

    @property
    def imports_dir(self) -> Path:
        return self.data_dir / "imports"

    @property
    def recordings_staging_dir(self) -> Path:
        return self.data_dir / "imports" / "staging"


settings = Settings()
