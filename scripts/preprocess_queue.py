#!/usr/bin/env python3
"""L2 preprocess: phone JSONL → derived impressions (raw file untouched).

Example:
  python scripts/preprocess_queue.py data/phone-queue/events-….jsonl
  python scripts/preprocess_queue.py data/phone-queue/events-….jsonl --since 2026-10-15T09:20:00Z
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.derived.preprocess import run_preprocess  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jsonl", type=Path)
    ap.add_argument(
        "--out-root",
        type=Path,
        default=ROOT / "data" / "derived",
        help="Directory for run_id folders (default data/derived)",
    )
    ap.add_argument("--min-dwell-ms", type=float, default=2000.0)
    ap.add_argument(
        "--drop-no-identity",
        action="store_true",
        help="Mark rows without creator/caption as dropped",
    )
    ap.add_argument(
        "--keep-share-sheet",
        action="store_true",
        help="Do not drop impressions near share-sheet raw samples",
    )
    ap.add_argument(
        "--since",
        default="",
        help="Only events at/after ISO time (e.g. 2026-10-15T09:20:00Z)",
    )
    args = ap.parse_args()

    if not args.jsonl.exists():
        print(f"[preprocess] ERROR missing {args.jsonl}", file=sys.stderr)
        return 1

    print("[preprocess] stage : L2 derived impressions")
    print(f"[preprocess] input : {args.jsonl.resolve()}")
    print("[preprocess] note  : L0 JSONL will not be modified")

    result = run_preprocess(
        args.jsonl,
        out_root=args.out_root,
        min_dwell_ms=args.min_dwell_ms,
        drop_share_sheet=not args.keep_share_sheet,
        drop_no_identity=args.drop_no_identity,
        since=args.since or None,
    )

    print(f"[preprocess] era   : {result.schema_era}")
    print(f"[preprocess] run   : {result.run_id}")
    print(f"[preprocess] output: {result.impressions_path}")
    print(f"[preprocess] manifest: {result.manifest_path}")
    for k, v in result.counts.items():
        print(f"[preprocess] {k}: {v}")
    print(
        "[preprocess] next  : python scripts/merge_sources.py "
        f"{result.impressions_path} --export-root <DYI_ROOT>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
