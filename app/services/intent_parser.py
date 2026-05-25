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


class GroceryItem(BaseModel):
    title: str
    qty: str | None = None
    # family-os has three shopping-list "shelves": grocery (food),
    # home (cleaning/laundry/paper), health (pharmacy/hygiene). Defaults
    # to grocery — the most common case — but the LLM should override
    # based on Hebrew keywords (see system prompt).
    shopping_category: Literal["grocery", "home", "health"] = "grocery"


class GroceryIntent(BaseModel):
    intent: Literal["grocery"] = "grocery"
    # Always a list, even for a single item — the user can ask for many at
    # once ("תוסיף עגבניות וביצים"). The webhook handler creates one row
    # per item.
    items: list[GroceryItem] = Field(..., min_length=1)


class ChoreIntent(BaseModel):
    intent: Literal["chore"] = "chore"
    title: str
    # Free-text Hebrew name of the assignee, if mentioned. family-os tries
    # to resolve it to a known familyMember; on no match it's stored as
    # free text.
    assigned_to: str | None = None


class NoteIntent(BaseModel):
    intent: Literal["note"] = "note"
    # Required body — the main text of the note. Pinning is always false
    # at creation time; the user pins manually in the app.
    body: str
    # Optional short title — if the user explicitly named one ("פתק עם
    # הכותרת X"). Most casual notes won't have one.
    title: str | None = None


class QueryEventsIntent(BaseModel):
    intent: Literal["query_events"] = "query_events"
    range: Literal["today", "tomorrow", "week"] = "today"


class QueryGroceryIntent(BaseModel):
    intent: Literal["query_grocery"] = "query_grocery"


class QueryChoresIntent(BaseModel):
    intent: Literal["query_chores"] = "query_chores"


class UnsupportedIntent(BaseModel):
    intent: Literal["unsupported"] = "unsupported"
    reason: str


# Discriminated union — Pydantic picks the right one based on the `intent` field.
ParsedIntent = (
    FamilyEventIntent
    | GroceryIntent
    | ChoreIntent
    | NoteIntent
    | QueryEventsIntent
    | QueryGroceryIntent
    | QueryChoresIntent
    | UnsupportedIntent
)


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

2. "grocery" — the user wants to add one or more items to the shopping list.
   Field:
     items — list of objects, one per item the user mentioned. EXTRACT
             EVERY ITEM, not just the first. For "תוסיף עגבניות וביצים"
             return [{"title":"עגבניות"},{"title":"ביצים"}].
             Per-item fields:
                title — short Hebrew name of the item.
                qty   — optional, the quantity as text (e.g. "2", "ליטר",
                         "חבילה", "תריסר"), if the user gave one for
                         THAT specific item.
                shopping_category — ONE of "grocery", "home", "health".
                         Choose PER ITEM based on what it is:
                          - "grocery"  food, drinks, snacks. Examples:
                            חלב, לחם, ביצים, בננות, גבינה, יוגורט,
                            קוטג׳, חומוס, קוקה קולה, שוקולד, אורז, פסטה.
                          - "home"     household, cleaning, laundry, paper,
                            light/electric. Examples: סבון כלים, נייר טואלט,
                            סקוטש, מטליות, אקונומיקה, אבקת כביסה, מרכך,
                            שקיות זבל, נורה, סוללות.
                          - "health"   pharmacy, hygiene, medicine. Examples:
                            תרופות, ויטמינים, שמפו, מרכך שיער, משחת שיניים,
                            דאודורנט, פלסטרים, מסיכות, סבון רחצה.
                         When in doubt, pick "grocery". If the user
                         explicitly says "לרשימת ניקיון"/"לחומרי ניקוי"/
                         "לפארם"/"לרוקחות" — use that category for ALL
                         items in the message.

