# Later: iOS

No iOS code in the current slice. This document is the extension path so the Android client never becomes the schema.

## Hard limit

A third-party iOS app cannot read Instagram’s screen in the background. There is no equivalent of an Android `AccessibilityService` that another app can point at Reels. Per-reel dwell therefore stays an Android capture method (`capture_method=accessibility`).

## Path

### 1. Catalog only

Create a device with `platform_os=ios`. Import the same Instagram data download, or paste a reel URL (`capture_method=manual` or `share_sheet`). No server change beyond what the current schema already stores. Download-your-information is an account export, not an OS export.

### 2. Coarse sessions

A small Swift app, using Screen Time / Device Activity, posts `session_start` and `session_end` with `capture_method=screen_time` and **zero** reel events. Day and session grouping then include iPhone foreground time.

Requires Apple’s Family Controls entitlement. Does not yield reel index, dwell, or URL. Sessions with zero impressions are already valid in the schema.

### 3. Same reel events from a player we own

If a future in-house feed player emits `reel_shown` and `reel_hidden`, `sessionize` already accepts them. That is a different product from watching the live Instagram app.

### 4. Out of scope

- Jailbreak hooks
- Reading Instagram’s private API
- Treating Screen Time rows as if they were per-reel impressions

## What already protects this path

- Semantic wire format only (see [event-schema.md](event-schema.md))
- `devices.platform_os` and `capture_method` on sessions / raw events
- `sessionize` ignores debug types and does not require Android fields
- Platform adapters map social-app meaning, not OS package names
