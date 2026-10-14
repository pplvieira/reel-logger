# Android detector notes

Personal pilot. Instagram UI changes will break heuristics; recalibrate with fixtures.

## Confidence rubric

| Score | Meaning |
| --- | --- |
| **0.9** | On a Reels-like surface and both `creator_handle` and a **non-chrome** `caption_excerpt` were found |
| **0.7** | On a Reels-like surface and either creator or real caption was found |
| **0.3** | Surface or scroll boundary only — weak identity; treat as low-trust for URL matching |

## Surface detection

Treat as Reels / For You when:

- Visible text includes `Reels`, `For you`, or `Para ti`, or
- Like + comment + share/send controls are all present

**Excluded:** Stories (`'s story`), home-feed cards (`posted a photo`), and share/send overlays (session stays open).

## Reel change

A new `reel_shown` is emitted when **meaningful** identity changes (creator change, or non-chrome caption change), with debounce (`minReelIntervalMs`, default 400ms). Chrome-only caption churn (e.g. `Send post. Button…`) does not open a new reel.

Optional payload flags when text matches: `is_sponsored`, `is_suggested`.

## Interactions

Prefer labeled control clicks (`Like button`, `Comment`, `Share`, `Send`, `Save`) over double-tap. Duplicate same-kind clicks within 600ms are dropped on-device.

Kinds: `like`, `unlike`, `comment_open`, `comment_send`, `share_open`, `send`, `save`, `profile_open`.

## Fix on-device vs post-process

| Issue | Prefer |
| --- | --- |
| Send-button text as caption | **On-device** denylist (also `--clean` in `visualize_queue.py` for old JSONL) |
| `15.6K` / digit “handles” | **On-device** handle filter (+ post-process) |
| Share sheet ends session | **On-device** overlay detection (cannot fully repair old JSONL) |
| Duplicate `share_open` | **On-device** debounce (+ post-process) |
| Sub-second flicker impressions | Mostly **on-device** (ignore chrome churn); post-process can drop dwell &lt; 500ms |
| Stories / feed as Reels | **On-device** surface filters |
| UTF-8 mojibake in pull | **Pull script** encoding (post-hoc hard) |
| Attach interaction → impression | **Ingest / post-process** (last open reel) |
| Reel URL / media id | **Not in a11y** — DYI reconcile only |

Old pulls remain valuable as calibration dumps; re-install the app after detector changes for cleaner future days. For already-captured files:

```powershell
python scripts\visualize_queue.py data\phone-queue\events-….jsonl --clean
```

## What we could extract but do not yet

Technically available from the accessibility tree (with more fixtures / work):

- Like / comment / share **counts** (often in contentDescription)
- Audio / original-audio label
- Explicit “Sponsored” / “Suggested” (partially: `is_sponsored` / `is_suggested` flags)
- Profile-open vs creator chip
- Whether comments sheet / likers sheet is open (overlay kinds)
- Approximate vertical position / scroll deltas (noisy)
- `raw_a11y` debug summaries (opt-in; not for analysis)

Not available via accessibility on For You:

- Canonical reel URL / media id / fbid (use DYI)
- True watch completion %
- Exact algorithm rank

## Debug

`raw_a11y` is off by default. Enable only while calibrating; it is ignored by `sessionize`.