3. "chore" — the user wants to add a household to-do / chore (something
   one person needs to DO, with no specific time). Distinguish from
   "family_event" by the absence of a clock time and the imperative,
   action-on-a-person feel ("תזכיר ל…", "X צריך…", "תוסיף משימה…").
   Fields:
     title        — short Hebrew action phrase (4–60 chars), starting with
                    a verb when natural ("להוציא את הזבל", "לעבור על
                    חשבונות", "לקנות מתנה ליום הולדת").
     assigned_to  — optional Hebrew name of who should do it, if the user
                    named one ("עודד", "אמא", "הילדים"). Leave null if
                    unspecified or generic ("מישהו"/"כולם").
   Examples:
     "תזכיר לעודד להוציא את הזבל" → {title:"להוציא את הזבל", assigned_to:"עודד"}
     "אני צריך לעבור על החשבונות"  → {title:"לעבור על החשבונות"}
     "תוסיף משימה לקנות מתנה לסבתא" → {title:"לקנות מתנה לסבתא"}

4. "note" — the user wants to save a free-form note / reminder / piece of
   info for the family. Distinguish from "chore" by the absence of an
   action verb directed at a person — notes are pieces of INFORMATION to
   remember, not things TO DO. Triggers: "תרשום פתק…", "תוסיף לפתקים…",
   "תזכור ש…", "תעלה לי במחברת…", "שמור לי ש…".
   Fields:
     body  — the main text of the note. Use what the user actually wants
             to remember, not the framing ("תרשום ש-X" → body="X").
     title — optional short title, ONLY if the user explicitly named one
             ("פתק עם הכותרת X", "תוסיף פתק שכותרתו…"). Otherwise null.
   Examples:
     "תרשום פתק שהמפתחות אצל השכן" → {body:"המפתחות אצל השכן"}
     "תזכור שיש לנו את הוואי-פיי חדש: SSID FamilyOS, סיסמה 12345"
                                  → {body:"וואי-פיי חדש: SSID FamilyOS, סיסמה 12345"}
     "תעלה לי במחברת את מספר השרברב 050-1234567"
                                  → {body:"מספר השרברב 050-1234567"}

5. "query_events" — the user is ASKING what's scheduled (not creating
   anything). Triggers: "מה יש לי היום", "מה יש מחר", "מה התוכניות לשבוע",
   "אילו אירועים יש השבוע", "מה יש בלוח".
   Fields:
     range — ONE of "today" / "tomorrow" / "week".
             Default: "today" if the user said "היום" or didn't specify a
             timeframe; "tomorrow" for "מחר"; "week" for "השבוע" / "בימים
             הקרובים".

6. "query_grocery" — the user is ASKING what's on the shopping list.
   Triggers: "מה ברשימת הקניות", "מה צריך לקנות", "מה יש בקניות",
   "מה חסר במכולת".
   No fields beyond the intent name.

7. "query_chores" — the user is ASKING what tasks are open.
   Triggers: "מה המשימות הפתוחות", "מה יש לי לעשות", "אילו מטלות יש",
   "מה צריך לעשות בבית".
   No fields beyond the intent name.

8. "unsupported" — the request is something else (projects, kids' schedules,
   general chat, deleting/updating existing items). Reply with a short
   Hebrew `reason`, e.g.
   "אני יודע להוסיף ולשאול לגבי אירועים, קניות, משימות ופתקים — שאר הדברים עוד לא".

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
        if intent == "chore":
            return ChoreIntent.model_validate(raw)
        if intent == "note":
            return NoteIntent.model_validate(raw)
        if intent == "query_events":
            return QueryEventsIntent.model_validate(raw)
        if intent == "query_grocery":
            return QueryGroceryIntent.model_validate(raw)
        if intent == "query_chores":
            return QueryChoresIntent.model_validate(raw)
        if intent == "unsupported":
            return UnsupportedIntent.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        return UnsupportedIntent(reason=f"שגיאה בפענוח הבקשה: {exc}")

    return UnsupportedIntent(
        reason="לא הצלחתי להבין את הבקשה. נסו לנסח אחרת."
    )
