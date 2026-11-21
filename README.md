# LLM Chatbot with Key Failover and Response Caching

React + FastAPI + SQLite chatbot. LiteLLM is the gateway: it provides the API-key pool with automatic
failover, and the built-in response cache. Multi-turn history lives in SQLite.

**Stack:** React 18 (Vite) · FastAPI · LiteLLM 1.110.2 · SQLite · Docker (multi-stage) · pytest

```
.
├── backend/            FastAPI app (app/), tests (tests/), Dockerfile
│   └── app/            main.py (routes) · gateway.py (LiteLLM) · db.py · config.py · schemas.py · simulation.py
├── frontend/           React UI (src/), Dockerfile (nginx), nginx.conf
├── docker-compose.yml  both services + named volume `app_data` mounted at /data
├── Makefile            make up / make down
├── .env.example        every variable, placeholder values
└── docs/DEPLOYMENT.md  step-by-step deployment guide
```

## 1. Live URLs

| Component | URL |
|---|---|
| Frontend | https://ai-chatbot-vert-zeta-96.vercel.app |
| Backend API Base URL | https://ai-chatbot-zdyj.onrender.com |
| Backend Health Check | https://ai-chatbot-zdyj.onrender.com/health |
| GitHub Repository | https://github.com/vinayak15khandelwal/ai-chatbot |

The frontend is deployed on Vercel and communicates with the FastAPI backend deployed on Render.

## 2. Run locally: with Docker and without

### With Docker (needs Docker with Compose v2)

```bash
cp .env.example .env        # then put at least 2 real keys in LLM_API_KEYS (comma-separated)
make up                     # frontend http://localhost:3000 · backend http://localhost:8000
make down                   # stop; the SQLite DB stays in the `app_data` volume
```

`make logs` tails logs. History survives `make down` / `make up` because the DB is at `/data/app.db` on a named volume.

### Without Docker

```bash
# backend (Python 3.12)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export LLM_API_KEYS=key-one,key-two LLM_MODEL=gemini/gemini-3.8-flash \
       DATABASE_URL=sqlite:///./data/app.db ALLOWED_ORIGINS=http://localhost:3000 \
       ENABLE_FAILURE_SIMULATION=true
uvicorn app.main:app --port 8000

# frontend (Node 20+), second terminal
cd frontend
cp .env.example .env        # VITE_API_BASE_URL=http://localhost:8000
npm install && npm run dev  # http://localhost:3000
```

### Environment variables

| Variable | Meaning | Default |
|---|---|---|
| `LLM_API_KEYS` | Comma-separated key pool (≥2). Ids are `key_1`, `key_2`… in order | – |
| `LLM_MODEL` | LiteLLM model string; must match your keys' provider | `gemini/gemini-3.8-flash` |
| `DATABASE_URL` | SQLite location, e.g. `sqlite:////data/app.db` | `sqlite:///./data/app.db` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000` |
| `ENABLE_FAILURE_SIMULATION` | `true` enables `X-Simulate-Failure` | `false` |
| `CACHE_ENABLED` / `CACHE_TYPE` / `CACHE_DIR` | LiteLLM cache on/off, `local` (memory) or `disk` | `true` / `local` / `./data/llm_cache` |
| `DEFAULT_SYSTEM_PROMPT`, `LOG_LEVEL`, `LLM_TIMEOUT_SECONDS` | misc | see `.env.example` |
| `VITE_API_BASE_URL` | (frontend, build time) backend URL used by the browser | empty = same origin |

### API (exactly three endpoints)

* `GET /health` → `{"status":"ok","keys_configured":2,"cache_enabled":true}` (503 if the DB is unreachable or fewer than 2 keys).
* `POST /chat` `{session_id, message, system_prompt?}` → `{session_id, reply, metadata{resolution_source, model, latency_ms, input_tokens, output_tokens, key_id, fallback_attempts}}`.
* `GET /sessions/{session_id}/messages` → history oldest first, no system prompt; assistant messages carry metadata.
* Errors are always JSON `{"detail": ...}`: 422 validation, 503 `all providers unavailable`, 404 `session not found`.

### Tests

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q     # or: make test
```

41 tests: validation, CORS, multi-turn, isolation, ordering, persistence, cache, failover, simulation.
They use a fake LiteLLM *custom provider* in place of the network call, so **no paid inference is used**, but the real
LiteLLM Router, fallback chain, cache and hooks are exercised.

## 3. Design decisions: key fallback, caching, SQLite session storage

