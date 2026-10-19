# Researcher workflow

**Release:** Python/API `0.1.0` (git tag `v0.1.0`); Android logger `0.1.1-android`. After `.\scripts\install-phone.ps1`, the app status line should show `Logger: 0.1.1-android`.

Personal pilot for logging Instagram Reels pace on your own Android phone, then analyzing on a PC. Use this runbook for a **new phone**, a **new PC**, or day-to-day capture.

**Capture-max / process-on-PC:** keep raw JSONL + DYI immutable (L0); derive impressions (L2) and DYI links (L3) offline. Prefer L3 plots for analysis figures.

Do **not** commit phone queues, SQLite DBs, Instagram data downloads, `data/derived/`, `.env`, or `scripts/local.device.json`.

---

## What you need (checklist)

| Item | Notes |
| --- | --- |
| Android phone you administer | USB debugging and/or Wireless debugging |
| PC with Android Studio (or SDK) + JDK **17** | Studio’s bundled JBR 25 breaks this Gradle setup |
| This repo cloned | `reel-logger` |
| Instagram on the phone | Package `com.instagram.android` |
| Optional: Instagram “Download your information” JSON | For reel **URLs** only (no dwell) |

---

## A. New PC setup (once)

```powershell
cd reel-logger
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# optional for LAN sync later: set API_TOKEN in .env
alembic upgrade head
uvicorn app.main:app --reload
```

Leave the API running while you capture/ingest. OpenAPI: http://127.0.0.1:8000/docs

Android tooling:

```powershell
copy android\keystore.properties.example android\keystore.properties
.\scripts\generate-debug-keystore.ps1
```

In Android Studio: open `android/`, set **Gradle JDK = 17** (not 25), sync once.

---

## B. New phone setup (order matters)

### 1. Connect adb

**Wireless (recommended if USB debugging never prompts):**

1. Phone + PC on same Wi‑Fi  
2. Developer options → **Wireless debugging** → ON  
3. **Pair device with pairing code** → note IP:`pairingPort` + 6-digit code  
4. On PC:

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb pair 192.168.x.x:PAIRING_PORT
# enter code
& $adb connect 192.168.x.x:CONNECT_PORT
& $adb devices
```

You want a line ending in `device`. Same phone may appear twice (IP + `adb-tls-…`); scripts pick the IP automatically.

### 2. Install the logger

```powershell
.\scripts\install-phone.ps1
```

### 3. Enable capture on the phone

1. Open **Scroll logger**  
2. Android 13+: allow **restricted settings** for the app if asked  
3. **Accessibility → Scroll logger (Instagram)** → ON  
4. In the app: **Logging on** → notification “Scroll logger on” must stay visible  
5. Optional but recommended for research: enable **Debug raw_a11y** so era-C tree samples (`nodes[]` + bounds) land in the JSONL for PC identity (off by default)

### 4. Register the device with the API

API must be running first.

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\register_device.py --base-url http://127.0.0.1:8000
```

Example output:

```json
{
  "user_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "device_id": "ffffffff-1111-2222-3333-444444444444"
}
```

Save locally (not in git):

```powershell
copy scripts\local.device.json.example scripts\local.device.json
# edit scripts\local.device.json with those UUIDs
```

Also paste `user_id` / `device_id` into the app sync fields if you will use LAN sync later.

### 5. Smoke test (2 minutes)

1. Instagram → Reels / For You, scroll a bit, maybe one like  
2. App: **Queue lines** should be &gt; 0  
3. On PC:

```powershell
.\scripts\sync-day.ps1
```

4. Check http://127.0.0.1:8000/docs → `GET /sessions` and `GET /impressions` with your `user_id`  
   Expect ≥1 session and some impressions with `dwell_ms`.

---

## C. Day-to-day capture

```powershell
# Terminal 1 — API
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Terminal 2 — after scrolling with Logging on
.\scripts\sync-day.ps1
```

`sync-day.ps1` will:

1. Pick one adb device (handles dual wireless entries)  
2. Pull `events-YYYYMMDD-HHMMSS.jsonl` into `data/phone-queue/`  
3. Ingest using `scripts/local.device.json`  
4. Print session/impression counts  

Pull only (no ingest):

