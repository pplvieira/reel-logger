# Deploy — Android phone updates

**Android-only.** iOS install is not covered here; see [ios.md](ios.md).

Goal: make iterating on the phone logger a one-command reinstall so development stays fast.

## Principles

- Stable `applicationId` and the same debug keystore across builds so each install **replaces** the app and keeps the on-phone event queue.
- Wireless debugging after a one-time USB pair: `adb connect <phone-ip>:<port>`.
- Service / schema changes on the PC do **not** require a phone rebuild. Only the Kotlin listener does.

## One-time setup (when the Android module exists)

1. Enable Developer options and Wireless debugging on the phone.
2. Pair once over USB or with the pairing code from Wireless debugging.
3. Confirm `adb devices` shows the phone.
4. On Android 13+, allow restricted settings for the sideloaded logger so Accessibility can be enabled.
5. Enable the Accessibility service for the logger and keep the “logging on” notification visible while capturing.

## Daily update path

From the repo root (after the Android module is added):

```powershell
.\scripts\install-phone.ps1
```

That script runs `gradlew installDebug` against the connected device (wireless or USB). Prefer this over Android Studio Run for repeatability.

Optional:

```powershell
.\scripts\install-phone.ps1 -Serial <adb-serial>
```

## PC service reload

```powershell
uvicorn app.main:app --reload
```

Parsing, matching, and reports change without touching the phone.

## Checklist after install

- [ ] App replaces previous build (same package)
- [ ] Accessibility still enabled (Android may ask again after some updates)
- [ ] Logging notification appears when capture is on
- [ ] Test batch reaches `POST /ingest/events` (when wireless sync is wired)
