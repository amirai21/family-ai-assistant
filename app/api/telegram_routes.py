"""
Telegram bot HTTP endpoints.

  POST /telegram/generate-code   ← called by the family-os web/native app
                                   from the Settings "Connect Telegram" CTA.
  POST /telegram/webhook         ← called by Telegram on every update.

Note: this router is mounted at the ROOT, NOT under /api. The family-os
frontend has the URL hardcoded as `${ASSISTANT_URL}/telegram/generate-code`
in src/lib/api/endpoints.ts:211.

Auth model:
  - generate-code: trusts the client-supplied family_id today. This is the
    same trust level the family-os auth helpers extend to localStorage.
    Tightening to a JWT exchange is a follow-up.
  - webhook: anyone-can-call by design — Telegram does. To distinguish real
    Telegram traffic, we check the `X-Telegram-Bot-Api-Secret-Token` header
    against TELEGRAM_BOT_TOKEN's last 16 chars (set as secret on
    setWebhook). Lightweight defense — Telegram's official recommendation.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.services import telegram_service
from app.services.family_os_client import family_os_client
from app.services.intent_parser import (
    FamilyEventIntent,
    GroceryIntent,
    UnsupportedIntent,
    parse_intent,
)
from app.services.telegram_client import send_message

log = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


# ────────────────────────────────────────────────────────────────────────
# generate-code  (called by the family-os frontend)
# ────────────────────────────────────────────────────────────────────────

class GenerateCodeRequest(BaseModel):
    # The frontend sends `family_id` (snake_case) — keep this name.
    family_id: str = Field(..., min_length=8, max_length=64)


class GenerateCodeResponse(BaseModel):
    code: str
    expires_in_minutes: int


@router.post("/generate-code", response_model=GenerateCodeResponse)
async def generate_code(
    body: GenerateCodeRequest,
    db: AsyncSession = Depends(get_db),
) -> GenerateCodeResponse:
    """Mint a one-time code for the user to redeem in Telegram."""
    s = get_settings()
    if not s.telegram_bot_token or not s.openai_api_key:
        # The bot itself wouldn't be able to handle the redemption — fail
        # fast rather than handing out codes that can never be used.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram integration is not configured",
        )
    code, ttl = await telegram_service.generate_code(db, body.family_id)
    return GenerateCodeResponse(code=code, expires_in_minutes=ttl)


# ────────────────────────────────────────────────────────────────────────
# webhook  (called by Telegram)
# ────────────────────────────────────────────────────────────────────────


def _bot_name() -> str:
    return "family_os_assistant_bot"


def _format_event_reply(intent: FamilyEventIntent) -> str:
    def hhmm(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    when = f"{intent.date} בשעה {hhmm(intent.start_minutes)}-{hhmm(intent.end_minutes)}"
    base = f"✅ נוצר אירוע: {intent.title}\n📅 {when}"
    if intent.location:
        base += f"\n📍 {intent.location}"
    return base


def _format_grocery_reply(intent: GroceryIntent) -> str:
    if intent.qty:
        return f"🛒 נוסף לרשימת קניות: {intent.title} ({intent.qty})"
    return f"🛒 נוסף לרשימת קניות: {intent.title}"


async def _handle_text_message(
    db: AsyncSession, chat_id: int, text: str
) -> str:
    """
    Dispatch a free-text message to the right family-os endpoint and return
    the reply text to send back to the user.
    """
    family_id = await telegram_service.get_family_for_chat(db, chat_id)
    if not family_id:
        return (
            "אנא חברו את החשבון מתוך האפליקציה תחילה: "
            "הגדרות → חבר טלגרם, ואז שלחו לי את הקוד עם /start"
        )

    parsed = await parse_intent(text)

    if isinstance(parsed, UnsupportedIntent):
        return f"מצטער, {parsed.reason}"

    try:
        if isinstance(parsed, FamilyEventIntent):
            await family_os_client.create_family_event(
                family_id,
                title=parsed.title,
                start_minutes=parsed.start_minutes,
                end_minutes=parsed.end_minutes,
                is_recurring=False,
                date=parsed.date,
                location=parsed.location,
            )
            return _format_event_reply(parsed)

        if isinstance(parsed, GroceryIntent):
            await family_os_client.create_grocery_item(
                family_id,
                title=parsed.title,
                qty=parsed.qty,
            )
            return _format_grocery_reply(parsed)
    except httpx.HTTPStatusError as exc:
        log.warning("family-os API %s: %s", exc.response.status_code, exc.response.text[:200])
        return (
            f"⚠️ שגיאת שרת ({exc.response.status_code}). "
            f"נסו לנסח אחרת או פנו לתמיכה."
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("unexpected error handling message")
        return f"⚠️ שגיאה לא צפויה: {exc}"

    return "לא הצלחתי להבין. אפשר לנסות לנסח אחרת?"


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Telegram POSTs every chat update here. Always return 200 — Telegram
    retries on non-2xx, which double-sends messages to the user.

    Shape: https://core.telegram.org/bots/api#update
    """
    s = get_settings()

    # Lightweight authenticity check (Telegram-recommended pattern).
    expected = s.telegram_bot_token[-16:] if s.telegram_bot_token else ""
    if expected:
        provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if provided != expected:
            log.warning("webhook: bad secret token, ignoring")
            return {"ok": True}

    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return {"ok": True}

    # /start <code> — redeem the one-time code and bind the chat.
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        code = parts[1].strip() if len(parts) > 1 else ""
        if not code:
            await send_message(
                chat_id,
                "ברוכים הבאים ל-Family OS!\n\n"
                "כדי לחבר את החשבון, פתחו את האפליקציה → הגדרות → חבר טלגרם, "
                "ושלחו לי את הקוד עם הפקודה: /start <CODE>",
            )
            return {"ok": True}

        family_id = await telegram_service.redeem_code(db, code, chat_id)
        if family_id is None:
            await send_message(
                chat_id,
                "❌ קוד לא תקף או פג תוקפו. אנא חזרו לאפליקציה והפיקו קוד חדש.",
            )
        else:
            await send_message(
                chat_id,
                "✅ חיברתי! עכשיו אפשר לשלוח לי בקשות בעברית, למשל:\n"
                "• \"תקבע מסיבת תה ב-15 לאפריל ב-14:00\"\n"
                "• \"תוסיף חלב לקניות\"",
            )
        return {"ok": True}

    if text.startswith("/help"):
        await send_message(
            chat_id,
            "אני העוזר של משפחת Family OS 🏠\n"
            "אפשר לבקש ממני:\n"
            "• לתזמן אירוע: \"תקבע פגישה ביום ראשון ב-10\"\n"
            "• להוסיף לקניות: \"תוסיף לחם וחלב לרשימה\"",
        )
        return {"ok": True}

    # Free-form message → LLM intent → family-os.
    reply = await _handle_text_message(db, chat_id, text)
    await send_message(chat_id, reply)
    return {"ok": True}


# ────────────────────────────────────────────────────────────────────────
# admin: register / re-register the Telegram webhook
# ────────────────────────────────────────────────────────────────────────


class SetWebhookRequest(BaseModel):
    webhook_url: str


@router.post("/admin/set-webhook")
async def admin_set_webhook(
    body: SetWebhookRequest,
    request: Request,
) -> dict[str, Any]:
    """
    Manually trigger setWebhook on Telegram. Call this once after deploy
    (or whenever the Cloud Run URL changes). Auth: Bearer FAMILY_OS_SERVICE_TOKEN.

    Curl:
      curl -X POST https://<assistant>/telegram/admin/set-webhook \\
        -H "Authorization: Bearer $SERVICE_TOKEN" \\
        -H "Content-Type: application/json" \\
        -d '{"webhook_url":"https://<assistant>/telegram/webhook"}'
    """
    s = get_settings()
    if not s.family_os_service_token:
        raise HTTPException(status_code=503, detail="service token not configured")
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {s.family_os_service_token}":
        raise HTTPException(status_code=401, detail="bad service token")

    from app.services.telegram_client import set_webhook

    res = await set_webhook(body.webhook_url)
    if res is None:
        raise HTTPException(status_code=500, detail="setWebhook failed")
    return res
