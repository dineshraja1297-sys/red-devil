# Red Devil

![Red Devil logo](assets/red-devil-logo.svg)

Red Devil is a multi-agent trading platform (FastAPI + PostgreSQL + Redis, React dashboard and
LangGraph agents in later stages).

> **Current stage: 1 of 10 (foundation).** Paper mode only. Live trading is
> hard-locked in configuration: the app refuses to start if
> `LIVE_TRADING_ENABLED=true` or `TRADING_MODE=live`. No broker connections exist.

## What Stage 1 contains

| Area | Status |
|---|---|
| Project structure | Done |
| FastAPI app, CORS, request IDs, request logging | Done, tested |
| Config from `.env` with validation (risk defaults, live-trading lock) | Done, tested |
| Logging to console + rotating `logs/app.log` | Done |
| JSON error responses (no internal details leaked) | Done, tested |
| Auth foundation: register, JWT login, `/me`, bcrypt hashing | Done, tested |
| Database models for all 14 spec entities | Done, tested |
| `/health` (liveness) and `/health/ready` (PostgreSQL + Redis) | Done, tested |
| Agents, risk engine, approvals, paper broker, dashboard | **Not started** (folders reserved) |

## Prerequisites (Windows 11)

- Python 3.11, 3.12 or 3.13 from python.org (tick "Add python.exe to PATH")
- Docker Desktop (runs PostgreSQL and Redis)
- VS Code with the Python extension

## Setup (PowerShell, from the project folder)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# paste the output into .env as SECRET_KEY=...

docker compose up -d
docker compose ps          # wait until both show "healthy"

python -m database.init_db
```

If `Activate.ps1` is blocked, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Run

```powershell
uvicorn backend.app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health
- Readiness: http://127.0.0.1:8000/health/ready

## Test

```powershell
python -m pytest
```

Tests use a temporary SQLite database, so they run even without Docker.

## Health endpoint meanings

| `/health/ready` status | HTTP | Meaning |
|---|---|---|
| `ok` | 200 | PostgreSQL and Redis reachable |
| `degraded` | 200 | PostgreSQL OK, Redis down |
| `unavailable` | 503 | PostgreSQL down |

## Safety rules built into the foundation

- Live trading cannot be enabled by configuration in this stage.
- Trading tables carry an `is_simulated` flag that defaults to `true`.
- Orders require a unique `idempotency_key` (database-enforced duplicate prevention).
- Approval requests store only hashes of the approval token and the exact order payload.
- Audit log table is append-only by convention; auth events are already logged.
- Money and prices use `Numeric`, never floats.
- `.env` is git-ignored; the app refuses the placeholder `SECRET_KEY`.
