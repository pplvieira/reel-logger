"""L2: normalize phone JSONL eras → derived impressions (immutable L0)."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.derived import PREPROCESS_VERSION

UI_HANDLE_TOKENS = {
    "repost",
    "home",
    "play",
    "expand",
    "reels",
    "share",
    "send",
    "like",
    "comment",
    "save",
    "more",
    "seekbar",
    "audio",
    "for",
    "you",
    "friends",
    "message",
    "profile",
    "back",
}

CHROME_SUBSTRINGS = (
    "send post",
    "double-tap to choose who to send",
    "double-tap to play or pause",
    "double-tap to like",
    "view likes",
    "view comments",
    "the like number is",
    "comment number is",
    "reshare number is",
    "save number is",
    "search and explore",
    "like button",
    "chat not selected",
    "add comment",
)

RE_REEL_BY = re.compile(r"^Reel by ([^.]+)\.", re.I)
RE_PROFILE_PIC = re.compile(r"^Profile picture of (.+)$", re.I)
RE_POSTED = re.compile(r"^(.+?) posted a (video|reel|photo)", re.I)


@dataclass
class DerivedImpression:
    impression_id: str
    shown_at: str
    hidden_at: str
    dwell_ms: float
    creator_handle: str
    caption_excerpt: str
    identity_confidence: float
    identity_method: str
    quality_flags: str
    source_jsonl: str
    logger_version: str
    schema_era: str
    preprocess_version: str
    kept: bool = True
    dropped_reason: str = ""


@dataclass
class PreprocessResult:
    run_id: str
    out_dir: Path
    impressions_path: Path
    manifest_path: Path
    schema_era: str
    counts: dict[str, Any] = field(default_factory=dict)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_events(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def detect_era(events: list[dict[str, Any]]) -> str:
    has_raw = False
    has_nodes = False
    for e in events:
        if e.get("type") != "raw_a11y":
            continue
        has_raw = True
        payload = e.get("payload") or {}
        if payload.get("nodes"):
            has_nodes = True
            break
    if has_nodes:
        return "C"
    if has_raw:
        return "B"
    return "A"


def is_chrome(text: str | None) -> bool:
    if not text:
        return False
    s = text.lower()
    return any(m in s for m in CHROME_SUBSTRINGS)


def is_ui_handle(handle: str | None) -> bool:
    if not handle:
        return True
    h = handle.strip()
    if h.lower() in UI_HANDLE_TOKENS:
        return True
    core = (
        h.replace(".", "")
        .replace("K", "")
        .replace("k", "")
        .replace("M", "")
        .replace("m", "")
    )
    if core.isdigit():
        return True
    return False


def is_share_sheet(texts: list[str]) -> bool:
    joined = " ".join(texts).lower()
    return (
        "chat not selected" in joined
        or "whatsapp" in joined
        and "copy link" in joined
        or ("send to" in joined and "search" in joined)
    )


def texts_from_raw(payload: dict[str, Any]) -> list[str]:
    sample = payload.get("texts_sample")
    if isinstance(sample, list) and sample:
        return [str(t) for t in sample]
    nodes = payload.get("nodes")
    if isinstance(nodes, list):
        out: list[str] = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            for key in ("text", "contentDescription"):
                v = n.get(key)
                if v:
                    out.append(str(v))
        return out
    return []


def extract_identity_from_texts(
    texts: list[str],
) -> tuple[Optional[str], Optional[str], str, float]:
    """Return creator, caption, method, confidence from raw phrases."""
    creator: Optional[str] = None
    method = "none"
    for t in texts:
        m = RE_PROFILE_PIC.match(t.strip())
        if m:
            creator = m.group(1).strip()
            method = "raw_profile_picture"
            break
    if creator is None:
        for t in texts:
            m = RE_REEL_BY.match(t.strip())
            if m:
                creator = m.group(1).strip()
                method = "raw_reel_by"
                break
    if creator is None:
        for t in texts:
            m = RE_POSTED.match(t.strip())
            if m:
                creator = m.group(1).strip()
                method = "raw_posted_a"
                break

    caption: Optional[str] = None
    for t in texts:
        s = t.strip()
        if len(s) < 16 or len(s) > 240:
            continue
        if is_chrome(s):
            continue
        if RE_REEL_BY.match(s) or RE_PROFILE_PIC.match(s) or RE_POSTED.match(s):
            continue
        if s.lower() in UI_HANDLE_TOKENS:
            continue
        if creator and s.lower().startswith(creator.lower()) and len(s) > len(creator) + 2:
            caption = s
            break
        if caption is None and ("#" in s or " more" in s.lower() or len(s) >= 24):
            caption = s
    conf = 0.9 if creator and caption else (0.75 if creator else 0.3)
    return creator, caption, method, conf


def nearest_raw_texts(
    events: list[dict[str, Any]],
    at: datetime,
    window_s: float = 2.0,
) -> tuple[list[str], bool]:
    best: tuple[float, list[str], bool] | None = None
    for e in events:
        if e.get("type") != "raw_a11y":
            continue
        t = parse_ts(e["observed_at"])
        dt = abs((t - at).total_seconds())
        if dt > window_s:
            continue
        texts = texts_from_raw(e.get("payload") or {})
        sheet = is_share_sheet(texts)
        if best is None or dt < best[0]:
            best = (dt, texts, sheet)
    if best is None:
        return [], False
    return best[1], best[2]


def build_raw_impressions(
    events: list[dict[str, Any]],
    *,
    source_jsonl: str,
    schema_era: str,
) -> list[DerivedImpression]:
    imps: list[DerivedImpression] = []
    open_shown: dict[str, Any] | None = None

    def close(hidden_at: datetime) -> None:
        nonlocal open_shown
        if open_shown is None:
            return
        shown_at = parse_ts(open_shown["observed_at"])
        dwell = (hidden_at - shown_at).total_seconds() * 1000
        payload = open_shown.get("payload") or {}
        hints = payload.get("hints") if isinstance(payload.get("hints"), dict) else {}

        raw_texts, share_sheet = nearest_raw_texts(events, shown_at)
        creator: Optional[str] = None
        caption: Optional[str] = None
        method = "none"
        conf = 0.3

        # PC identity from raw wins when available (eras B/C)
        if raw_texts and not share_sheet:
            creator, caption, method, conf = extract_identity_from_texts(raw_texts)

        need_hint = creator is None or is_ui_handle(creator)
        if need_hint and (schema_era == "A" or not raw_texts or share_sheet):
            hint = hints.get("creator_handle") or payload.get("creator_handle")
            hint_cap = hints.get("caption_excerpt") or payload.get("caption_excerpt")
            if hint and not is_ui_handle(str(hint)):
                creator = str(hint)
                method = "on_device_hint"
                conf = 0.45
            elif hint and is_ui_handle(str(hint)):
                method = "on_device_hint_ui"
                conf = 0.2
            if hint_cap and not is_chrome(str(hint_cap)):
                caption = str(hint_cap)[:240]
                if method == "on_device_hint":
                    conf = 0.5

        flags: list[str] = []
        if dwell < 500:
            flags.append("short_dwell")
        if dwell < 2000:
            flags.append("under_2s")
        if share_sheet:
            flags.append("share_sheet_near")
        if caption and is_chrome(caption):
            flags.append("chrome_caption")
        if creator and is_ui_handle(creator):
            flags.append("ui_handle")
            creator = None
            if method.startswith("on_device"):
                method = "on_device_hint_ui"
            conf = min(conf, 0.25)
        if not creator and not caption:
            flags.append("no_identity")

        imps.append(
            DerivedImpression(
                impression_id=str(uuid.uuid4()),
                shown_at=shown_at.isoformat(),
                hidden_at=hidden_at.isoformat(),
                dwell_ms=round(dwell, 1),
                creator_handle=creator or "",
                caption_excerpt=(caption or "")[:240],
                identity_confidence=conf,
                identity_method=method,
                quality_flags=",".join(flags),
                source_jsonl=source_jsonl,
                logger_version="",
                schema_era=schema_era,
                preprocess_version=PREPROCESS_VERSION,
                kept=True,
            )
        )
        open_shown = None

    for e in events:
        typ = e.get("type")
        if typ == "reel_shown":
            if open_shown is not None:
                close(parse_ts(e["observed_at"]))
            open_shown = e
        elif typ in ("reel_hidden", "session_end") and open_shown is not None:
            close(parse_ts(e["observed_at"]))
    return imps


def apply_smoothing(
    imps: list[DerivedImpression],
    *,
    min_dwell_ms: float,
    drop_share_sheet: bool,
    drop_no_identity: bool,
) -> list[DerivedImpression]:
    """Flag/drop with audit fields; merge consecutive same identity flickers."""
    out: list[DerivedImpression] = []
    for imp in imps:
        flags = set(imp.quality_flags.split(",")) if imp.quality_flags else set()
        flags.discard("")
        reason = ""
        kept = True
        if imp.dwell_ms < min_dwell_ms:
            flags.add("short_dwell")
            kept = False
            reason = f"dwell_lt_{int(min_dwell_ms)}"
        if drop_share_sheet and "share_sheet_near" in flags:
            kept = False
            reason = reason or "share_sheet"
        if drop_no_identity and "no_identity" in flags and not imp.creator_handle:
            kept = False
            reason = reason or "no_identity"

        if (
            kept
            and out
            and out[-1].kept
            and out[-1].creator_handle
            and out[-1].creator_handle == imp.creator_handle
            and out[-1].caption_excerpt
            and out[-1].caption_excerpt == imp.caption_excerpt
        ):
            prev_hidden = parse_ts(out[-1].hidden_at)
            shown = parse_ts(imp.shown_at)
            if (shown - prev_hidden).total_seconds() < 2.0:
                # merge into previous
                out[-1].hidden_at = imp.hidden_at
                out[-1].dwell_ms = round(
                    (parse_ts(imp.hidden_at) - parse_ts(out[-1].shown_at)).total_seconds()
                    * 1000,
                    1,
                )
                flags.add("merged_flicker")
                out[-1].quality_flags = ",".join(sorted(set(out[-1].quality_flags.split(",")) | flags - {""}))
                continue

        imp.quality_flags = ",".join(sorted(flags))
        imp.kept = kept
        imp.dropped_reason = reason if not kept else ""
        out.append(imp)
    return out


def run_preprocess(
    jsonl: Path,
    *,
    out_root: Path,
    min_dwell_ms: float = 2000.0,
    keep_dropped: bool = True,
    drop_share_sheet: bool = True,
    drop_no_identity: bool = False,
    since: Optional[str] = None,
) -> PreprocessResult:
    events = load_events(jsonl)
    if since:
        since_dt = parse_ts(since if "T" in since else since + "T00:00:00Z")
        events = [e for e in events if parse_ts(e["observed_at"]) >= since_dt]

    era = detect_era(events)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + jsonl.stem[-12:]
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_imps = build_raw_impressions(
        events,
        source_jsonl=str(jsonl.resolve()),
        schema_era=era,
    )
    smoothed = apply_smoothing(
        raw_imps,
        min_dwell_ms=min_dwell_ms,
        drop_share_sheet=drop_share_sheet,
        drop_no_identity=drop_no_identity,
    )
    rows = smoothed if keep_dropped else [i for i in smoothed if i.kept]
    kept_n = sum(1 for i in smoothed if i.kept)

    impressions_path = out_dir / "impressions.csv"
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(asdict(DerivedImpression(
        impression_id="", shown_at="", hidden_at="", dwell_ms=0, creator_handle="",
        caption_excerpt="", identity_confidence=0, identity_method="", quality_flags="",
        source_jsonl="", logger_version="", schema_era="", preprocess_version="",
    )).keys())

    import csv

    with impressions_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(asdict(row))

    counts = {
        "events_in": len(events),
        "impressions_built": len(raw_imps),
        "impressions_written": len(rows),
        "impressions_kept": kept_n,
        "impressions_dropped": len(smoothed) - kept_n,
        "schema_era": era,
        "min_dwell_ms": min_dwell_ms,
    }
    manifest = {
        "preprocess_version": PREPROCESS_VERSION,
        "ruleset_id": "phrase_v1",
        "run_id": run_id,
        "source_jsonl": str(jsonl.resolve()),
        "schema_era": era,
        "counts": counts,
        "note": "L0 JSONL was not modified. Rows with kept=false are auditable drops.",
    }
    manifest_path = out_dir / "preprocess_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return PreprocessResult(
        run_id=run_id,
        out_dir=out_dir,
        impressions_path=impressions_path,
        manifest_path=manifest_path,
        schema_era=era,
        counts=counts,
    )
