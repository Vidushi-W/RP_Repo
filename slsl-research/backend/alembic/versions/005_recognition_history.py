"""recognition history persistence

Revision ID: 005
Revises: 004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recognition_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="playground"),
        sa.Column("filename", sa.String(255), nullable=False, default=""),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(255), nullable=False, default=""),
        sa.Column("model_version", sa.String(64), nullable=False, default=""),
        sa.Column("english", sa.Text(), nullable=False, default=""),
        sa.Column("gloss_sequence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("emotion", sa.String(32), nullable=True),
        sa.Column("decoder_score", sa.Float(), nullable=True),
        sa.Column("inference_ms", sa.Float(), nullable=True),
        sa.Column("uncertain", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("recognition_messages")
