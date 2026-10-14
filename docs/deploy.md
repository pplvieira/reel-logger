# Deploy — Android phone updates

**Android-only.** Package id: `dk.sdu.scrolllogger`. iOS: see [ios.md](ios.md).

Goal: one-command reinstall so development stays fast.

## Prerequisites

- Android Studio (or SDK + JDK 17)
- Phone with Developer options + Wireless debugging
- Generate debug keystore once: `.\scripts\generate-debug-keystore.ps1`
- Open `android/` in Android Studio once if `gradlew.bat` is missing (File → Open → let it sync / create wrapper)

## One-time phone setup

1. Enable Developer options and Wireless debugging.
2. Pair once (USB or pairing code), then `adb connect <phone-ip>:<port>`.
3. Confirm `adb devices` shows the phone.
4. Install: `.\scripts\install-phone.ps1`
5. On Android 13+, allow **restricted settings** for Scroll logger, then enable **Accessibility → Scroll logger (Instagram)**.
6. Open the app → turn **Logging on** (notification must stay visible).
7. Register device against the PC API:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
# other terminal:
python scripts\register_device.py
```

Enter printed `user_id` / `device_id` in the app sync config.

## Daily update path

```powershell
.\scripts\install-phone.ps1
```

Stable `applicationId` + a **local** `android/debug.keystore` (gitignored; generate with `scripts/generate-debug-keystore.ps1`) keep the on-phone queue across reinstalls on the same PC.

## Pull queue (offline path)

```powershell
.\scripts\pull-queue.ps1
python scripts\ingest_queue.py data\phone-queue\events-XXXX.jsonl --user-id <id> --device-id <id>
```

## LAN sync

1. Set `API_TOKEN` in `.env` (recommended on LAN).
2. Run API bound to the LAN: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. In the app: base URL `http://<pc-lan-ip>:8000`, user/device ids, token → **Save** → **Sync now**.

## Import Instagram DYI catalog

```powershell
python scripts\import_dyi.py --export-root "C:\path\to\your-unzipped-instagram-export"
```

Do not commit the export into git.

## Checklist after install

- [ ] App replaces previous build (`dk.sdu.scrolllogger`)
- [ ] Accessibility still enabled
- [ ] Logging notification visible when capture is on
- [ ] Queue line count increases after scrolling Reels
- [ ] Pull or sync reaches `POST /ingest/events`
