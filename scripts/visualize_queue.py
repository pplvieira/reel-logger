#!/usr/bin/env python3
"""Timeline + summary stats for a phone-queue JSONL pull.

Examples:
  python scripts/visualize_queue.py data/phone-queue/events-20261014-170249.jsonl
  python scripts/visualize_queue.py data/phone-queue/events-….jsonl --clean --no-show -o out/day.png
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


EVENT_COLORS = {
    "session_start": "#2ca02c",
    "session_end": "#d62728",
    "reel_shown": "#1f77b4",
    "reel_hidden": "#aec7e8",
    "interaction": "#ff7f0e",
    "raw_a11y": "#7f7f7f",
}

CHROME_MARKERS = (
    "send post",
    "double-tap to choose who to send",
    "double-tap to play or pause",
    "double-tap to like",
    "like button",
    "comment button",
    "share button",
)


@dataclass
class Event:
    event_id: str
    type: str
    observed_at: datetime
    payload: dict


@dataclass
class Impression:
    shown_at: datetime
    hidden_at: datetime | None
    creator: str | None
    caption: str | None
    confidence: float | None
    dwell_ms: float | None = None
    chrome: bool = False


@dataclass
class Session:
    started_at: datetime
    ended_at: datetime | None = None
    end_reason: str | None = None
    impressions: list[Impression] = field(default_factory=list)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def is_chrome_caption(text: str | None) -> bool:
    if not text:
        return True
    s = text.strip().lower()
    return any(m in s for m in CHROME_MARKERS)


def is_bad_handle(handle: str | None) -> bool:
    if not handle:
        return True
    if handle.replace(".", "", 1).replace("K", "").replace("k", "").replace("M", "").replace("m", "").isdigit():
        return True
    if handle.isdigit() and len(handle) >= 5:
        return True
    return False


def load_events(path: Path) -> list[Event]:
    out: list[Event] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        out.append(
            Event(
                event_id=raw.get("event_id", ""),
                type=raw["type"],
                observed_at=parse_ts(raw["observed_at"]),
                payload=raw.get("payload") or {},
            )
        )
    return out


def clean_events(events: list[Event]) -> list[Event]:
    """Post-process heuristics for already-captured JSONL (does not mutate phone)."""
    cleaned: list[Event] = []
    last_interaction: tuple[str, datetime] | None = None
    for e in events:
        if e.type == "interaction":
            kind = e.payload.get("kind", "")
            if last_interaction and last_interaction[0] == kind:
                if (e.observed_at - last_interaction[1]).total_seconds() < 0.6:
                    continue
            last_interaction = (kind, e.observed_at)
            cleaned.append(e)
            continue

        if e.type == "reel_shown":
            payload = dict(e.payload)
            cap = payload.get("caption_excerpt")
            handle = payload.get("creator_handle")
            if is_chrome_caption(cap):
                payload.pop("caption_excerpt", None)
            if is_bad_handle(handle):
                payload.pop("creator_handle", None)
            # Drop chrome-only shown events with no identity left
            if not payload.get("caption_excerpt") and not payload.get("creator_handle"):
                continue
            cleaned.append(Event(e.event_id, e.type, e.observed_at, payload))
            continue

        cleaned.append(e)
    return cleaned


def build_sessions(events: list[Event]) -> list[Session]:
    sessions: list[Session] = []
    current: Session | None = None
    open_imp: Impression | None = None

    def close_imp(at: datetime) -> None:
        nonlocal open_imp
        if open_imp is None or current is None:
            open_imp = None
            return
        open_imp.hidden_at = at
        open_imp.dwell_ms = (at - open_imp.shown_at).total_seconds() * 1000
        current.impressions.append(open_imp)
        open_imp = None

    for e in events:
        if e.type == "session_start":
            if current and current.ended_at is None:
                close_imp(e.observed_at)
                current.ended_at = e.observed_at
                current.end_reason = "overlap"
            current = Session(started_at=e.observed_at)
            sessions.append(current)
        elif e.type == "reel_shown":
            if current is None:
                current = Session(started_at=e.observed_at)
                sessions.append(current)
            close_imp(e.observed_at)
            cap = e.payload.get("caption_excerpt")
            open_imp = Impression(
                shown_at=e.observed_at,
                hidden_at=None,
                creator=e.payload.get("creator_handle"),
                caption=cap,
                confidence=e.payload.get("confidence"),
                # Only flag when a caption is present and looks like UI chrome
                chrome=bool(cap) and is_chrome_caption(cap),
            )
        elif e.type == "reel_hidden":
            close_imp(e.observed_at)
        elif e.type == "session_end":
            close_imp(e.observed_at)
            if current and current.ended_at is None:
                current.ended_at = e.observed_at
                current.end_reason = e.payload.get("end_reason")
            current = None
    if open_imp is not None and current is not None:
        current.impressions.append(open_imp)
    return sessions


def print_stats(events: list[Event], sessions: list[Session]) -> None:
    types = Counter(e.type for e in events)
    kinds = Counter(e.payload.get("kind") for e in events if e.type == "interaction")
    ends = Counter(s.end_reason for s in sessions)

    impressions = [i for s in sessions for i in s.impressions]
    dwells = [i.dwell_ms for i in impressions if i.dwell_ms is not None]
    chrome_n = sum(1 for i in impressions if i.chrome)
    bad_handles = sum(1 for i in impressions if is_bad_handle(i.creator) and i.creator)

    sess_durs = []
    for s in sessions:
        if s.ended_at:
            sess_durs.append((s.ended_at - s.started_at).total_seconds())

    print("=== Event counts ===")
    for k, v in types.most_common():
        print(f"  {k:16} {v}")
    if kinds:
        print("=== Interactions ===")
        for k, v in kinds.most_common():
            print(f"  {k:16} {v}")
    print("=== Sessions ===")
    print(f"  count            {len(sessions)}")
    print(f"  end_reasons      {dict(ends)}")
    if sess_durs:
        print(
            f"  duration_s       "
            f"min={min(sess_durs):.1f}  med={statistics.median(sess_durs):.1f}  "
            f"mean={statistics.mean(sess_durs):.1f}  max={max(sess_durs):.1f}"
        )
        print(f"  under_3s         {sum(1 for d in sess_durs if d < 3)} / {len(sess_durs)}")
    print("=== Impressions ===")
    print(f"  count            {len(impressions)}")
    print(f"  chrome_caption   {chrome_n}")
    print(f"  bad_handles      {bad_handles}")
    if dwells:
        print(
            f"  dwell_ms         "
            f"min={min(dwells):.0f}  med={statistics.median(dwells):.0f}  "
            f"mean={statistics.mean(dwells):.0f}  p90={sorted(dwells)[int(len(dwells)*0.9)]:.0f}  "
            f"max={max(dwells):.0f}"
        )
        print(
            f"  dwell buckets    "
            f"<0.5s={sum(1 for d in dwells if d < 500)}  "
            f"0.5–2s={sum(1 for d in dwells if 500 <= d < 2000)}  "
            f"2–15s={sum(1 for d in dwells if 2000 <= d < 15000)}  "
            f">=15s={sum(1 for d in dwells if d >= 15000)}"
        )
        real = [d for d, i in zip(dwells, [x for x in impressions if x.dwell_ms is not None]) if not i.chrome and d >= 500]
        if real:
            print(
                f"  dwell_ms (clean) "
                f"n={len(real)}  med={statistics.median(real):.0f}  mean={statistics.mean(real):.0f}"
            )


def plot_timeline(events: list[Event], sessions: list[Session], out: Path | None, show: bool) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except ImportError:
        print("matplotlib not installed. Run: pip install matplotlib", file=sys.stderr)
        return

    if not events:
        print("No events to plot", file=sys.stderr)
        return

    t0 = events[0].observed_at
    xs: list[float] = []
    ys: list[float] = []
    colors: list[str] = []
    labels: list[str] = []

    y_map = {
        "session_start": 4,
        "session_end": 4,
        "reel_shown": 3,
        "reel_hidden": 2.5,
        "interaction": 1.5,
        "raw_a11y": 0.5,
    }

    fig, (ax_tl, ax_dwell) = plt.subplots(
        2,
        1,
        figsize=(14, 7),
        gridspec_kw={"height_ratios": [2.2, 1]},
        sharex=True,
    )

    for e in events:
        sec = (e.observed_at - t0).total_seconds()
        y = y_map.get(e.type, 0.5)
        xs.append(sec)
        ys.append(y)
        colors.append(EVENT_COLORS.get(e.type, "#333333"))
        if e.type == "interaction":
            labels.append(str(e.payload.get("kind", "")))
        elif e.type == "session_end":
            labels.append(str(e.payload.get("end_reason", "")))
        elif e.type == "reel_shown":
            h = e.payload.get("creator_handle") or ""
            labels.append(h[:18])
        else:
            labels.append("")

    x_max = max(xs) if xs else 1.0
    x_pad = max(1.0, x_max * 0.02)

    ax_tl.scatter(xs, ys, c=colors, s=28, alpha=0.85, zorder=3)

    # Session spans as background bands (both panels)
    for i, s in enumerate(sessions):
        end = s.ended_at or events[-1].observed_at
        x0 = (s.started_at - t0).total_seconds()
        x1 = (end - t0).total_seconds()
        band = "#dddddd" if i % 2 == 0 else "#eeeeee"
        ax_tl.axvspan(x0, x1, color=band, alpha=0.7, zorder=0)
        ax_dwell.axvspan(x0, x1, color=band, alpha=0.7, zorder=0)

    # Annotate a sparse sample of interactions / reel_shown
    annotate_budget = 18
    step = max(1, len(events) // annotate_budget)
    for i, (x, y, lab, e) in enumerate(zip(xs, ys, labels, events)):
        if not lab:
            continue
        if e.type not in ("interaction", "reel_shown", "session_end"):
            continue
        if i % step != 0 and e.type != "interaction":
            continue
        ax_tl.annotate(
            lab,
            (x, y),
            textcoords="offset points",
            xytext=(0, 8 if e.type == "interaction" else -12),
            ha="center",
            fontsize=7,
            color=EVENT_COLORS.get(e.type, "#333"),
            arrowprops=dict(arrowstyle="->", color="#999999", lw=0.6),
        )

    ax_tl.set_yticks([0.5, 1.5, 2.5, 3, 4])
    ax_tl.set_yticklabels(["raw_a11y", "interaction", "reel_hidden", "reel_shown", "session"])
    ax_tl.set_ylabel("event type")
    ax_tl.set_title(f"Scroll timeline from {t0.isoformat()}")
    ax_tl.grid(True, axis="x", alpha=0.3)

    legend = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=8, label=k)
        for k, c in EVENT_COLORS.items()
        if any(e.type == k for e in events)
    ]
    ax_tl.legend(handles=legend, loc="upper right", fontsize=8, ncol=3)

    # Dwell bars for closed impressions (same time origin / xlim as top panel)
    impressions = [i for s in sessions for i in s.impressions if i.dwell_ms is not None]
    if impressions:
        dx = [(i.shown_at - t0).total_seconds() for i in impressions]
        dw = [i.dwell_ms / 1000.0 for i in impressions]
        bar_colors = ["#bbbbbb" if i.chrome else "#1f77b4" for i in impressions]
        bar_w = max(0.4, x_max / max(len(dx) * 40, 1))
        ax_dwell.bar(dx, dw, width=bar_w, color=bar_colors, align="edge", zorder=3)
        ax_dwell.set_ylabel("dwell (s)")
        ax_dwell.set_title("Impression dwell (grey = chrome/noisy caption)")
        ax_dwell.grid(True, axis="y", alpha=0.3)
    else:
        ax_dwell.text(0.5, 0.5, "No closed impressions", transform=ax_dwell.transAxes, ha="center")

    ax_dwell.set_xlabel(f"seconds since {t0.strftime('%H:%M:%S')} UTC")
    ax_tl.set_xlim(-x_pad, x_max + x_pad)
    # sharex=True keeps ax_dwell aligned; reinforce after bar plot autoscaling
    ax_dwell.set_xlim(-x_pad, x_max + x_pad)

    fig.tight_layout()
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=140)
        print(f"Wrote {out}")
    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="Phone-queue events-*.jsonl")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Apply post-process filters (drop chrome-only reels, debounce interactions)",
    )
    parser.add_argument("-o", "--output", type=Path, default=None, help="Save figure PNG/PDF")
    parser.add_argument("--no-show", action="store_true", help="Do not open an interactive window")
    parser.add_argument("--no-plot", action="store_true", help="Stats only")
    args = parser.parse_args()

    if not args.jsonl.exists():
        print(f"File not found: {args.jsonl}", file=sys.stderr)
        return 1

    events = load_events(args.jsonl)
    if args.clean:
        before = len(events)
        events = clean_events(events)
        print(f"Post-process: {before} -> {len(events)} events\n")

    sessions = build_sessions(events)
    print_stats(events, sessions)
    print()

    if not args.no_plot:
        out = args.output
        if out is None and args.no_show:
            out = args.jsonl.with_suffix(".timeline.png")
        plot_timeline(events, sessions, out=out, show=not args.no_show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
