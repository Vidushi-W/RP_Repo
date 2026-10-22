"""dataset management schema

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("datasets") as batch:
        batch.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("status", sa.String(32), nullable=False, server_default="draft"))
        batch.add_column(sa.Column("current_version", sa.String(32), nullable=False, server_default="1.0.0"))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)")))
        batch.alter_column("provenance", type_=sa.String(32), existing_type=sa.Text())
        batch.drop_column("source_type")

    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("split_manifest_path", sa.String(512), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recordings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recording_id", sa.String(128), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("dataset_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("signer_id", sa.String(128), nullable=False, server_default="UNKNOWN"),
        sa.Column("provenance", sa.String(32), nullable=False, server_default="synthetic"),
        sa.Column("ordered_sign_labels", sa.String(512), nullable=False, server_default=""),
        sa.Column("emotion_label", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("reference_english_sentence", sa.Text(), nullable=False, server_default=""),
        sa.Column("split", sa.String(16), nullable=False, server_default="unassigned"),
        sa.Column("collection_date", sa.String(32), nullable=True),
        sa.Column("group_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frame_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_rate_hz", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_protected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "recording_id", "dataset_version", name="uq_recording_version"),
    )
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("step", sa.String(64), nullable=False, server_default="select_files"),
        sa.Column("source_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("report_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("import_jobs")
    op.drop_table("recordings")
    op.drop_table("dataset_versions")
    with op.batch_alter_table("datasets") as batch:
        batch.add_column(sa.Column("source_type", sa.String(64), server_default="synthetic"))
        batch.drop_column("updated_at")
        batch.drop_column("current_version")
        batch.drop_column("status")
        batch.drop_column("description")
