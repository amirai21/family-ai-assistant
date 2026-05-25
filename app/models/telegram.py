"""
Telegram bot persistence models.

Two tables live on the Assistant's OWN database (the family-os data lives
elsewhere and is reached via the family-os REST API):

  telegram_codes  — one-time 6-char codes minted when a user taps "Connect
                    Telegram" in the family-os UI. The bot consumes them on
                    /start <code>. TTL ~10 minutes.

  telegram_chats  — long-lived binding from a Telegram chat_id to a
                    family-os family_id (UUID). Set on /start <code>;
                    used on every subsequent message to know which family
                    to act on.

Both store the family-os family_id as TEXT (it's a UUID v4 on the family-os
side — we don't need PG's `uuid` type here, plain text is enough).
"""
from datetime import datetime

from sqlalchemy import String, BigInteger, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.timestamps import TimestampMixin


class TelegramCode(Base, TimestampMixin):
    """One-time code redeemable via the Telegram bot's /start handler."""
    __tablename__ = "telegram_codes"

    # 6-char alphanumeric — short enough to type into Telegram, long enough
    # to be unguessable for a 10-minute window.
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TelegramChat(Base, TimestampMixin):
    """
    Binding from a Telegram chat to a family-os family.

    Telegram chat_id is a 64-bit signed int (negative for group chats),
    so we use BigInteger.
    """
    __tablename__ = "telegram_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


Index("ix_telegram_codes_expires_at", TelegramCode.expires_at)
