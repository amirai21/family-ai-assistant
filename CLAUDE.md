# CLAUDE.md (family-ai-assistant)

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## What this is

The Telegram-bot brain for **Family OS** — a Hebrew RTL family-management app. This service receives Telegram webhook updates, parses Hebrew natural language with OpenAI, and creates events / grocery items in family-os via its REST API.

**This is the sibling repo to `family-os`** (`github.com/amirkubla/family-os`). The user's main repo on disk is `/Users/amirkoblyansky/family-os`. That CLAUDE.md has the broader architecture; this one focuses on the Assistant.

| | |
|---|---|
| **Stack** | FastAPI · SQLAlchemy 2.0 (async + asyncpg) · Alembic · Pydantic v2 · OpenAI · httpx |
| **Hosted at** | Cloud Run `family-ai-assistant` in GCP project `family-ai-assistant-476208`, region `me-west1` |
| **Public URL** | https://family-ai-assistant-m7braajria-zf.a.run.app |
| **DB** | OWN Neon Postgres (not family-os's). Stores telegram_codes + telegram_chats bindings only. |
| **Account** | Personal `amirkubla@gmail.com`. Switch via `gcloud config set account amirkubla@gmail.com`. |

## Two-repo data flow

```
family-os frontend  ──tap "חבר טלגרם"──►  Assistant POST /telegram/generate-code
                                                        │
                                                        ▼
                                          mint code, store in own Neon
                                                        │
       ◄─{code, ttl}─────────────────────────────────────┘
       │
       opens https://t.me/family_os_assistant_bot?start=<code>
                                  │
                                  ▼
                          Telegram POST /telegram/webhook (this service)
                                  │
                                  ▼
                          /start <code> → bind chat_id → family_id
                                  │
                                  ▼
                          Free text → OpenAI gpt-4o-mini → intent
                                  │
                                  ▼
                          ┌─ family_event ─►  POST family-os /v1/internal/family/:fid/family-events
                          └─ grocery ──────►  POST family-os /v1/internal/family/:fid/grocery
                                  │
                                  ▼
                          Telegram sendMessage with confirmation
```

**The Assistant never touches the family-os DB directly.** Source of truth for family data is family-os; we call its REST API with `Authorization: Bearer ${FAMILY_OS_SERVICE_TOKEN}`.

## Layout

```
app/
  main.py                          FastAPI bootstrap, router registration
  core/
    config.py                      Settings (env vars). New ones: openai_api_key,
                                   openai_model, telegram_bot_token,
                                   family_os_api_url, family_os_service_token
    database.py                    Async SQLAlchemy engine + session factory
  models/
    telegram.py                    TelegramCode, TelegramChat
    family.py, family_member.py,   (pre-existing, used by other routes)
    task.py, reminder.py, ...
  api/
    telegram_routes.py             /telegram/generate-code, /webhook, /admin/set-webhook
    family_routes.py, ...          (pre-existing CRUD)
  services/
    intent_parser.py               OpenAI Hebrew NL → discriminated Pydantic union
    family_os_client.py            httpx async client to family-os REST API
    telegram_client.py             Outbound sendMessage + setWebhook helpers
    telegram_service.py            Code gen + atomic redeem + chat binding
alembic/
  env.py                           Imports all models so autogenerate sees them
  versions/0002_telegram_tables.py
```

The `/telegram/*` router is mounted at the ROOT of the FastAPI app, NOT under `/api`. The family-os frontend hardcodes `${ASSISTANT_URL}/telegram/generate-code`, and Telegram POSTs to whatever absolute URL we register with `setWebhook`. Other routes (user, family, task, reminder…) stay under `/api`.

## Commands

```bash
# Local dev (against the prod Neon DB unless you override DATABASE_URL)
uvicorn app.main:app --reload --port 8000

# Apply migrations (against whatever DATABASE_URL resolves to)
DATABASE_URL='...' alembic upgrade head

# Generate a new migration after editing models
alembic revision --autogenerate -m "describe change"
```

## Deploy

GitHub Actions on push to `master` (see `.github/workflows/deploy.yml`):
1. Build Docker image, tag with short SHA + `:latest`
2. Push to Artifact Registry
3. `gcloud run deploy --update-env-vars "DATABASE_URL=..."` (additive — never `--set-env-vars`)

**Migrations are NOT run automatically.** Apply them manually before pushing schema-affecting code:
```bash
DATABASE_URL='<assistant-neon-url>' alembic upgrade head
```

The deploy SA is `gha-deployer@family-ai-assistant-476208.iam.gserviceaccount.com`, authenticated via Workload Identity Federation.

## Env vars on Cloud Run

| Name | Source | Purpose |
|---|---|---|
| `DATABASE_URL` | plain env (GH secret `DATABASE_URL` via deploy.yml `--update-env-vars`) | Assistant's own Neon. Should move to Secret Manager eventually. |
| `OPENAI_API_KEY` | Secret Manager `OPENAI_API_KEY:latest` | gpt-4o-mini intent extraction |
| `OPENAI_MODEL` | plain (default `gpt-4o-mini`) | LLM model name |
| `TELEGRAM_BOT_TOKEN` | Secret Manager `TELEGRAM_BOT_TOKEN:latest` | From `@BotFather` |
| `FAMILY_OS_API_URL` | plain | `https://family-os-4ilvxexrha-zf.a.run.app` |
| `FAMILY_OS_SERVICE_TOKEN` | plain (rotate together with family-os's `SERVICE_TOKEN`) | Bearer for `/v1/internal/*` calls |

To list names without leaking values:
```bash
gcloud run services describe family-ai-assistant \
  --project=family-ai-assistant-476208 --region=me-west1 \
  --format="value(spec.template.spec.containers[0].env[].name)"
```

## Telegram setup

**Bot account**: `@family_os_assistant_bot`. Token in Secret Manager. To rotate via BotFather: `/revoke` → choose the bot → copy new token → pipe to `gcloud secrets versions add` (NOT inline).

**Webhook registration** (one-shot after deploy or URL change):
```bash
WEBHOOK="https://family-ai-assistant-m7braajria-zf.a.run.app/telegram/webhook"
TOKEN=$(grep -oE '[0-9]{8,12}:[A-Za-z0-9_-]{30,}' /Users/amirkoblyansky/telegramtoken | head -1)
SECRET="${TOKEN: -16}"
curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$WEBHOOK\",\"secret_token\":\"$SECRET\",\"drop_pending_updates\":true}"
unset TOKEN SECRET
```

The webhook handler checks `X-Telegram-Bot-Api-Secret-Token` against the last 16 chars of the bot token (Telegram-recommended authenticity pattern). Without it, the handler logs a warning and silently 200s — Telegram would otherwise retry.

## Intent parser

`app/services/intent_parser.py` calls OpenAI Chat Completions with `response_format={"type":"json_object"}` and a Hebrew system prompt. The model returns one of three intents (discriminated by the `intent` field):

- `FamilyEventIntent` — `title`, `date` (YYYY-MM-DD), `start_minutes`, `end_minutes`, optional `location`
- `GroceryIntent` — `items: list[GroceryItem]` where each item has `title`, optional `qty`, and `shopping_category: Literal["grocery","home","health"]`
- `UnsupportedIntent` — `reason` (short Hebrew refusal)

If the LLM call fails or returns malformed JSON, we degrade to `UnsupportedIntent` with the error message — the user always gets a graceful reply.

To add a new intent: extend the Union + add a schema class + extend the system prompt with examples + add a dispatch branch in `telegram_routes._handle_text_message` + (if it writes) add a new internal route on the family-os side.

## QA pattern: synthetic webhook driver

Test the bot end-to-end without typing in Telegram. POST a Telegram `Update` JSON to `/telegram/webhook` with the right `X-Telegram-Bot-Api-Secret-Token`:

```python
import json, subprocess, requests, random, time
BOT_TOKEN = open('/Users/amirkoblyansky/telegramtoken').read().strip().split()[-1]  # naive — use a regex in real code
SECRET = BOT_TOKEN[-16:]
CHAT_ID = 386781351   # the maintainer's chat

def send(text):
    body = {
      "update_id": random.randrange(1, 10**9),
      "message": {"message_id": random.randrange(1, 10**9),
                  "from": {"id": CHAT_ID, "first_name": "tester", "is_bot": False},
                  "chat": {"id": CHAT_ID, "type": "private"},
                  "date": int(time.time()),
                  "text": text}
    }
    r = requests.post("https://family-ai-assistant-m7braajria-zf.a.run.app/telegram/webhook",
                      headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
                      json=body)
    return r.status_code
```

The bot WILL send real replies to the bound Telegram chat (acceptable as long as the runner controls that chat). Verify by diffing rows in the family-os DB before/after.

## Security checklist

- **Never** `--set-env-vars` in deploy.yml — only `--update-env-vars` (additive). The former silently wipes plain env vars and broke the bot on 2026-05-25.
- **New secrets** go in Secret Manager, piped from file via `gcloud secrets create --data-file=-`. Mount via `--update-secrets`. Never inline.
- **The bot token** is the keys-to-the-kingdom for the bot. If it leaks: `@BotFather /revoke` → invalidates old token, generates new. The bot retains its name/username/chat history; you just need to refresh the Secret Manager value.
- **`FAMILY_OS_SERVICE_TOKEN` compromise** = anyone can write to any family in family-os. To rotate: update on both sides simultaneously (family-os's `SERVICE_TOKEN` env var and the Assistant's `FAMILY_OS_SERVICE_TOKEN`).
