"""add family_member_id to telegram_chats

Revision ID: 0003_telegram_chat_member_id
Revises: 0002_telegram_tables
Create Date: 2026-05-26 09:00:00.000000

Adds the optional binding of a Telegram chat to a specific family member
(by family-os UUID). Lets the bot answer "my tasks" without having to ask
who's speaking on every message. Set lazily via the /me command — existing
rows stay NULL and the bot falls back to "all family chores" with a hint
to set /me.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_telegram_chat_member_id"
down_revision: Union[str, Sequence[str], None] = "0002_telegram_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_chats",
        sa.Column("family_member_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_chats", "family_member_id")
