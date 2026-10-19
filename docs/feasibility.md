# Feasibility

## Goal

Characterize average scrolling pace over days: sessions per day, dwell per reel, skip rate, and explicit interactions (like, comment, share, send). Optional: attach a reel URL when Instagram’s own export provides one.

## Sources of truth (what each may claim)

| Source | Strong on | Weak / absent | Notes |
| --- | --- | --- | --- |
| Accessibility timing (`reel_shown`/`hidden`) | When the UI changed | True reel id / URL | L0→L2 dwell |
| Accessibility tree (`raw_a11y`) | Labels on screen at that instant | Meaning until PC interprets | Prefer `Reel by X` / `Profile picture of X` over bare tokens |
| On-device handle guess | Convenience hint only | Often UI chrome (`Repost`, `SeekBar`) | Discount when raw present |
| DYI `videos_watched` | URL + timestamp (+ caption/fbid) | No dwell; gaps ≠ watch time | L0→L3 catalog |
| In-app Watch History (~30d) | Find watched reels | No dwell; not automated | Optional spot-check |
| Graph API | Owned business media | No personal For You watch/dwell | Dead end for this pilot |
| UsageStats | App foreground time | Not per-reel | Deferred |
| MediaProjection / OCR | Visual ground truth | High burden / consent | Deferred |
| TLS / Frida intercept | — | Brittle, ToS-hostile | **Out of scope** |

**Honest claim:** cleaned accessibility dwell (PC preprocess) + DYI URL attachment by time (merge). No phone path exposes Meta’s internal watch-time metric.

Pipeline layers and CLI stages: [architecture.md](architecture.md).

## What works on a personal Android phone

A sideloaded app with an `AccessibilityService` limited to Instagram can:

- Notice when Instagram is in the foreground and when a Reels / For You surface is active
- Emit `session_start` / `session_end` and `reel_shown` / `reel_hidden` as the feed advances
- Optionally dump tree samples (`raw_a11y`) with texts and (from `0.1.1-android`) node bounds
- Record taps on like, comment, share, and send when those controls announce a click
- Queue JSON locally and pull to the PC

**Capture-max / process-on-PC:** the phone keeps evidence; Instagram-specific identity cleaning runs in `preprocess_queue.py` / `merge_sources.py`.

## What does not work for live For You URLs

- Instagram does not show `instagram.com/reel/...` on the For You accessibility tree.
- There is no official API for For You impressions plus watch time.
- Certificate pinning bypass (VPN, Frida, LSPosed) is **out of scope**.
- Auto Share → Copy link changes the behavior under study.
- Silent clipboard reads from the background are blocked on modern Android.

## Watch History and Download your information

**In-app Watch History** (Profile → menu → Your activity → Watch history):

- Roughly 30 days; sort/filter by date or account
- No dwell; URL not listed as text (open row to view)

**Download your information** (JSON):

- Path: `ads_information/ads_and_topics/videos_watched.json`
- URL + `timestamp` + often `Caption` / `fbid`; Author may be absent
- **Never** treat inter-row timestamp gaps as dwell

**Matching:** time window around impression shown/hidden (+ optional caption/creator agreement). Ambiguous clusters stay `ambiguous` — never a guessed URL. Offline L3 statuses: `matched` / `ambiguous` / `logger_only` / `dyi_only` via `scripts/merge_sources.py`. API reconcile: `POST /impressions/reconcile` (`unique` / `ambiguous` / `unmatched`).

## iOS

A third-party iOS app cannot read Instagram’s screen in the background. Per-reel dwell stays Android `capture_method=accessibility`. iOS can still use the PC API for DYI import and coarse Screen Time. See [ios.md](ios.md).
