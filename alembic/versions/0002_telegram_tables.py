"""add telegram_codes and telegram_chats tables

Revision ID: 0002_telegram_tables
Revises: initial_schema_with_recurring
Create Date: 2026-05-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_telegram_tables"
down_revision: Union[str, Sequence[str], None] = "initial_schema_with_recurring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_codes",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("family_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index("ix_telegram_codes_family_id", "telegram_codes", ["family_id"])
    op.create_index("ix_telegram_codes_expires_at", "telegram_codes", ["expires_at"])

    op.create_table(
        "telegram_chats",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("family_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("chat_id"),
    )
    op.create_index("ix_telegram_chats_family_id", "telegram_chats", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_telegram_chats_family_id", table_name="telegram_chats")
    op.drop_table("telegram_chats")
    op.drop_index("ix_telegram_codes_expires_at", table_name="telegram_codes")
    op.drop_index("ix_telegram_codes_family_id", table_name="telegram_codes")
    op.drop_table("telegram_codes")