```powershell
.\scripts\pull-queue.ps1
```

Ingest a specific file:

```powershell
python scripts\ingest_queue.py "data\phone-queue\events-20261014-155449.jsonl" `
  --user-id YOUR-USER-UUID `
  --device-id YOUR-DEVICE-UUID
```

---

## D. Optional: Instagram URLs (DYI)

Watch history lives under the export’s  
`ads_information/ads_and_topics/videos_watched.json`  
(not only `your_instagram_activity/`). It has URLs + timestamps, **not** dwell.

**Important:** the export only covers watches up to when Meta generated it. If logging started *after* that cutoff, time-merge will find **zero** overlap — request a new download that covers the logging days.

### Offline pipeline (L2 preprocess → L3 merge)

Raw JSONL and DYI zips are **never overwritten**. Stages print clear banners.

```powershell
# L2 — derived impressions (auditable flags; raw untouched)
python scripts\preprocess_queue.py data\phone-queue\events-….jsonl --min-dwell-ms 500
# writes data\derived\<run_id>\impressions.csv + preprocess_manifest.json

# L3 — link derived + DYI by time (no dwell from DYI)
python scripts\merge_sources.py data\derived\<run_id>\impressions.csv `
  --export-root "C:\path\to\unzipped-instagram-export"
# writes data\derived\<run_id>\merged.csv
```

`compare_logger_dyi.py` remains a thin alias that runs preprocess+merge for one-shot use.

Via API (after ingest):

```powershell
python scripts\import_dyi.py --export-root "C:\path\to\unzipped-instagram-export"
# POST /impressions/reconcile?user_id=YOUR-USER-UUID
```

Never invent dwell from gaps between DYI timestamps. Layers: [architecture.md](architecture.md).

---

## E. Analysis

- Quick: OpenAPI `/sessions/days`, `/impressions`  
- Prefer plotting **L3 merged** (or L2 derived), not raw JSONL, for analysis figures.  
- Timeline x-axes use **absolute clock time** in an IANA zone (`--tz`, default `Europe/Copenhagen`; use `--tz UTC` for UTC hours).  
- L3 merged timeline:

```powershell
pip install -e ".[viz]"
python scripts\visualize_merged.py data\derived\<run_id>\merged.csv --tz Europe/Copenhagen
python scripts\visualize_merged.py data\derived\<run_id>\merged.csv `
  --hide-dyi-only --no-show -o data\derived\<run_id>\merged_timeline.png
# --matched-only = only match_status=matched; --hide-dyi-only drops unmatched DYI rows
```

- Raw phone JSONL timeline (debug / capture QA only):

```powershell
python scripts\visualize_queue.py data\phone-queue\events-YYYYMMDD-HHMMSS.jsonl --clean --tz Europe/Copenhagen
```

- Notebook: `notebooks/pace_report.ipynb` (set `BASE` / `USER_ID` as needed)

Layers and CSV columns: [architecture.md](architecture.md).

---

## F. App updates after code changes

```powershell
.\scripts\install-phone.ps1
```

Re-check Accessibility after some updates. Same `applicationId` + local debug keystore keep the on-phone queue.

PC-only changes (API, import, notebook): restart/reload uvicorn — no phone reinstall.

---

## Troubleshooting (short)

| Symptom | Fix |
| --- | --- |
| `more than one device/emulator` | Scripts auto-pick IP; or `.\scripts\pull-queue.ps1 -Serial 192.168.x.x:PORT` |
| Gradle error `25.0.3` | Use JDK 17 for Gradle (not Studio JBR 25) |
| Queue lines stay 0 | Accessibility off, Logging off, or not in Instagram Reels |
| Empty pull file | Scroll with logging on; confirm queue count in app |
| API 404 on ingest | Wrong `user_id`/`device_id`; re-run `register_device.py` |
| USB never asks for debugging | Use Wireless debugging (section B.1) |
| Merge finds 0 matches | DYI export cutoff before logging days — request a new download covering those dates |
| Creator looks like `Repost` / `SeekBar` | Era-A/B hint noise; re-preprocess with era-C JSONL (Debug raw_a11y on) |

More detail: [deploy.md](deploy.md), [android-detector.md](android-detector.md), [feasibility.md](feasibility.md).
