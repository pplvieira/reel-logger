# Feasibility

## Goal

Characterize average scrolling pace over days: sessions per day, dwell per reel, skip rate, and explicit interactions (like, comment, share, send). Optional later: attach a reel URL when Instagram’s own export provides one.

## What works on a personal Android phone

A sideloaded app with an `AccessibilityService` limited to Instagram can:

- Notice when Instagram is in the foreground and when a Reels / For You surface is active
- Emit `session_start` / `session_end` and `reel_shown` / `reel_hidden` as the feed advances
- Record taps on like, comment, share, and send when those controls announce a click or state change
- Queue semantic JSON locally and sync to the PC later

Dwell is the interval between `reel_shown` and `reel_hidden`, minus time the app is not focused. Double-tap-to-like is less reliable than the heart button. Instagram UI changes can break detectors; every impression carries a client `confidence` flag.

## What does not work for live For You URLs

- Instagram does not show `instagram.com/reel/...` on the For You screen. The accessibility tree usually exposes buttons, a creator name, and sometimes a caption — not the reel shortcode.
- There is no official API for For You impressions plus watch time.
- Breaking Instagram’s certificate pinning (VPN interception, Frida, LSPosed) to read private API calls is **out of scope**. It is not lightweight, it breaks on each Instagram update, and it is traffic interception rather than a personal habit log.
- Auto-tapping Share → Copy link would change the behavior under study. A link you copy yourself can be an optional later stamp (`capture_method=manual` or `share_sheet`). Silent clipboard reads from the background are blocked on modern Android.

## Watch History and Download your information

**In-app Watch History** (Profile → menu → Your activity → Watch history):

- Roughly 30 days of videos Instagram chose to record
- Creator + watch time; tapping a row opens the reel
- No dwell; short skips may be missing; URL is not printed on the list

**Download your information** (JSON):

- Typical path: `ads_information/ads_and_topics/videos_watched.json` (older archives: `impressions_history_videos_watched`)
- A 2026 personal export had **URL on every videos_watched row** (many `/reel/…`), plus `timestamp`, `fbid`, and often `Caption`, but **no Author**
- Fields still vary by export; the importer keeps the raw object and fills `external_url` only when a link is present
- Likes/saves under `your_instagram_activity/` are sparse; they are not a substitute for `videos_watched`
- Inter-row timestamp gaps are often 0–1s — **never** treat them as dwell

**Matching rule** (later, in `reconcile`): same user, same platform, same creator, watch time near impression start. Two reels from one creator close together stay `ambiguous` — never a guessed URL.

Driving Watch History (open each reel, Share, Copy link) is a possible spot-check. It is not how daily logging works.

## Honest claim of the live log

- Session start and end while Instagram is in front
- Local reel index within a session (not a URL)
- Dwell from one detected reel change to the next
- Creator handle and short caption only when those strings are on screen
- Interactions when the control is observable
- Confidence on every impression row

## iOS

A third-party iOS app cannot read Instagram’s screen in the background. Per-reel dwell stays an Android `capture_method=accessibility` path. iOS can still use the same PC API for catalog import and coarse Screen Time sessions. See [ios.md](ios.md).
