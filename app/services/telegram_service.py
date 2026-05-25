"""
Persistence helpers for the Telegram bot integration.

Two responsibilities:
  - one-time code lifecycle for the family-os "Connect Telegram" flow
  - long-lived chat_id → family_id binding once a code is redeemed
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.telegram import TelegramChat, TelegramCode

CODE_TTL_MINUTES = 10
CODE_LENGTH = 6  # 6 chars × ~32 entropy ≈ 30 bits — fine for a 10-min window
# Avoid easily-confused chars (0/O, 1/I/L). Telegram users type these manually.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _generate_code_str() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(CODE_LENGTH))


async def generate_code(db: AsyncSession, family_id: str) -> tuple[str, int]:
    """
    Mint a fresh code for `family_id` and persist it.

    Returns (code, expires_in_minutes).
    """
    code = _generate_code_str()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)
    db.add(
        TelegramCode(
            code=code,
            family_id=family_id,
            expires_at=expires_at,
        )
    )
    await db.flush()
    return code, CODE_TTL_MINUTES


async def redeem_code(
    db: AsyncSession, code: str, chat_id: int
) -> str | None:
    """
    Atomically:
      1. find the code (if it exists and isn't expired),
      2. bind chat_id → family_id (upsert),
      3. delete the code so it can't be re-used.

    Returns the bound family_id on success, or None if the code was bad/expired.
    """
    now = datetime.now(timezone.utc)
    code = code.strip().upper()

    row = await db.execute(
        select(TelegramCode).where(TelegramCode.code == code)
    )
    rec = row.scalar_one_or_none()
    if rec is None:
        return None
    # Compare with stored UTC. Some DBs return naive datetimes — coerce.
    expires_at = rec.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        # expired — clean up and reject
        await db.execute(delete(TelegramCode).where(TelegramCode.code == code))
        return None

    family_id = rec.family_id

    # Upsert chat binding. If the chat was already bound to a different
    # family, we replace it — the latest redemption wins.
    stmt = pg_insert(TelegramChat).values(
        chat_id=chat_id, family_id=family_id
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[TelegramChat.chat_id],
        set_={"family_id": family_id},
    )
    await db.execute(stmt)

    # one-time code: delete after redeem
    await db.execute(delete(TelegramCode).where(TelegramCode.code == code))
    return family_id


async def get_family_for_chat(db: AsyncSession, chat_id: int) -> str | None:
    row = await db.execute(
        select(TelegramChat.family_id).where(TelegramChat.chat_id == chat_id)
    )
    return row.scalar_one_or_none()


async def prune_expired_codes(db: AsyncSession) -> int:
    """Best-effort cleanup. Called occasionally to keep the table tidy."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(TelegramCode).where(TelegramCode.expires_at < now)
    )
    return result.rowcount or 0
