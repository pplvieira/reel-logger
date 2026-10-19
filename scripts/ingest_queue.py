"""POST a pulled JSONL queue file to the FastAPI ingest endpoint."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--token", default="")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    lines = [
        json.loads(line)
        for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    def post_batch(events: list[dict]) -> dict:
        body = {
            "schema_version": "1",
            "device_id": args.device_id,
            "user_id": args.user_id,
            "platform": "instagram",
            "capture_method": "accessibility",
            "logger_version": "0.1.1-android",
            "events": [
                {
                    "type": e["type"],
                    "observed_at": e["observed_at"],
                    "payload": e.get("payload") or {},
                    **({"event_id": e["event_id"]} if e.get("event_id") else {}),
                }
                for e in events
            ],
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            args.base_url.rstrip("/") + "/ingest/events",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if args.token:
            req.add_header("Authorization", f"Bearer {args.token}")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    for i in range(0, len(lines), args.batch_size):
        chunk = lines[i : i + args.batch_size]
        result = post_batch(chunk)
        print(f"batch {i // args.batch_size + 1}: {result}")


if __name__ == "__main__":
    main()