**Key fallback.** Each key becomes its own LiteLLM Router model group (`key_1`, `key_2`, …) with one deployment whose
`model_info.id` is the key id. The Router's `fallbacks` option chains `key_1 → key_2 → …`, so LiteLLM itself moves to the
next key on 429 / quota / 5xx / timeout. `num_retries=0` (no hammering the same key) and cooldowns are disabled so a
rate-limited key is simply tried first again on the next request. Separate groups make the order deterministic and the
attribution exact. A pre-call hook records every real provider attempt, so `fallback_attempts` = attempts − 1 and `key_id`
is the key of the last attempt that succeeded; the raw key never leaves the backend. If everything fails the API returns
`503 {"detail":"all providers unavailable"}` and nothing is stored.

**Caching.** `litellm.enable_cache` plus `Router(cache_responses=True)`. `caching_groups` makes all key groups share one
cache identity, so the identity is *model namespace + full message list (system + history + new message)*, never the
session id or the key. The same first message in a new session is therefore a hit; any different message or history is a miss.
Hits are detected from LiteLLM's own `cache_hit` flag (not by latency). Stored token usage is returned as-is, `key_id=null`,
`fallback_attempts=0`. The default is the in-memory cache (cleared on restart); `CACHE_TYPE=disk` persists it.

**SQLite session storage.** Table `messages` follows the required schema (+ index on `(session_id, id)`); a small
`sessions` table stores the per-session system prompt. The backend loads history, sends `system + history + new message` to the LLM, and
only after a successful reply writes the session row, user message and assistant message in **one transaction**, so
failed requests (422/503) never appear in history. Timestamps are server-side ISO-8601 UTC.

**Tokens.** Taken from the provider's usage for that one request (never cumulative). If a provider returns no usage,
`litellm.token_counter` is used as an explicit fallback and a warning is logged.

**Failure simulation.** `X-Simulate-Failure: key_1=429,key_2=500` / `*=429` (statuses 429, 500, 502, 503), honored only if
`ENABLE_FAILURE_SIMULATION=true`. The pre-call hook raises the matching LiteLLM exception for that key *inside the real
fallback path*, for that request only. Simulated requests skip cache reads so a cached answer cannot hide the simulated outage.

## 4. Verification: how to see failover, cache hits and per-message token usage

Replace `$API` with `http://localhost:8000` (or your backend URL).

```bash
# Cache: send the same message in two NEW sessions → LIVE_INFERENCE, then LLM_CACHE (faster, key_id null)
curl -s $API/chat -H 'Content-Type: application/json' -d '{"session_id":"a1","message":"What is the capital of France?"}'
curl -s $API/chat -H 'Content-Type: application/json' -d '{"session_id":"a2","message":"What is the capital of France?"}'

# Failover: key_1 fails, key_2 answers (200, key_id "key_2", fallback_attempts 1)
curl -s $API/chat -H 'Content-Type: application/json' -H 'X-Simulate-Failure: key_1=429' \
     -d '{"session_id":"a3","message":"Tell me a fun fact"}'

# Everything fails → 503 {"detail":"all providers unavailable"}, nothing stored
curl -si $API/chat -H 'Content-Type: application/json' -H 'X-Simulate-Failure: *=429' \
     -d '{"session_id":"a4","message":"Tell me a fun fact"}'

# History and per-message usage
curl -s $API/sessions/a1/messages
```

In the UI: open **Settings** (top right) to pick a simulated failure, ask a question, then ask it again after **New chat**.
Each assistant reply shows its own source, model, latency and input/output tokens (`data-testid`s `meta-*`).

## 5. Setup Used: your editor and AI tools

`<FILL IN: your editor (e.g. VS Code), AI assistants used (e.g. Claude), terminal/Docker versions>`

## 6. Bonus features (if any): what you added beyond the requirements and why

* **Settings panel** with the optional system-prompt field (`system-prompt-input`) and a failure-simulation picker, so
  failover can be demonstrated from the UI during the demo.
* **"Answered by" line** per reply (key id and number of failed keys) to make failover visible.
* **Dark mode**, mobile layout, per-session system prompt persisted server-side, `CACHE_TYPE=disk` option.
* Backend container drops root privileges after fixing `/data` ownership (works with root-owned hosting disks).

## Known limits

* The in-memory cache and request locks are per process: run a single backend instance.
* Docker images, the live LiteLLM-to-provider path and deployment were **not** executed by the author of this scaffold
  in the build environment (no Docker daemon, no provider keys); run `make up` and the curl checks above with real keys.
