"""Shared helpers for L3 analysis plots (pastel style, CSV I/O, timezone)."""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

# Vibrant pastel palette (new plots only)
STATUS_COLORS = {
    "matched": "#7DCFB6",
    "ambiguous": "#FFB7A5",
    "logger_only": "#A8C5F0",
    "dyi_only": "#CDB4DB",
}

STATUS_ORDER = ("matched", "ambiguous", "logger_only", "dyi_only")
LOGGER_DWELL_STATUSES = frozenset({"matched", "ambiguous", "logger_only"})

COLOR_BAR = "#89C2D9"
COLOR_SMOOTH = "#F07167"
COLOR_FACE = "#FAFBFC"
COLOR_SPINE = "#8B95A1"
COLOR_TEXT = "#2F3A44"
COLOR_GRID = "#E6E9F0"

DEFAULT_TZ = "Europe/Copenhagen"
DEFAULT_DPI = 160


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


def _optional_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_merged_rows(path: Path) -> list[MergeRow]:
    rows: list[MergeRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                MergeRow(
                    match_status=r.get("match_status") or "",
                    match_method=r.get("match_method") or "",
                    match_dt_s=_optional_float(r.get("match_dt_s")),
                    shown_at=parse_ts(r.get("shown_at") or ""),
                    watched_at=parse_ts(r.get("watched_at") or ""),
                    dwell_ms=_optional_float(r.get("dwell_ms")),
                    creator_handle=r.get("creator_handle") or "",
                    external_url=r.get("external_url") or "",
                    identity_method=r.get("identity_method") or "",
                )
            )
    return rows


def parse_statuses(spec: str | None, *, default: frozenset[str] = LOGGER_DWELL_STATUSES) -> frozenset[str]:
    if not spec or not spec.strip():
        return frozenset(default)
    parts = {p.strip() for p in spec.split(",") if p.strip()}
    return frozenset(parts) if parts else frozenset(default)


def filter_rows(
    rows: Sequence[MergeRow],
    *,
    statuses: Iterable[str] | None = None,
    require_dwell: bool = False,
    require_shown_at: bool = False,
) -> list[MergeRow]:
    allowed = frozenset(statuses) if statuses is not None else None
    out: list[MergeRow] = []
    for r in rows:
        if allowed is not None and r.match_status not in allowed:
            continue
        if require_dwell and (r.dwell_ms is None or r.dwell_ms < 0):
            continue
        if require_shown_at and r.shown_at is None:
            continue
        out.append(r)
    return out


def resolve_tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as exc:  # noqa: BLE001 — surface as CLI error
        raise ValueError(f"Unknown timezone {name!r}") from exc


def status_order(present: Iterable[str]) -> list[str]:
    seen = set(present)
    ordered = [s for s in STATUS_ORDER if s in seen]
    extras = sorted(seen - set(STATUS_ORDER))
    return ordered + extras


def apply_sleek_style(ax, *, grid_axis: str = "y") -> None:
    """Light pastel chart chrome: no top/right spines, soft grid, charcoal labels."""
    fig = ax.figure
    fig.patch.set_facecolor(COLOR_FACE)
    ax.set_facecolor(COLOR_FACE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(COLOR_SPINE)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=COLOR_TEXT, labelsize=9)
    ax.xaxis.label.set_color(COLOR_TEXT)
    ax.yaxis.label.set_color(COLOR_TEXT)
    ax.title.set_color(COLOR_TEXT)
    ax.grid(True, axis=grid_axis, color=COLOR_GRID, linewidth=0.8, alpha=0.9, zorder=0)
    ax.set_axisbelow(True)


def save_or_show(
    fig,
    output: Path | None,
    *,
    show: bool,
    dpi: int = DEFAULT_DPI,
) -> None:
    import matplotlib.pyplot as plt

    fig.tight_layout()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches="tight")
        print(f"[viz] wrote : {output}")
    if show:
        plt.show()
    else:
        plt.close(fig)


def require_matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Run: pip install -e \".[viz]\"", file=sys.stderr)
        raise
    return plt


def gaussian_kde_1d(
    samples: Sequence[float],
    grid: Sequence[float],
    *,
    bandwidth: float,
    weights: Sequence[float] | None = None,
) -> list[float]:
    """Weighted 1D Gaussian KDE (density integrates roughly to 1 on infinite line)."""
    xs = list(samples)
    if not xs:
        return [0.0] * len(grid)
    if bandwidth <= 0:
        raise ValueError("bandwidth must be positive")
    if weights is None:
        ws = [1.0] * len(xs)
    else:
        if len(weights) != len(xs):
            raise ValueError("weights length must match samples")
        ws = [max(float(w), 0.0) for w in weights]
    w_sum = sum(ws) or 1.0
    inv = 1.0 / (bandwidth * math.sqrt(2.0 * math.pi))
    out: list[float] = []
    for g in grid:
        acc = 0.0
        for x, w in zip(xs, ws):
            u = (g - x) / bandwidth
            acc += w * math.exp(-0.5 * u * u)
        out.append(inv * acc / w_sum)
    return out


def silverman_bandwidth(samples: Sequence[float]) -> float:
    """Silverman rule-of-thumb; falls back to a small positive default."""
    xs = list(samples)
    n = len(xs)
    if n < 2:
        return 1.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    xs_sorted = sorted(xs)
    mid = n // 2
    if n % 2:
        median = xs_sorted[mid]
    else:
        median = 0.5 * (xs_sorted[mid - 1] + xs_sorted[mid])
    abs_dev = sorted(abs(x - median) for x in xs)
    if n % 2:
        mad = abs_dev[mid]
    else:
        mad = 0.5 * (abs_dev[mid - 1] + abs_dev[mid])
    sigma = min(std, mad / 0.6745) if mad > 0 else std
    if sigma <= 0:
        return max(0.5, (max(xs) - min(xs)) / 10.0 or 0.5)
    return 1.06 * sigma * (n ** (-0.2))


def scale_curve_to_profile(curve: Sequence[float], profile: Sequence[float]) -> list[float]:
    """Rescale curve so mean(curve) matches mean(profile) (same visual y-units)."""
    if not curve:
        return []
    p_mean = sum(profile) / len(profile) if profile else 0.0
    c_mean = sum(curve) / len(curve)
    if c_mean <= 0:
        return [0.0] * len(curve)
    factor = p_mean / c_mean if p_mean > 0 else 1.0
    return [y * factor for y in curve]
