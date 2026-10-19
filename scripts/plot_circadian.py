#!/usr/bin/env python3
"""Wrap-around 24h average-day barplot from L3 merged.csv.

Y metrics: count | watch_time_s | reels_per_minute.
Optional circular smooth overlay: --smooth kde|moving.
Optional per-hour error bars across active days: --error sd|sem.

Examples:
  python scripts/plot_circadian.py data/derived/<run_id>/merged.csv
  python scripts/plot_circadian.py …/merged.csv --metric watch_time_s --smooth kde
  python scripts/plot_circadian.py …/merged.csv --error sem --no-show -o out/day.png
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from viz_common import (  # noqa: E402
    COLOR_BAR,
    COLOR_SMOOTH,
    COLOR_TEXT,
    DEFAULT_DPI,
    DEFAULT_TZ,
    LOGGER_DWELL_STATUSES,
    MergeRow,
    apply_sleek_style,
    filter_rows,
    gaussian_kde_1d,
    load_merged_rows,
    parse_statuses,
    require_matplotlib,
    resolve_tz,
    save_or_show,
    scale_curve_to_profile,
    silverman_bandwidth,
)

METRICS = ("count", "watch_time_s", "reels_per_minute")
METRIC_LABELS = {
    "count": "reels (mean per day)",
    "watch_time_s": "watch time (s, mean per day)",
    "reels_per_minute": "reels / minute (mean per day)",
}


def local_event_times(rows: Sequence[MergeRow], tz: ZoneInfo) -> list[tuple[MergeRow, datetime]]:
    out: list[tuple[MergeRow, datetime]] = []
    for r in rows:
        if r.shown_at is None:
            continue
        out.append((r, r.shown_at.astimezone(tz)))
    return out


def fractional_hours(dt: datetime) -> float:
    return dt.hour + dt.minute / 60.0 + dt.second / 3600.0


def hour_day_keys(dt: datetime) -> tuple[date, int]:
    return dt.date(), dt.hour


def row_contribution(row: MergeRow, metric: str) -> float:
    if metric == "count":
        return 1.0
    if metric == "watch_time_s":
        return (row.dwell_ms or 0.0) / 1000.0
    if metric == "reels_per_minute":
        return 1.0  # convert after hourly aggregation
    raise ValueError(f"unknown metric {metric!r}")


def build_day_hour_matrix(
    rows: Sequence[MergeRow],
    tz: ZoneInfo,
    metric: str,
) -> tuple[list[date], list[list[float]]]:
    """Return (sorted active days, matrix[day_index][hour] )."""
    events = local_event_times(rows, tz)
    if not events:
        return [], []

    days = sorted({dt.date() for _, dt in events})
    day_index = {d: i for i, d in enumerate(days)}
    matrix = [[0.0] * 24 for _ in days]

    for row, dt in events:
        d, h = hour_day_keys(dt)
        matrix[day_index[d]][h] += row_contribution(row, metric)

    if metric == "reels_per_minute":
        for i in range(len(days)):
            matrix[i] = [c / 60.0 for c in matrix[i]]

    return days, matrix


def mean_circadian_profile(matrix: list[list[float]]) -> list[float]:
    if not matrix:
        return [0.0] * 24
    n = len(matrix)
    return [sum(matrix[d][h] for d in range(n)) / n for h in range(24)]


def hour_dispersion(matrix: list[list[float]], kind: str) -> list[float]:
    """Per-hour SD or SEM across active days (sample SD, n-1)."""
    if kind == "none":
        return [0.0] * 24
    if kind not in ("sd", "sem"):
        raise ValueError(f"unknown error kind {kind!r}")
    if not matrix:
        return [0.0] * 24
    n = len(matrix)
    if n < 2:
        return [0.0] * 24
    out: list[float] = []
    for h in range(24):
        vals = [matrix[d][h] for d in range(n)]
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / (n - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        out.append(sd if kind == "sd" else sd / math.sqrt(n))
    return out


def circular_kde_density(
    hours: Sequence[float],
    *,
    bandwidth_h: float,
    grid: Sequence[float],
    weights: Sequence[float] | None = None,
) -> list[float]:
    """Wrap-around KDE: pad by ±24h, densify, fold back to [0, 24)."""
    xs = list(hours)
    if not xs:
        return [0.0] * len(grid)
    ws = list(weights) if weights is not None else None
    padded: list[float] = []
    padded_w: list[float] = []
    for i, h in enumerate(xs):
        w = ws[i] if ws is not None else 1.0
        for shift in (-24.0, 0.0, 24.0):
            padded.append(h + shift)
            padded_w.append(w)
    # Evaluate on extended grid then fold — evaluate only in [0,24) with padded samples
    density = gaussian_kde_1d(padded, grid, bandwidth=bandwidth_h, weights=padded_w)
    # With 3 copies, mass is triple-counted relative to one period; renormalize on [0,24)
    # Approximate integral via trapezoid
    if len(grid) >= 2:
        acc = 0.0
        for i in range(len(grid) - 1):
            acc += 0.5 * (density[i] + density[i + 1]) * (grid[i + 1] - grid[i])
        if acc > 0:
            density = [d / acc for d in density]
    return density


def circular_moving_mean(profile: Sequence[float], *, window: int) -> list[float]:
    n = len(profile)
    if n == 0:
        return []
    w = int(window)
    if w < 1:
        raise ValueError("window must be >= 1")
    if w % 2 == 0:
        w += 1  # prefer odd
    half = w // 2
    out: list[float] = []
    for i in range(n):
        acc = 0.0
        for k in range(-half, half + 1):
            acc += profile[(i + k) % n]
        out.append(acc / w)
    return out


def smooth_overlay(
    rows: Sequence[MergeRow],
    tz: ZoneInfo,
    profile: Sequence[float],
    *,
    metric: str,
    mode: str,
    bandwidth_h: float | None,
    window: int,
    grid_n: int = 192,
) -> tuple[list[float], list[float]] | None:
    """Return (x_grid, y_scaled) or None."""
    if mode == "none":
        return None

    if mode == "moving":
        y = circular_moving_mean(profile, window=window)
        # place at hour centers for a polyline through bars
        x = [h + 0.5 for h in range(24)]
        # close wrap visually: append first point at 24.5
        return x + [24.5], list(y) + [y[0]]

    if mode == "kde":
        events = local_event_times(rows, tz)
        hours = [fractional_hours(dt) for _, dt in events]
        if metric == "watch_time_s":
            weights = [max((r.dwell_ms or 0.0) / 1000.0, 0.0) for r, _ in events]
        else:
            weights = None
        if not hours:
            return None
        bw = bandwidth_h if bandwidth_h is not None and bandwidth_h > 0 else silverman_bandwidth(hours)
        # Circular data: keep bandwidth reasonable
        bw = min(max(bw, 0.25), 4.0)
        grid = [i * 24.0 / grid_n for i in range(grid_n + 1)]  # 0..24 inclusive
        density = circular_kde_density(hours, bandwidth_h=bw, grid=grid, weights=weights)
        # Sample density at hour midpoints to scale against profile
        mid_x = [h + 0.5 for h in range(24)]
        mid_y = []
        for mx in mid_x:
            # nearest grid
            j = min(int(round(mx / 24.0 * grid_n)), grid_n)
            mid_y.append(density[j])
        scaled_mids = scale_curve_to_profile(mid_y, profile)
        if sum(mid_y) > 0:
            factor = (sum(scaled_mids) / len(scaled_mids)) / (sum(mid_y) / len(mid_y))
        else:
            factor = 1.0
        y = [d * factor for d in density]
        return grid, y

    raise ValueError(f"unknown smooth mode {mode!r}")


def print_stats(days: list[date], profile: list[float], *, metric: str, tz_name: str) -> None:
    print("[circadian] stage : L3 average-day 24h profile")
    print(f"[circadian] days  : {len(days)} active ({tz_name})")
    if days:
        print(f"[circadian] range : {days[0]} … {days[-1]}")
    print(f"[circadian] metric: {metric}")
    print(
        f"[circadian] peak  : hour={profile.index(max(profile)):02d}:00 "
        f"value={max(profile):.3g}"
        if profile and max(profile) > 0
        else "[circadian] peak  : (empty)"
    )


def plot_circadian_bars(
    profile: Sequence[float],
    *,
    errors: Sequence[float] | None,
    error_kind: str,
    smooth_xy: tuple[list[float], list[float]] | None,
    metric: str,
    tz_name: str,
    n_days: int,
    title: str,
    dpi: int,
    output: Path | None,
    show: bool,
) -> None:
    plt = require_matplotlib()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    apply_sleek_style(ax, grid_axis="y")

    hours = list(range(24))
    bar_width = 0.85
    y = list(profile)
    ax.bar(
        hours,
        y,
        width=bar_width,
        color=COLOR_BAR,
        alpha=0.88,
        edgecolor="white",
        linewidth=0.4,
        align="edge",
        zorder=2,
        label=METRIC_LABELS.get(metric, metric),
    )

    if errors is not None and error_kind != "none" and any(e > 0 for e in errors):
        # Center whiskers on each bar (align=edge → midpoint at hour + width/2)
        x_err = [h + bar_width / 2 for h in hours]
        err_label = "SD" if error_kind == "sd" else "SEM"
        ax.errorbar(
            x_err,
            y,
            yerr=list(errors),
            fmt="none",
            ecolor="#5C6B7A",
            elinewidth=1.1,
            capsize=2.5,
            capthick=1.0,
            alpha=0.85,
            zorder=4,
            label=err_label,
        )

    if smooth_xy is not None:
        sx, sy = smooth_xy
        ax.plot(sx, sy, color=COLOR_SMOOTH, linewidth=2.4, alpha=0.92, label="smooth", zorder=3)

    ax.set_xlim(0, 24)
    ymax = max(y) if y else 0.0
    if errors is not None:
        ymax = max(ymax, max((yi + ei for yi, ei in zip(y, errors)), default=0.0))
    ax.set_ylim(0, ymax * 1.12 if ymax > 0 else 1.0)
    ax.set_xticks([0, 3, 6, 9, 12, 15, 18, 21, 24])
    ax.set_xticklabels(["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "24:00"])
    ax.set_xlabel(f"local hour of day ({tz_name})", fontsize=10)
    ax.set_ylabel(METRIC_LABELS.get(metric, metric), fontsize=10)
    err_note = f", {error_kind.upper()}" if error_kind in ("sd", "sem") else ""
    default_title = (
        f"Average day — {metric} ({n_days} day{'s' if n_days != 1 else ''}, {tz_name}{err_note})"
    )
    ax.set_title(title or default_title, fontsize=13, color=COLOR_TEXT, pad=10)
    ax.legend(frameon=False, fontsize=9, loc="upper right")

    save_or_show(fig, output, show=show, dpi=dpi)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("merged_csv", type=Path, help="L3 merged.csv from merge_sources.py")
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--no-show", action="store_true")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--tz", default=DEFAULT_TZ, help=f"IANA timezone (default {DEFAULT_TZ})")
    ap.add_argument(
        "--metric",
        choices=METRICS,
        default="count",
        help="Y-axis metric (default count)",
    )
    ap.add_argument(
        "--statuses",
        default="",
        help="Comma-separated match_status values (default: matched,ambiguous,logger_only)",
    )
    ap.add_argument(
        "--smooth",
        choices=("none", "kde", "moving"),
        default="none",
        help="Wrap-around smooth overlay (default none)",
    )
    ap.add_argument(
        "--smooth-bw",
        type=float,
        default=None,
        help="KDE bandwidth in hours (default: Silverman rule, clamped)",
    )
    ap.add_argument(
        "--smooth-window",
        type=int,
        default=3,
        help="Circular moving-average window in hours (odd; default 3)",
    )
    ap.add_argument(
        "--error",
        choices=("none", "sd", "sem"),
        default="none",
        help="Per-hour error bars across active days: sd or sem (default none)",
    )
    ap.add_argument("--title", default="", help="Override plot title")
    args = ap.parse_args()

    if not args.merged_csv.exists():
        print(f"[circadian] ERROR missing {args.merged_csv}", file=sys.stderr)
        return 1

    try:
        tz = resolve_tz(args.tz)
    except ValueError as exc:
        print(f"[circadian] ERROR {exc}", file=sys.stderr)
        return 1

    statuses = parse_statuses(args.statuses, default=LOGGER_DWELL_STATUSES)
    require_dwell = args.metric == "watch_time_s"
    rows = filter_rows(
        load_merged_rows(args.merged_csv),
        statuses=statuses,
        require_dwell=require_dwell,
        require_shown_at=True,
    )

    days, matrix = build_day_hour_matrix(rows, tz, args.metric)
    profile = mean_circadian_profile(matrix)
    errors = hour_dispersion(matrix, args.error) if args.error != "none" else None
    print_stats(days, profile, metric=args.metric, tz_name=args.tz)
    print(f"[circadian] input : {args.merged_csv.resolve()}")
    print(f"[circadian] smooth: {args.smooth}")
    print(f"[circadian] error : {args.error}")
    if args.error != "none" and len(days) < 2:
        print("[circadian] note  : need ≥2 active days for SD/SEM; error bars will be zero")

    smooth_xy = smooth_overlay(
        rows,
        tz,
        profile,
        metric=args.metric,
        mode=args.smooth,
        bandwidth_h=args.smooth_bw,
        window=args.smooth_window,
    )

    out = args.output
    if out is None and args.no_show:
        out = args.merged_csv.with_name(f"circadian_{args.metric}.png")

    plot_circadian_bars(
        profile,
        errors=errors,
        error_kind=args.error,
        smooth_xy=smooth_xy,
        metric=args.metric,
        tz_name=args.tz,
        n_days=len(days),
        title=args.title,
        dpi=args.dpi,
        output=out,
        show=not args.no_show,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
