#!/usr/bin/env python3
"""Histogram of logger dwell times from L3 merged.csv.

Bars can be stacked by match_status (matched / ambiguous / logger_only).
Optional linear KDE overlay.

Examples:
  python scripts/plot_dwell_hist.py data/derived/<run_id>/merged.csv
  python scripts/plot_dwell_hist.py …/merged.csv --no-stack-by-status --bins 40
  python scripts/plot_dwell_hist.py …/merged.csv --bin-width-s 5 --kde --no-show -o out/dwell.png
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from bisect import bisect_left
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from viz_common import (  # noqa: E402
    COLOR_SMOOTH,
    COLOR_TEXT,
    DEFAULT_DPI,
    LOGGER_DWELL_STATUSES,
    STATUS_COLORS,
    MergeRow,
    apply_sleek_style,
    filter_rows,
    gaussian_kde_1d,
    load_merged_rows,
    parse_statuses,
    require_matplotlib,
    save_or_show,
    scale_curve_to_profile,
    silverman_bandwidth,
    status_order,
)


def dwell_seconds_with_status(rows: list[MergeRow]) -> list[tuple[float, str]]:
    return [(r.dwell_ms / 1000.0, r.match_status) for r in rows if r.dwell_ms is not None]


def compute_bin_edges(
    values: list[float],
    *,
    bins: int | None,
    bin_width_s: float | None,
    clip_max_s: float | None,
) -> tuple[list[float], int]:
    """Return (edges, n_clipped)."""
    if not values:
        return [0.0, 1.0], 0
    clipped = 0
    xs = list(values)
    if clip_max_s is not None and clip_max_s > 0:
        clipped = sum(1 for v in xs if v > clip_max_s)
        xs = [min(v, clip_max_s) for v in xs]
    lo = 0.0
    hi = max(xs) if xs else 1.0
    if hi <= lo:
        hi = lo + 1.0

    if bin_width_s is not None and bin_width_s > 0:
        n = max(1, int(math.ceil((hi - lo) / bin_width_s)))
        edges = [lo + i * bin_width_s for i in range(n + 1)]
        if edges[-1] < hi - 1e-12:
            edges.append(hi)
        return edges, clipped

    n_bins = bins if bins is not None and bins > 0 else 30
    width = (hi - lo) / n_bins
    edges = [lo + i * width for i in range(n_bins + 1)]
    return edges, clipped


def _bin_index(v: float, edges: list[float]) -> int | None:
    n_bins = len(edges) - 1
    if n_bins < 1 or v < edges[0] or v > edges[-1]:
        return None
    if v == edges[-1]:
        return n_bins - 1
    # edges are sorted ascending
    i = bisect_left(edges, v) - 1
    if i < 0:
        i = 0
    if i >= n_bins:
        i = n_bins - 1
    if edges[i] <= v < edges[i + 1] or (i == n_bins - 1 and v <= edges[-1]):
        return i
    return None


def hist_counts_by_status(
    pairs: list[tuple[float, str]],
    edges: list[float],
    statuses: list[str],
) -> dict[str, list[int]]:
    n_bins = len(edges) - 1
    counts = {s: [0] * n_bins for s in statuses}
    for v, status in pairs:
        if status not in counts:
            continue
        idx = _bin_index(v, edges)
        if idx is not None:
            counts[status][idx] += 1
    return counts


def total_hist_counts(pairs: list[tuple[float, str]], edges: list[float]) -> list[int]:
    n_bins = len(edges) - 1
    heights = [0] * n_bins
    for v, _ in pairs:
        idx = _bin_index(v, edges)
        if idx is not None:
            heights[idx] += 1
    return heights


def print_stats(rows: list[MergeRow], values: list[float], *, clipped: int) -> None:
    print("[dwell-hist] stage : L3 dwell histogram")
    print(f"[dwell-hist] rows  : {len(rows)} (with dwell)")
    print(f"[dwell-hist] status: {dict(Counter(r.match_status for r in rows))}")
    if values:
        print(
            f"[dwell-hist] dwell_s: n={len(values)} "
            f"med={statistics.median(values):.1f} "
            f"mean={statistics.mean(values):.1f} "
            f"max={max(values):.1f}"
        )
    if clipped:
        print(f"[dwell-hist] clipped above max-dwell: {clipped}")


def plot_dwell_histogram(
    pairs: list[tuple[float, str]],
    edges: list[float],
    *,
    stack_by_status: bool,
    show_kde: bool,
    title: str,
    xlabel: str,
    dpi: int,
    output: Path | None,
    show: bool,
) -> None:
    plt = require_matplotlib()

    values = [v for v, _ in pairs]
    present = status_order(s for _, s in pairs)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    apply_sleek_style(ax, grid_axis="y")

    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
    widths = [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]
    bar_w = [w * 0.92 for w in widths]

    if stack_by_status and present:
        counts = hist_counts_by_status(pairs, edges, present)
        bottom = [0] * len(centers)
        for status in present:
            heights = counts[status]
            ax.bar(
                centers,
                heights,
                width=bar_w,
                bottom=bottom,
                color=STATUS_COLORS.get(status, "#CCCCCC"),
                alpha=0.88,
                edgecolor="white",
                linewidth=0.4,
                label=status,
                zorder=2,
                align="center",
            )
            bottom = [b + h for b, h in zip(bottom, heights)]
        total_heights = bottom
    else:
        total_heights = total_hist_counts(pairs, edges)
        ax.bar(
            centers,
            total_heights,
            width=bar_w,
            color=STATUS_COLORS.get("matched", "#7DCFB6"),
            alpha=0.88,
            edgecolor="white",
            linewidth=0.4,
            zorder=2,
            align="center",
        )

    if show_kde and values:
        bw = silverman_bandwidth(values)
        grid_n = max(200, len(edges) * 8)
        g_lo, g_hi = edges[0], edges[-1]
        grid = [g_lo + i * (g_hi - g_lo) / (grid_n - 1) for i in range(grid_n)]
        density = gaussian_kde_1d(values, grid, bandwidth=bw)
        mean_width = statistics.mean(widths) if widths else 1.0
        scaled = [d * len(values) * mean_width for d in density]
        # Match peak to tallest bar so long-tail dwells do not blow the y-axis
        sampled = []
        for c in centers:
            j = min(max(bisect_left(grid, c), 0), len(grid) - 1)
            sampled.append(scaled[j])
        peak_bar = max(total_heights) if total_heights else 0
        peak_curve = max(sampled) if sampled else 0
        if peak_bar > 0 and peak_curve > 0:
            factor = peak_bar / peak_curve
            scaled = [y * factor for y in scaled]
        elif sampled and any(total_heights):
            scaled_mids = scale_curve_to_profile(sampled, total_heights)
            s_mean = sum(sampled) / len(sampled)
            if s_mean > 0:
                factor = (sum(scaled_mids) / len(scaled_mids)) / s_mean
                scaled = [y * factor for y in scaled]
        ax.plot(grid, scaled, color=COLOR_SMOOTH, linewidth=2.2, alpha=0.9, label="KDE", zorder=3)

    handles, _labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(frameon=False, fontsize=9, loc="upper right")

    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel("count", fontsize=10)
    ax.set_title(title, fontsize=13, color=COLOR_TEXT, pad=10)
    ax.set_xlim(edges[0], edges[-1])
    ax.set_ylim(bottom=0)

    save_or_show(fig, output, show=show, dpi=dpi)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("merged_csv", type=Path, help="L3 merged.csv from merge_sources.py")
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--no-show", action="store_true")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument(
        "--statuses",
        default="",
        help="Comma-separated match_status values (default: matched,ambiguous,logger_only)",
    )
    ap.add_argument(
        "--stack-by-status",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stack histogram bars by match_status (default: on)",
    )
    ap.add_argument("--bins", type=int, default=None, help="Number of bins (default 30 if no width)")
    ap.add_argument("--bin-width-s", type=float, default=None, help="Fixed bin width in seconds")
    ap.add_argument("--max-dwell-s", type=float, default=None, help="Clip dwells above this (seconds)")
    ap.add_argument("--kde", action="store_true", help="Overlay linear Gaussian KDE")
    ap.add_argument("--title", default="", help="Override plot title")
    ap.add_argument("--xlabel", default="dwell (s)", help="X-axis label")
    args = ap.parse_args()

    if args.bins is not None and args.bin_width_s is not None:
        print("[dwell-hist] ERROR use only one of --bins or --bin-width-s", file=sys.stderr)
        return 1
    if not args.merged_csv.exists():
        print(f"[dwell-hist] ERROR missing {args.merged_csv}", file=sys.stderr)
        return 1

    statuses = parse_statuses(args.statuses, default=LOGGER_DWELL_STATUSES)
    rows = filter_rows(
        load_merged_rows(args.merged_csv),
        statuses=statuses,
        require_dwell=True,
    )
    pairs = dwell_seconds_with_status(rows)
    values = [v for v, _ in pairs]
    edges, clipped = compute_bin_edges(
        values,
        bins=args.bins,
        bin_width_s=args.bin_width_s,
        clip_max_s=args.max_dwell_s,
    )
    if args.max_dwell_s is not None and args.max_dwell_s > 0:
        pairs = [(min(v, args.max_dwell_s), s) for v, s in pairs]

    print_stats(rows, values, clipped=clipped)
    print(f"[dwell-hist] input : {args.merged_csv.resolve()}")
    print(f"[dwell-hist] stack : {args.stack_by_status}  kde={args.kde}")

    title = args.title or (
        f"Dwell distribution (n={len(pairs)}"
        + (f", clipped={clipped}" if clipped else "")
        + ")"
    )

    out = args.output
    if out is None and args.no_show:
        out = args.merged_csv.with_name("dwell_hist.png")

    plot_dwell_histogram(
        pairs,
        edges,
        stack_by_status=args.stack_by_status,
        show_kde=args.kde,
        title=title,
        xlabel=args.xlabel,
        dpi=args.dpi,
        output=out,
        show=not args.no_show,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
