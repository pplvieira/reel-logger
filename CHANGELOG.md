# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

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
