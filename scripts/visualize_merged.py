#!/usr/bin/env python3
"""Timeline from L3 merged.csv (derived logger + DYI links).

Shows match_status on a shared time axis and dwell bars for logger-side rows.
This is preprocessed/merged data — not the raw phone JSONL.

Examples:
  python scripts/visualize_merged.py data/derived/<run_id>/merged.csv
  python scripts/visualize_merged.py data/derived/<run_id>/merged.csv --tz UTC
  python scripts/visualize_merged.py data/derived/<run_id>/merged.csv --no-show -o data/derived/<run_id>/merged_timeline.png
  python scripts/visualize_merged.py …/merged.csv --hide-dyi-only --tz Europe/Copenhagen
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

STATUS_COLORS = {
    "matched": "#2ca02c",
    "ambiguous": "#ff7f0e",
    "logger_only": "#1f77b4",
    "dyi_only": "#7f7f7f",
}

STATUS_Y = {
    "matched": 3.0,
    "ambiguous": 2.0,
    "logger_only": 1.0,
    "dyi_only": 0.0,
}


@dataclass
class MergeRow:
    match_status: str
    match_method: str
    match_dt_s: float | None
    shown_at: datetime | None
    watched_at: datetime | None
    dwell_ms: float | None
    creator_handle: str
    external_url: str
    identity_method: str


def parse_ts(value: str) -> datetime | None:
    if not value or not str(value).strip():
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def load_merged(path: Path) -> list[MergeRow]:
    rows: list[MergeRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            dt_s = None
            if r.get("match_dt_s"):
                try:
                    dt_s = float(r["match_dt_s"])
                except ValueError:
                    dt_s = None
            dwell = None
            if r.get("dwell_ms"):
                try:
                    dwell = float(r["dwell_ms"])
                except ValueError:
                    dwell = None
            rows.append(
                MergeRow(
                    match_status=r.get("match_status") or "",
                    match_method=r.get("match_method") or "",
                    match_dt_s=dt_s,
                    shown_at=parse_ts(r.get("shown_at") or ""),
                    watched_at=parse_ts(r.get("watched_at") or ""),
                    dwell_ms=dwell,
                    creator_handle=r.get("creator_handle") or "",
                    external_url=r.get("external_url") or "",
                    identity_method=r.get("identity_method") or "",
                )
            )
    return rows


def event_time(row: MergeRow) -> datetime | None:
    """Place point on timeline: logger shown_at if present, else DYI watched_at."""
    return row.shown_at or row.watched_at


def print_stats(rows: list[MergeRow]) -> None:
    print("[visualize] stage : L3 merged timeline (derived, not raw JSONL)")
    print(f"[visualize] rows  : {len(rows)}")
    print(f"[visualize] status: {dict(Counter(r.match_status for r in rows))}")
    matched = [r for r in rows if r.match_status == "matched" and r.dwell_ms is not None]
    if matched:
        dwells = sorted(r.dwell_ms for r in matched if r.dwell_ms is not None)
        mid = dwells[len(dwells) // 2]
        print(
            f"[visualize] matched dwell_ms: n={len(dwells)} "
            f"med={mid:.0f} min={dwells[0]:.0f} max={dwells[-1]:.0f}"
        )


def plot_merged(
    rows: list[MergeRow],
    *,
    out: Path | None,
    show: bool,
    hide_dyi_only: bool,
    title_suffix: str,
    tz_name: str,
) -> None:
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except ImportError:
        print("matplotlib not installed. Run: pip install matplotlib", file=sys.stderr)
        return

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        print(f"[visualize] ERROR unknown timezone {tz_name!r}", file=sys.stderr)
        return

    plot_rows = [r for r in rows if not (hide_dyi_only and r.match_status == "dyi_only")]
    timed = [(event_time(r), r) for r in plot_rows]
    timed = [(t, r) for t, r in timed if t is not None]
    if not timed:
        print("[visualize] ERROR no timestamps to plot", file=sys.stderr)
        return
    timed.sort(key=lambda x: x[0])
    # Display times in the chosen zone (matplotlib date axis)
    timed_local = [(t.astimezone(tz), r) for t, r in timed]
    t0 = timed_local[0][0]
    t1 = timed_local[-1][0]

    fig, (ax_tl, ax_dwell) = plt.subplots(
        2,
        1,
        figsize=(14, 7),
        gridspec_kw={"height_ratios": [2.0, 1.2]},
        sharex=True,
    )

    xs: list[datetime] = []
    ys: list[float] = []
    colors: list[str] = []
    labels: list[str] = []
    for t, r in timed_local:
        xs.append(t)
        ys.append(STATUS_Y.get(r.match_status, -0.5))
        colors.append(STATUS_COLORS.get(r.match_status, "#333333"))
        if r.match_status == "matched":
            handle = r.creator_handle or ""
            short = (r.external_url or "").rstrip("/").split("/")[-1][:12]
            labels.append(handle[:14] or short)
        elif r.match_status == "ambiguous":
            labels.append("amb")
        else:
            labels.append("")

    span_s = max((t1 - t0).total_seconds(), 1.0)
    x_pad = timedelta(seconds=max(60.0, span_s * 0.02))

    ax_tl.scatter(xs, ys, c=colors, s=36, alpha=0.85, zorder=3)

    # Sparse annotations for matched
    annotate_budget = 16
    matched_idx = [i for i, (_, r) in enumerate(timed_local) if r.match_status == "matched"]
    step = max(1, len(matched_idx) // annotate_budget) if matched_idx else 1
    for j, i in enumerate(matched_idx):
        if j % step != 0:
            continue
        lab = labels[i]
        if not lab:
            continue
        ax_tl.annotate(
            lab,
            (xs[i], ys[i]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=7,
            color=STATUS_COLORS["matched"],
            arrowprops=dict(arrowstyle="->", color="#999999", lw=0.6),
        )

    ax_tl.set_yticks([0.0, 1.0, 2.0, 3.0])
    ax_tl.set_yticklabels(["dyi_only", "logger_only", "ambiguous", "matched"])
    ax_tl.set_ylabel("match_status")
    ax_tl.set_title(
        f"L3 merged timeline ({tz_name})"
        + (f" — {title_suffix}" if title_suffix else "")
    )
    ax_tl.grid(True, axis="x", alpha=0.3)

    legend = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=STATUS_COLORS[k],
            markersize=9,
            label=k,
        )
        for k in ("matched", "ambiguous", "logger_only", "dyi_only")
        if any(r.match_status == k for _, r in timed_local)
    ]
    ax_tl.legend(handles=legend, loc="upper right", fontsize=8, ncol=4)

    # Dwell bars: logger-side rows only (have dwell_ms)
    dwell_rows = [
        (t, r)
        for t, r in timed_local
        if r.dwell_ms is not None and r.match_status in ("matched", "ambiguous", "logger_only")
    ]
    if dwell_rows:
        dx = [t for t, _ in dwell_rows]
        dw = [r.dwell_ms / 1000.0 for _, r in dwell_rows]
        bar_colors = [STATUS_COLORS.get(r.match_status, "#333") for _, r in dwell_rows]
        # bar width in days (matplotlib date units)
        bar_w_days = max(span_s / max(len(dx) * 35, 1), 30.0) / 86400.0
        ax_dwell.bar(dx, dw, width=bar_w_days, color=bar_colors, align="edge", zorder=3, alpha=0.85)
        ax_dwell.set_ylabel("dwell (s)")
        ax_dwell.set_title(
            "Logger dwell (green=matched URL, orange=ambiguous, blue=logger_only; no dwell from DYI)"
        )
        ax_dwell.grid(True, axis="y", alpha=0.3)
    else:
        ax_dwell.text(
            0.5,
            0.5,
            "No logger dwells in plot set",
            transform=ax_dwell.transAxes,
            ha="center",
        )

    locator = mdates.AutoDateLocator(minticks=5, maxticks=12)
    # Hour:Minute on short spans; include date when multi-day
    if span_s < 36 * 3600:
        formatter = mdates.DateFormatter("%H:%M", tz=tz)
        ax_dwell.set_xlabel(f"time ({tz_name}) — {t0.strftime('%Y-%m-%d')}")
    else:
        formatter = mdates.ConciseDateFormatter(locator, tz=tz)
        ax_dwell.set_xlabel(f"date / time ({tz_name})")

    for ax in (ax_tl, ax_dwell):
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.set_xlim(t0 - x_pad, t1 + x_pad)

    fig.autofmt_xdate()
    fig.tight_layout()
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=140)
        print(f"[visualize] wrote  : {out}")
    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("merged_csv", type=Path, help="L3 merged.csv from merge_sources.py")
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--no-show", action="store_true")
    ap.add_argument(
        "--hide-dyi-only",
        action="store_true",
        help="Omit DYI watches with no logger impression (cleaner pace view)",
    )
    ap.add_argument(
        "--matched-only",
        action="store_true",
        help="Plot only match_status=matched rows",
    )
    ap.add_argument(
        "--tz",
        default="Europe/Copenhagen",
        help="IANA timezone for x-axis labels (default Europe/Copenhagen; use UTC for UTC)",
    )
    args = ap.parse_args()

    if not args.merged_csv.exists():
        print(f"[visualize] ERROR missing {args.merged_csv}", file=sys.stderr)
        return 1

    rows = load_merged(args.merged_csv)
    if args.matched_only:
        rows = [r for r in rows if r.match_status == "matched"]
    print_stats(rows)
    print(f"[visualize] input : {args.merged_csv.resolve()}")
    print(f"[visualize] tz    : {args.tz}")

    out = args.output
    if out is None and args.no_show:
        out = args.merged_csv.with_name("merged_timeline.png")

    suffix = args.merged_csv.parent.name
    plot_merged(
        rows,
        out=out,
        show=not args.no_show,
        hide_dyi_only=args.hide_dyi_only or args.matched_only,
        title_suffix=suffix,
        tz_name=args.tz,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
