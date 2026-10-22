"""evaluation system schema

Revision ID: 004
Revises: 003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("evaluation_runs") as batch:
        batch.add_column(sa.Column("dataset_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("dataset_version", sa.String(32), nullable=True))
        batch.add_column(sa.Column("split_used", sa.String(16), server_default="test", nullable=False))
        batch.add_column(sa.Column("provenance", sa.String(32), server_default="synthetic", nullable=False))
        batch.add_column(sa.Column("config_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("results_path", sa.String(512), nullable=True))
        batch.add_column(sa.Column("word_error_rate", sa.Float(), nullable=True))
        batch.add_column(sa.Column("metrics_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("message", sa.Text(), server_default="", nullable=False))
        batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("evaluation_runs") as batch:
        batch.drop_column("completed_at")
        batch.drop_column("message")
        batch.drop_column("metrics_json")
        batch.drop_column("word_error_rate")
        batch.drop_column("results_path")
        batch.drop_column("config_json")
        batch.drop_column("provenance")
        batch.drop_column("split_used")
        batch.drop_column("dataset_version")
        batch.drop_column("dataset_id")
