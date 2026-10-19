# Event schema

Timestamps are UTC. Each user has an IANA timezone (default `Europe/Copenhagen`). Session and calendar-day grouping use that zone. A day is a query, not a table: one day holds many sessions.

## Enums

| Field | Values |
| --- | --- |
| `platform` | `instagram` (live); `tiktok`, `youtube_shorts` accepted by types, rejected by parsers until implemented |
| `platform_os` | `android`, `ios`, `other` |
| `capture_method` | `accessibility`, `screen_time`, `manual`, `dyi`, `share_sheet` |
| `surface` | `for_you` first; others later |
| `match_status` | `unmatched`, `unique`, `ambiguous` |
| Interaction kinds | `like`, `unlike`, `comment_open`, `comment_send`, `share_open`, `send`, `save`, `profile_open` |

## Ban on OS-specific required fields

Required columns and the Instagram platform adapter **must not** contain package names, view ids, resource ids, accessibility class names, or motion events. `com.instagram.android` lives only in the Android client. OS identity is `devices.platform_os` + `capture_method`.

## Tables

### `users`

| Column | Notes |
| --- | --- |
| `id` | UUID |
| `display_name` | Local label |
| `timezone` | IANA, default `Europe/Copenhagen` |

One local user is seeded on first migration / startup.

### `devices`

| Column | Notes |
| --- | --- |
| `id` | UUID |
| `user_id` | FK |
| `platform_os` | `android` / `ios` / … |
| `label` | e.g. “Pixel personal” |
| `logger_version` | Client build string |

### `sessions`

One continuous visit to a feed surface. Ends on leave, screen off, or a gap (default 60s).

| Column | Notes |
| --- | --- |
| `id` | UUID |
| `user_id`, `device_id`, `platform` | |
| `started_at`, `ended_at` | UTC |
| `surface` | e.g. `for_you` |
| `end_reason` | `leave`, `screen_off`, `gap`, `explicit` |
| `capture_method` | |
| `logger_version` | |

Sessions may contain **zero** impressions (e.g. Screen Time).

### `raw_events`

Append-only. Re-running sessionize rebuilds derived rows from semantic types alone.

| Column | Notes |
| --- | --- |
| `id` | UUID |
| `user_id`, `device_id`, `platform` | |
| `schema_version` | Wire version |
| `observed_at` | UTC |
| `type` | Event type string |
| `payload` | JSON |
| `capture_method` | |

### `impressions`

One reel showing inside a session.

| Column | Notes |
| --- | --- |
| `id` | UUID |
| `session_id` | FK |
| `user_id`, `platform` | |
| `position_in_session` | 1-based |
| `shown_at`, `hidden_at` | UTC |
| `dwell_ms` | `hidden_at - shown_at` when both set |
| `creator_handle` | Nullable |
| `caption_excerpt` | Nullable, short |
| `confidence` | Client float 0–1 |
| `external_url` | Null until matched |
| `match_status` | Default `unmatched` |

### `interactions`

| Column | Notes |
| --- | --- |
| `id` | UUID |
| `impression_id` | Nullable if timing ambiguous |
| `session_id` | FK |
| `user_id`, `platform` | |
| `kind` | See enum |
| `observed_at` | UTC |

### `content_records`

From DYI, pasted URL, or Watch History dump.

| Column | Notes |
| --- | --- |
| `id` | UUID |
| `user_id`, `platform` | |
| `source` | `dyi`, `manual`, `watch_history`, … |
| `creator_handle` | Nullable |
| `external_url` | Nullable — only when present in source |
| `watched_at` | Nullable |
| `time_precision` | e.g. `second`, `day`, `unknown` |
| `raw_json` | Original object |

### `impression_matches`

| Column | Notes |
| --- | --- |
| `impression_id`, `content_record_id` | |
| `status` | `unique` or `ambiguous` |

## Phone / client batch

```json
{
  "schema_version": "1",
  "device_id": "...",
  "user_id": "...",
  "platform": "instagram",
  "capture_method": "accessibility",
  "events": [
    {
      "type": "session_start",
      "observed_at": "2026-10-14T09:00:00Z",
      "payload": { "surface": "for_you" }
    },
    {
      "type": "reel_shown",
      "observed_at": "2026-10-14T09:00:01Z",
      "payload": {
        "creator_handle": "example",
        "caption_excerpt": "…",
        "confidence": 0.8
      }
    },
    {
      "type": "interaction",
      "observed_at": "2026-10-14T09:00:05Z",
      "payload": { "kind": "like" }
    },
    {
      "type": "reel_hidden",
      "observed_at": "2026-10-14T09:00:12Z",
      "payload": {}
    },
    {
      "type": "session_end",
      "observed_at": "2026-10-14T09:05:00Z",
      "payload": { "end_reason": "leave" }
    }
  ]
}
```

### Debug type `raw_a11y`

Optional Android evidence dump (enable **Debug raw_a11y** in the app). Stored in JSONL / `raw_events` and **ignored by `sessionize`**. Offline L2 (`preprocess_queue.py`) uses it for identity when present.

| Era | Typical payload |
| --- | --- |
| B | `texts_sample`: list of visible strings |
| C (`0.1.1-android`+) | `texts_sample` **and** `nodes[]` with `text` / `content_desc` / `bounds` / optional `screen` |

On-device `reel_shown` creator/caption fields remain convenience hints (`identity_source` / `payload.hints`); prefer PC extractors when raw samples exist.

Offline derived CSV columns (L2/L3): [architecture.md](architecture.md).
