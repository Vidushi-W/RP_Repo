"""training registry schema

Revision ID: 003
Revises: 002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("training_jobs") as batch:
        batch.add_column(sa.Column("model_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("training_mode", sa.String(32), server_default="fresh", nullable=False))
        batch.add_column(sa.Column("source_model_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("config_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("progress_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("pid", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("current_epoch", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("total_epochs", sa.Integer(), server_default="20", nullable=False))
        batch.add_column(sa.Column("train_loss", sa.Float(), nullable=True))
        batch.add_column(sa.Column("val_loss", sa.Float(), nullable=True))
        batch.add_column(sa.Column("val_wer", sa.Float(), nullable=True))
        batch.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("ml_models") as batch:
        batch.add_column(sa.Column("architecture", sa.String(64), server_default="ctc_cnn_bilstm", nullable=False))
        batch.add_column(sa.Column("dataset_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("dataset_version", sa.String(32), nullable=True))
        batch.add_column(sa.Column("provenance", sa.String(32), server_default="synthetic", nullable=False))
        batch.add_column(sa.Column("training_job_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("bundle_path", sa.String(512), nullable=True))
        batch.add_column(sa.Column("vocabulary_json", sa.Text(), server_default="[]", nullable=False))
        batch.add_column(sa.Column("feature_schema_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("validation_metrics_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("emotion_available", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column("emotion_model_path", sa.String(512), nullable=True))
        batch.add_column(sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("ml_models") as batch:
        for col in [
            "architecture", "dataset_id", "dataset_version", "provenance", "training_job_id",
            "bundle_path", "vocabulary_json", "feature_schema_json", "validation_metrics_json",
            "emotion_available", "emotion_model_path", "is_archived",
        ]:
            batch.drop_column(col)
    with op.batch_alter_table("training_jobs") as batch:
        for col in [
            "model_id", "training_mode", "source_model_id", "config_json", "progress_json",
            "pid", "current_epoch", "total_epochs", "train_loss", "val_loss", "val_wer",
            "started_at", "completed_at",
        ]:
            batch.drop_column(col)
