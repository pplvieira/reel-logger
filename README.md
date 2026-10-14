# Personal scroll logger

A personal pilot for logging short-form scrolling habits on your own phone. The phone records when a reel appeared, when it left, and which controls you used. A FastAPI service on your PC turns that into sessions and days, and matches optional reel URLs from Instagram’s data download.

This build is for **your own device**. It is not a participant instrument and is not published to an app store.

## What is measured

| Source | What you get | What you do not get |
| --- | --- | --- |
| Live phone logger (Android) | Session start/end, per-reel dwell, like / comment / share / send when the UI exposes them | Reliable reel URL on For You live |
| Instagram Download your information (`videos_watched.json`) | URL + watch timestamp (+ caption/fbid in current exports) | Dwell time; Author may be absent |
| Screen Time (iOS, later) | Coarse “Instagram was open” sessions | Per-reel index, dwell, or URL |

The wire format is **semantic**: clients post `session_start`, `session_end`, `reel_shown`, `reel_hidden`, and `interaction`. See [docs/event-schema.md](docs/event-schema.md).

## Quick start (PC)

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

## Researcher runbook

**Start here for a new phone or daily loop:** [docs/researcher-workflow.md](docs/researcher-workflow.md)

## Android logger

```powershell
copy android\keystore.properties.example android\keystore.properties
.\scripts\generate-debug-keystore.ps1
# Open android/ in Android Studio once if gradlew is missing; set Gradle JDK = 17
.\scripts\install-phone.ps1
python scripts\register_device.py
copy scripts\local.device.json.example scripts\local.device.json
# edit local.device.json with the printed user_id / device_id
```

Enable Accessibility for **Scroll logger (Instagram)**, turn logging on, scroll Reels, then:

```powershell
.\scripts\sync-day.ps1
```

Or configure LAN sync in the app (set `API_TOKEN` + `--host 0.0.0.0` on the PC).

Details: [docs/deploy.md](docs/deploy.md), [docs/android-detector.md](docs/android-detector.md).

## Instagram DYI catalog

```powershell
python scripts\import_dyi.py --export-root "C:\path\to\your-unzipped-instagram-export"
```

Watch history is under `ads_information/ads_and_topics/videos_watched.json` (not only `your_instagram_activity/`). Then:

`POST /impressions/reconcile?user_id=…` — matches by time window; never invents dwell from export gaps.

## Pace notebook

See [notebooks/pace_report.ipynb](notebooks/pace_report.ipynb).

## Repo layout

```
reel-logger/
  android/             Kotlin accessibility logger
  app/                 FastAPI service
  docs/                researcher-workflow + design docs
  scripts/             install / pull / sync-day / ingest / DYI import
  notebooks/
  tests/
```

## Status

| Piece | Status |
| --- | --- |
| FastAPI ingest / sessionize / reporting | Done |
| Android accessibility logger + JSONL queue | Done (build on machine with Android SDK) |
| LAN sync + API token + event_id dedupe | Done |
| DYI import for real `videos_watched` shape | Done |
| Reconcile by time (+ URL/caption) | Done |
| Pace notebook | Done |
| Day sync script + researcher runbook | Done |
| TikTok / YouTube Shorts / iOS | Seams / docs only |
