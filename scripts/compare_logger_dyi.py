#!/usr/bin/env python3
"""One-shot alias: L2 preprocess then L3 merge (does not modify L0 files).

Prefer the staged commands for clarity:
  python scripts/preprocess_queue.py …
  python scripts/merge_sources.py …

This wrapper remains for backwards compatibility with earlier docs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.derived.merge import run_merge  # noqa: E402
from app.services.derived.preprocess import run_preprocess  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--export-root", type=Path, required=True)
    ap.add_argument("--clean", action="store_true", help="Ignored; preprocess always derives")
    ap.add_argument("--min-dwell-ms", type=float, default=2000.0)
    ap.add_argument("--window-seconds", type=int, default=180)
    ap.add_argument("-o", "--output", type=Path, default=None, help="Optional merged.csv path")
    ap.add_argument("--since", default="")
    args = ap.parse_args()

    print("[compare_logger_dyi] deprecated alias → running preprocess then merge")
    print("[compare_logger_dyi] prefer: preprocess_queue.py then merge_sources.py")

    pre = run_preprocess(
        args.jsonl,
        out_root=ROOT / "data" / "derived",
        min_dwell_ms=args.min_dwell_ms,
        since=args.since or None,
    )
    print(f"[preprocess] era={pre.schema_era} kept={pre.counts.get('impressions_kept')} → {pre.impressions_path}")

    out = args.output or (pre.out_dir / "merged.csv")
    merged, counts = run_merge(
        pre.impressions_path,
        args.export_root,
        window_seconds=args.window_seconds,
        out_path=out,
    )
    print(
        f"[merge] matched={counts.get('matched', 0)} "
        f"ambiguous={counts.get('ambiguous', 0)} "
        f"logger_only={counts.get('logger_only', 0)} "
        f"dyi_only={counts.get('dyi_only', 0)}"
    )
    print(f"[merge] wrote {merged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
