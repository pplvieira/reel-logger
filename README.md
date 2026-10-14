# Personal scroll logger

A personal pilot for logging short-form scrolling habits on your own phone. The phone records when a reel appeared, when it left, and which controls you used. A FastAPI service on your PC turns that into sessions and days, and later can match optional reel URLs from Instagram’s data download.

This build is for **your own device**. It is not a participant instrument and is not published to an app store.

## What is measured

| Source | What you get | What you do not get |
| --- | --- | --- |
| Live phone logger (Android, next milestone) | Session start/end, per-reel dwell, like / comment / share / send when the UI exposes them | Reliable reel URL on For You |
| Instagram Watch History / Download your information | Creator + watch time; sometimes a URL | Dwell time; guaranteed URL for every watch |
| Screen Time (iOS, later) | Coarse “Instagram was open” sessions | Per-reel index, dwell, or URL |

The wire format is **semantic**: clients post `session_start`, `session_end`, `reel_shown`, `reel_hidden`, and `interaction`. Android view ids and accessibility dumps stay on the phone. That keeps a later iOS client from forcing a schema rewrite. See [docs/event-schema.md](docs/event-schema.md) and [docs/ios.md](docs/ios.md).

## Repo layout

```
reel-logger/
  app/                 FastAPI service (code-first models)
  docs/                Feasibility, architecture, schema, deploy, privacy, iOS
  scripts/             Phone install helpers (Android)
  tests/               Sessionize, day bucketing, DYI fixtures
  alembic/             Migrations generated from SQLAlchemy models
```

Heavy analysis (plots, long-run pace summaries) stays in notebooks on the PC. The API serves rows and a few session/day aggregates.

## Quick start (PC service)

```powershell
cd reel-logger
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

- Health: `GET http://127.0.0.1:8000/health`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Default database: SQLite at `./data/reel_logger.db`
- Set `DATABASE_URL` later for Postgres / Supabase

## Phone updates (Android, later)

Documented in [docs/deploy.md](docs/deploy.md). Priority is a one-command wireless reinstall via `scripts/install-phone.ps1` so each debug build replaces the app and keeps the on-phone queue. The Android listener is the next milestone after this skeleton.

## Documentation

- [docs/feasibility.md](docs/feasibility.md) — live log vs Watch History vs data download
- [docs/architecture.md](docs/architecture.md) — clients, ingest, sessionizer, importers
- [docs/event-schema.md](docs/event-schema.md) — tables, event types, `capture_method`
- [docs/deploy.md](docs/deploy.md) — Android wireless install (Android-only)
- [docs/ios.md](docs/ios.md) — later iOS path without rewriting the server
- [docs/privacy.md](docs/privacy.md) — on-device consent, localhost API, no screenshots

## Status

| Piece | Status |
| --- | --- |
| FastAPI models, ingest, sessionize stubs | This repo |
| Instagram DYI importer contract | Stub + fixtures |
| Android accessibility logger | Next milestone |
| TikTok / YouTube Shorts adapters | Empty stubs |
| iOS Screen Time client | Documented only |
| Supabase / multi-user | Seam via `DATABASE_URL` and `user_id` |
