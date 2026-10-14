# Android detector notes

Personal pilot. Instagram UI changes will break heuristics; recalibrate with fixtures.

## Confidence rubric

| Score | Meaning |
| --- | --- |
| **0.9** | On a Reels-like surface and both `creator_handle` and `caption_excerpt` were found |
| **0.7** | On a Reels-like surface and either creator or caption was found |
| **0.3** | Surface or scroll boundary only — weak identity; treat as low-trust for URL matching |

## Surface detection

Treat as Reels / For You when:

- Visible text includes `Reels`, `For you`, or `Para ti`, or
- Like + comment + share/send controls are all present

## Reel change

A new `reel_shown` is emitted when identity (creator/caption) changes after a scroll/window event, with a short debounce (`minReelIntervalMs`, default 400ms). Previous reel gets `reel_hidden` first.

## Interactions

Prefer labeled control clicks (`Like button`, `Comment`, `Share`, `Send`, `Save`) over double-tap. Kinds match the server schema: `like`, `unlike`, `comment_open`, `comment_send`, `share_open`, `send`, `save`, `profile_open`.

## Debug

`raw_a11y` is off by default. Enable only while calibrating; it is ignored by `sessionize`.
