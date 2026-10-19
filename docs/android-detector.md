# Android detector notes

Personal pilot. Instagram UI changes will break on-device heuristics; **PC preprocess** is the durable identity layer. See [architecture.md](architecture.md) L0–L3.

## Capture-max policy

- Phone keeps evidence: timing events + optional `raw_a11y` tree samples.
- On-device `creator_handle` / `caption_excerpt` are **hints** (`identity_source=on_device_heuristic_v1`), not ground truth.
- When `raw_a11y` is present, PC phrase/spatial rules win over hints.

## Logger versions / JSONL eras

| Logger | Era | `raw_a11y` payload |
| --- | --- | --- |
| ≤ `0.1.0-android` | A or B | none, or `texts_sample` only |
| `0.1.1-android`+ | C when debug on | `texts_sample` **and** `nodes[]` with `bounds`, optional `screen` |

Enable **Debug raw_a11y** in the app to record tree samples (off by default). Without it, pulls stay era A (timing + on-device hints only) even on `0.1.1-android`.

## Confidence rubric (on-device hint only)

| Score | Meaning |
| --- | --- |
| **0.9** | Surface + creator hint + non-chrome caption hint |
| **0.7** | Surface + creator or caption hint |
| **0.3** | Weak |

## Surface / session

- Reels / For you / Para ti text, or like+comment+share cluster.
- Share/send overlays do **not** end the session (capture continuity).
- Stories / “posted a photo” home cards are weak non-reel signals on-device; PC may still see them in raw dumps.

## PC identity (preferred)

From `texts_sample` / `nodes`:

1. `Reel by {handle}.…`
2. `Profile picture of {handle}`
3. `{user} posted a video|reel`
4. Else weak on-device hint (era A)

Ignore bare tokens: `Repost`, `SeekBar`, `Home`, `Play`, `More`, `Save`, `Share`, …

## Interactions

Labeled control clicks; same-kind debounce 600ms on device.
