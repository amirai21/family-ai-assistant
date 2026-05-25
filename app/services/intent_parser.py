"""
Hebrew natural-language → structured intent, via OpenAI.

The Telegram bot accepts free-form Hebrew text like:
  "תקבע לנו מסיבת תה ב-15 לאפריל ב-14:00"
  "תוסיף חלב לקניות"
  "תזכיר לי לקנות סוללות בערב"

We ask the model to pick ONE intent and emit a strict JSON envelope. If the
text doesn't match any supported intent, the model returns
`{"intent": "unsupported", "reason": "..."}` and the bot replies politely.

We keep the schema as tight as possible so the bot can route + call the
family-os API without further parsing.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings

TZ = ZoneInfo("Asia/Jerusalem")


class FamilyEventIntent(BaseModel):
    intent: Literal["family_event"] = "family_event"
    title: str
    date: str = Field(..., description='ISO YYYY-MM-DD in Asia/Jerusalem')
    start_minutes: int = Field(..., ge=0, le=1439)
    end_minutes: int = Field(..., ge=0, le=1440)
    location: str | None = None


class GroceryIntent(BaseModel):
    intent: Literal["grocery"] = "grocery"
    title: str
    qty: str | None = None


class UnsupportedIntent(BaseModel):
    intent: Literal["unsupported"] = "unsupported"
    reason: str


# Discriminated union — Pydantic picks the right one based on the `intent` field.
ParsedIntent = FamilyEventIntent | GroceryIntent | UnsupportedIntent


SYSTEM_PROMPT = """\
You are an extraction layer for a Hebrew-language family-coordination bot.

The user sends free-form Hebrew text. Your job: choose EXACTLY ONE intent
from the list below and emit JSON matching that intent's schema.

Intents:

1. "family_event" — the user wants to schedule a one-time event for the
   whole family (a meeting, a meal, an appointment, etc.).
   Fields:
     title          — short Hebrew title (4–40 chars).
     date           — "YYYY-MM-DD" in Asia/Jerusalem timezone.
                       Resolve relative dates ("מחר", "ביום שלישי הבא",
                       "15 לאפריל") against the CURRENT_DATE you'll be given.
                       If the year is unspecified and the date already
                       passed this year, use NEXT year.
     start_minutes  — minutes since midnight (0–1439).
                       If the user gives a time range, this is the start.
                       If only one time is given, set duration = 60 min.
                       If no time is given, default to 18:00 (1080) and
                       21:00 (1260).
     end_minutes    — minutes since midnight (1–1440). Must be > start_minutes.
     location       — optional, only if explicitly stated.

2. "grocery" — the user wants to add an item to the shopping list.
   Fields:
     title — short Hebrew name of the item.
     qty   — optional, the quantity as text (e.g. "2", "ליטר", "חבילה").

3. "unsupported" — the request is something else (chores, projects, notes,
   general chat). Reply with a short Hebrew `reason` the bot will show the
   user, e.g. "אני יודע כרגע רק לתזמן אירועים ולהוסיף קניות".

Rules:
- ALWAYS return valid JSON matching ONE of the schemas above.
- NEVER add fields not in the schema.
- Hebrew text only in user-visible fields.
- If multiple intents could apply, pick the one the user spent more words
  describing.
"""


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        s = get_settings()
        _client = AsyncOpenAI(api_key=s.openai_api_key)
    return _client


def _now_in_jerusalem() -> datetime:
    return datetime.now(timezone.utc).astimezone(TZ)


async def parse_intent(text: str) -> ParsedIntent:
    """
    Send `text` to OpenAI with the system prompt and parse the response.
    On any failure (network, malformed JSON, missing fields), return an
    UnsupportedIntent so the bot can fail gracefully.
    """
    s = get_settings()
    if not s.openai_api_key:
        return UnsupportedIntent(
            reason="השירות לא מוגדר כראוי (חסר מפתח OpenAI)."
        )

    now = _now_in_jerusalem()
    user_msg = (
        f"CURRENT_DATE: {now.strftime('%Y-%m-%d')} "
        f"(local time {now.strftime('%H:%M')} Asia/Jerusalem)\n\n"
        f"USER_TEXT:\n{text.strip()}"
    )

    try:
        resp = await _get_client().chat.completions.create(
            model=s.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        content = resp.choices[0].message.content or "{}"
        raw: dict[str, Any] = json.loads(content)
    except Exception as exc:  # noqa: BLE001
        return UnsupportedIntent(reason=f"שגיאת LLM: {exc}")

    intent = raw.get("intent")
    try:
        if intent == "family_event":
            return FamilyEventIntent.model_validate(raw)
        if intent == "grocery":
            return GroceryIntent.model_validate(raw)
        if intent == "unsupported":
            return UnsupportedIntent.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        return UnsupportedIntent(reason=f"שגיאה בפענוח הבקשה: {exc}")

    return UnsupportedIntent(
        reason="לא הצלחתי להבין את הבקשה. נסו לנסח אחרת."
    )
