"""Register a local Android device against the seeded user. Prints IDs for the phone UI."""

from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--label", default="android-personal")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    def get(path: str):
        req = urllib.request.Request(args.base_url.rstrip("/") + path)
        if args.token:
            req.add_header("Authorization", f"Bearer {args.token}")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def post(path: str, body: dict):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            args.base_url.rstrip("/") + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if args.token:
            req.add_header("Authorization", f"Bearer {args.token}")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    user = get("/devices/users/me")
    device = post(
        "/devices",
        {
            "user_id": user["id"],
            "platform_os": "android",
            "label": args.label,
            "logger_version": "0.1.1-android",
        },
    )
    print(json.dumps({"user_id": user["id"], "device_id": device["id"]}, indent=2))
    print("\nEnter these values in the Scroll logger app sync config.")


if __name__ == "__main__":
    main()
