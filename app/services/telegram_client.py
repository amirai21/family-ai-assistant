"""
Outbound Telegram Bot API client.

Just enough to reply to a chat. We don't pull in python-telegram-bot for
this because all we need is one HTTP POST.

Docs: https://core.telegram.org/bots/api#sendmessage
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

TELEGRAM_BASE = "https://api.telegram.org"


async def send_message(chat_id: int, text: str) -> dict[str, Any] | None:
    """
    Fire-and-best-effort: send a plain-text reply to `chat_id`. Returns the
    Telegram API JSON response on success, None on any failure (logged).

    Errors are swallowed so the webhook handler can always respond 200 to
    Telegram — otherwise Telegram will retry the same update on next poll,
    which spams the user.
    """
    s = get_settings()
    if not s.telegram_bot_token:
        log.warning("send_message: TELEGRAM_BOT_TOKEN not set, skipping")
        return None
    url = f"{TELEGRAM_BASE}/bot{s.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(url, json={"chat_id": chat_id, "text": text})
            if r.status_code >= 400:
                log.warning("telegram sendMessage %s: %s", r.status_code, r.text[:200])
                return None
            return r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram sendMessage failed: %s", exc)
        return None


async def set_webhook(webhook_url: str) -> dict[str, Any] | None:
    """
    Register the webhook URL with Telegram. Idempotent — calling this with
    the same URL just refreshes the registration.
    """
    s = get_settings()
    if not s.telegram_bot_token:
        return None
    url = f"{TELEGRAM_BASE}/bot{s.telegram_bot_token}/setWebhook"
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json={"url": webhook_url})
            if r.status_code >= 400:
                log.warning("telegram setWebhook %s: %s", r.status_code, r.text[:200])
                return None
            return r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram setWebhook failed: %s", exc)
        return None
