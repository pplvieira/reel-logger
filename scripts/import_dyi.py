"""Import Instagram DYI JSON files into the API (videos_watched / liked / saved)."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


def post(base_url: str, path: str, body: dict, token: str) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_user(base_url: str, token: str) -> str:
    req = urllib.request.Request(base_url.rstrip("/") + "/devices/users/me")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["id"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--export-root",
        required=True,
        help="Unzipped Instagram export root (not committed to git)",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", default="")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    root = Path(args.export_root)
    user_id = args.user_id or get_user(args.base_url, args.token)

    videos = root / "ads_information" / "ads_and_topics" / "videos_watched.json"
    liked = root / "your_instagram_activity" / "likes" / "liked_posts.json"
    saved = root / "your_instagram_activity" / "saved" / "saved_posts.json"

    if videos.exists():
        doc = json.loads(videos.read_text(encoding="utf-8"))
        result = post(
            args.base_url,
            "/imports/dyi/videos-watched",
            {"user_id": user_id, "platform": "instagram", "document": doc},
            args.token,
        )
        print("videos_watched:", result)
    else:
        print("missing", videos)

    if liked.exists():
        doc = json.loads(liked.read_text(encoding="utf-8"))
        result = post(
            args.base_url,
            "/imports/dyi/liked-posts",
            {"user_id": user_id, "platform": "instagram", "document": doc},
            args.token,
        )
        print("liked_posts:", result)

    if saved.exists():
        doc = json.loads(saved.read_text(encoding="utf-8"))
        result = post(
            args.base_url,
            "/imports/dyi/saved-posts",
            {"user_id": user_id, "platform": "instagram", "document": doc},
            args.token,
        )
        print("saved_posts:", result)


if __name__ == "__main__":
    main()
