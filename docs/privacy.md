# Privacy

## Scope

This project is a **personal pilot** on your own phone and PC. It is not a multi-participant instrument. Enrolling any other device or person requires a separate decision (and, for research use, ethics review).

## On device

- Capture is explicit: you enable Accessibility (Android) and a visible “logging on” notification stays on while recording.
- No screenshots, no screen recording, no microphone, no contacts.
- Only the Instagram package is targeted by the planned Android listener. Other apps are not observed.
- Local queue on the phone until you sync or export. Prefer no `INTERNET` permission until wireless sync to your PC is intentionally added.

## On PC

- Default API bind: `127.0.0.1` (localhost).
- Default store: local SQLite under `./data/`.
- API token is reserved for when the service listens on the LAN; unused while localhost-only.
- DYI exports and logs may contain account handles and media URLs. Keep them out of public repos (see `.gitignore`).

## What is stored

- Semantic scroll events, sessions, impressions, interactions
- Optional content records from your Instagram data download
- No password or Meta credentials

## What is not stored

- Full accessibility trees in normal operation (`raw_a11y` is calibration-only and off by default)
- Screenshots or video of the feed
- Other users’ devices without an explicit enrollment decision

## Research note

If this logger is later used with participants, treat it as a new instrument: informed consent, data minimization, retention limits, and a review of Accessibility-based capture under your ethics protocol. The personal pilot does not substitute for that review.
