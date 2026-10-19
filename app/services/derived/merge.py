"""L3: merge derived impressions (L2) with DYI content rows. Never invents dwell."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.derived import MERGE_VERSION
from app.services.importers.dyi import parse_videos_watched_document


@dataclass
class MergeRow:
    match_status: str
    match_method: str
    match_dt_s: str
    impression_id: str
    shown_at: str
    hidden_at: str
    dwell_ms: str
    creator_handle: str
    caption_excerpt: str
    identity_method: str
    quality_flags: str
    watched_at: str
    external_url: str
    dyi_caption: str
    fbid: str
    source_jsonl: str
    source_export_path: str
    merge_version: str


def parse_ts(value: str) -> datetime:
    if not value:
        raise ValueError("empty timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_impressions_csv(path: Path, *, kept_only: bool = True) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if kept_only:
        rows = [r for r in rows if r.get("kept", "True") in ("True", "true", "1", "")]
    return rows


def load_dyi(export_root: Path) -> tuple[list[Any], Path]:
    videos = (
        export_root
        / "ads_information"
        / "ads_and_topics"
        / "videos_watched.json"
    )
    if not videos.exists():
        raise FileNotFoundError(f"Missing {videos}")
    doc = json.loads(videos.read_text(encoding="utf-8"))
    return parse_videos_watched_document(doc), videos


def _compatible(imp: dict[str, Any], watch: Any) -> bool:
    """Soft agreement: do not reject on missing fields."""
    cap_i = (imp.get("caption_excerpt") or "").strip().lower()
    cap_w = (watch.caption or "").strip().lower()
    if cap_i and cap_w and len(cap_i) >= 12 and len(cap_w) >= 12:
        if cap_i[:40] in cap_w or cap_w[:40] in cap_i:
            return True
        # different captions — still allow time-only match (caller ranks)
    return True


def merge_impressions_dyi(
    impressions: list[dict[str, Any]],
    watches: list[Any],
    *,
    export_path: Path,
    window_seconds: int = 180,
) -> list[MergeRow]:
    window = timedelta(seconds=window_seconds)
    used_imp: set[int] = set()
    rows: list[MergeRow] = []

    timed = [w for w in watches if w.watched_at is not None]
    timed.sort(key=lambda w: w.watched_at)

    for w in timed:
        candidates: list[tuple[float, int, str]] = []
        for i, imp in enumerate(impressions):
            if i in used_imp:
                continue
            shown = parse_ts(imp["shown_at"])
            hidden = parse_ts(imp["hidden_at"]) if imp.get("hidden_at") else shown
            start = shown - window
            end = hidden + window
            if not (start <= w.watched_at <= end):
                continue
            if not _compatible(imp, w):
                continue
            mid = shown + (hidden - shown) / 2
            dt = abs((w.watched_at - mid).total_seconds())
            method = "time_window"
            cap_i = (imp.get("caption_excerpt") or "").lower()
            cap_w = (w.caption or "").lower()
            if cap_i and cap_w and (cap_i[:32] in cap_w or cap_w[:32] in cap_i):
                method = "time_plus_caption"
                dt *= 0.5
            creator = (imp.get("creator_handle") or "").lower()
            if creator and w.creator_handle and creator == w.creator_handle.lower():
                method = "time_plus_creator" if method == "time_window" else method
                dt *= 0.8
            candidates.append((dt, i, method))

        if not candidates:
            rows.append(
                MergeRow(
                    match_status="dyi_only",
                    match_method="",
                    match_dt_s="",
                    impression_id="",
                    shown_at="",
                    hidden_at="",
                    dwell_ms="",
                    creator_handle="",
                    caption_excerpt="",
                    identity_method="",
                    quality_flags="",
                    watched_at=w.watched_at.isoformat(),
                    external_url=w.external_url or "",
                    dyi_caption=(w.caption or "")[:240],
                    fbid=w.fbid or "",
                    source_jsonl="",
                    source_export_path=str(export_path),
                    merge_version=MERGE_VERSION,
                )
            )
            continue

        candidates.sort(key=lambda x: x[0])
        # Ambiguous if two candidates within 15% of best dt and < 30s
        best_dt, best_i, best_method = candidates[0]
        status = "matched"
        if len(candidates) > 1:
            second = candidates[1][0]
            if second <= max(best_dt * 1.15, best_dt + 5) and second < 30:
                status = "ambiguous"

        # Reserve impression for both unique and ambiguous so it is not also logger_only
        used_imp.add(best_i)
        imp = impressions[best_i]
        rows.append(
            MergeRow(
                match_status=status,
                match_method=best_method if status == "matched" else "ambiguous_time",
                match_dt_s=f"{best_dt:.1f}",
                impression_id=imp.get("impression_id", ""),
                shown_at=imp.get("shown_at", ""),
                hidden_at=imp.get("hidden_at", ""),
                dwell_ms=str(imp.get("dwell_ms", "")),
                creator_handle=imp.get("creator_handle", ""),
                caption_excerpt=imp.get("caption_excerpt", ""),
                identity_method=imp.get("identity_method", ""),
                quality_flags=imp.get("quality_flags", ""),
                watched_at=w.watched_at.isoformat(),
                external_url=w.external_url or "",
                dyi_caption=(w.caption or "")[:240],
                fbid=w.fbid or "",
                source_jsonl=imp.get("source_jsonl", ""),
                source_export_path=str(export_path),
                merge_version=MERGE_VERSION,
            )
        )

    for i, imp in enumerate(impressions):
        if i in used_imp:
            continue
        # skip impressions only used in ambiguous? still logger_only if not uniquely matched
        matched_ids = {r.impression_id for r in rows if r.match_status == "matched"}
        if imp.get("impression_id") in matched_ids:
            continue
        rows.append(
            MergeRow(
                match_status="logger_only",
                match_method="",
                match_dt_s="",
                impression_id=imp.get("impression_id", ""),
                shown_at=imp.get("shown_at", ""),
                hidden_at=imp.get("hidden_at", ""),
                dwell_ms=str(imp.get("dwell_ms", "")),
                creator_handle=imp.get("creator_handle", ""),
                caption_excerpt=imp.get("caption_excerpt", ""),
                identity_method=imp.get("identity_method", ""),
                quality_flags=imp.get("quality_flags", ""),
                watched_at="",
                external_url="",
                dyi_caption="",
                fbid="",
                source_jsonl=imp.get("source_jsonl", ""),
                source_export_path=str(export_path),
                merge_version=MERGE_VERSION,
            )
        )
    return rows


def run_merge(
    impressions_csv: Path,
    export_root: Path,
    *,
    window_seconds: int = 180,
    kept_only: bool = True,
    out_path: Optional[Path] = None,
) -> tuple[Path, Counter]:
    impressions = load_impressions_csv(impressions_csv, kept_only=kept_only)
    watches, videos_path = load_dyi(export_root)
    rows = merge_impressions_dyi(
        impressions,
        watches,
        export_path=videos_path,
        window_seconds=window_seconds,
    )
    if out_path is None:
        out_path = impressions_csv.parent / "merged.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
            w.writeheader()
            for r in rows:
                w.writerow(asdict(r))
        else:
            f.write("")
    counts = Counter(r.match_status for r in rows)
    manifest = {
        "merge_version": MERGE_VERSION,
        "impressions_csv": str(impressions_csv.resolve()),
        "export_root": str(export_root.resolve()),
        "videos_watched": str(videos_path),
        "window_seconds": window_seconds,
        "counts": dict(counts),
        "note": "Dwell never taken from DYI. L0 archives untouched.",
    }
    (out_path.parent / "merge_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return out_path, counts
