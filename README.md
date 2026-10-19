# Personal scroll logger

**Version:** [0.1.0](VERSION) · see [CHANGELOG.md](CHANGELOG.md) · tag `v0.1.0` · Android logger `0.1.1-android`

A personal pilot for logging short-form scrolling habits on your own phone. The phone records when a reel appeared, when it left, and which controls you used. A FastAPI service on your PC turns that into sessions and days, and matches optional reel URLs from Instagram’s data download.

This build is for **your own device**. It is not a participant instrument and is not published to an app store.

| Component | Version field |
| --- | --- |
| Repo / release tag | `VERSION` → `0.1.0`, git tag `v0.1.0` |
| Python API | `app.__version__` / `pyproject.toml` → `0.1.0` |
| Android app | `versionName` `0.1.1`, `LOGGER_VERSION` `0.1.1-android` |

Offline research pipeline (raw files never overwritten):

```powershell
python scripts\preprocess_queue.py data\phone-queue\events-….jsonl
python scripts\merge_sources.py data\derived\<run_id>\impressions.csv --export-root "C:\path\to\instagram-export"
```

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

Visualize (default `--tz Europe/Copenhagen`, or `--tz UTC`):

```powershell
pip install -e ".[viz]"
# L3 timeline (absolute clock)
python scripts\visualize_merged.py data\derived\<run_id>\merged.csv --hide-dyi-only --tz Europe/Copenhagen
# L3 dwell histogram (stacked by match_status)
python scripts\plot_dwell_hist.py data\derived\<run_id>\merged.csv --kde
# L3 average-day 24h profile
python scripts\plot_circadian.py data\derived\<run_id>\merged.csv --metric count --smooth kde
# Raw phone JSONL (debug / capture QA)
python scripts\visualize_queue.py data\phone-queue\events-….jsonl --clean --tz Europe/Copenhagen
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
  android/                  Kotlin accessibility logger (0.1.1-android)
  app/                      FastAPI service
    services/derived/       Offline L2 preprocess + L3 merge
  docs/                     researcher-workflow + design docs
  scripts/                  install / pull / sync-day / ingest / DYI /
                            preprocess_queue / merge_sources / visualize_*
  notebooks/
  tests/
  data/phone-queue/         Pulled L0 JSONL (gitignored)
  data/derived/             L2/L3 CSVs (gitignored)
```

## Status (0.1.0 + Android 0.1.1)

| Piece | Status |
| --- | --- |
| FastAPI ingest / sessionize / reporting | Done |
| Android accessibility logger + JSONL queue | Done (`0.1.1-android`: optional era-C `raw_a11y`) |
| LAN sync + API token + event_id dedupe | Done |
| Offline L2 preprocess → L3 DYI merge | Done (`preprocess_queue` / `merge_sources`) |
| DYI import + API reconcile by time | Done |
| Pace notebook | Done |
| Day sync script + researcher runbook | Done |
| Timeline viz (clock x-axis, `--tz`) | Done (merged + queue) |
| TikTok / YouTube Shorts / iOS | Seams / docs only |
