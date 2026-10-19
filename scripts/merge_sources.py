#!/usr/bin/env python3
"""L3 merge: derived impressions CSV + Instagram DYI (no dwell from DYI).

Example:
  python scripts/merge_sources.py data/derived/<run_id>/impressions.csv \\
    --export-root C:\\Users\\…\\instagram-export
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.derived.merge import run_merge  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("impressions_csv", type=Path, help="L2 impressions.csv from preprocess")
    ap.add_argument("--export-root", type=Path, required=True)
    ap.add_argument("--window-seconds", type=int, default=180)
    ap.add_argument(
        "--include-dropped",
        action="store_true",
        help="Also merge rows with kept=false from preprocess",
    )
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args()

    if not args.impressions_csv.exists():
        print(f"[merge] ERROR missing {args.impressions_csv}", file=sys.stderr)
        return 1
    if not args.export_root.exists():
        print(f"[merge] ERROR missing {args.export_root}", file=sys.stderr)
        return 1

    print("[merge] stage : L3 link derived logger + DYI")
    print(f"[merge] logger : {args.impressions_csv.resolve()}")
    print(f"[merge] dyi    : {args.export_root.resolve()}")
    print(f"[merge] window : {args.window_seconds}s")
    print("[merge] note   : dwell never taken from DYI; L0 archives untouched")

    out, counts = run_merge(
        args.impressions_csv,
        args.export_root,
        window_seconds=args.window_seconds,
        kept_only=not args.include_dropped,
        out_path=args.output,
    )

    print(f"[merge] output : {out}")
    print(
        f"[merge] result : matched={counts.get('matched', 0)} "
        f"ambiguous={counts.get('ambiguous', 0)} "
        f"logger_only={counts.get('logger_only', 0)} "
        f"dyi_only={counts.get('dyi_only', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
