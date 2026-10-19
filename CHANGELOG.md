# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Layered offline pipeline: `preprocess_queue.py` (L2) and `merge_sources.py` (L3); raw archives immutable
- Android `0.1.1-android`: `raw_a11y` nodes with bounds + `texts_sample`; on-device identity marked as hints
- `visualize_merged.py` for L3 `merged.csv` timelines (match status + logger dwell)
- PC phrase identity in preprocess (`Reel by X`, profile-picture labels, …) with chrome-token denylist

### Changed

- Docs: L0–L3 architecture, derived CSV columns, source-of-truth matrix, capture-max / process-on-PC
- Researcher runbook: Android `0.1.1-android`, Debug raw_a11y, clock-time viz (`--tz`)
- `compare_logger_dyi.py` is a thin alias for preprocess → merge
- Timeline scripts: absolute clock x-axis via `--tz` (default `Europe/Copenhagen`; use `UTC` for UTC)

## [0.1.0] — 2026-10-14

First tagged personal pilot release.

### Added

- Android accessibility logger (`dk.sdu.scrolllogger`) with local JSONL queue
- FastAPI ingest, sessionize, impressions, DYI import, and reconcile
- Researcher runbook, day sync script (`scripts/sync-day.ps1`)
- Queue timeline visualizer (`scripts/visualize_queue.py`)

### Changed

- Reel detector: chrome caption denylist, engagement-handle filter, share-sheet session continuity, interaction debounce
- Install scripts: JDK 17 resolution safe under PowerShell `$ErrorActionPreference = Stop`

### Notes

- Android client string: `0.1.0-android` (`BuildConfig.LOGGER_VERSION`)
- Python package / API: `0.1.0` (`app.__version__`, `pyproject.toml`)

[0.1.0]: https://github.com/pplvieira/reel-logger/releases/tag/v0.1.0
