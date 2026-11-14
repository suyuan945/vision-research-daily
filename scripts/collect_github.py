"""Collect and archive public GitHub research updates with their source dates."""

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request

if __package__:
    from .generate import request_data
else:
    from generate import request_data

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "github.json"
ASIA_SHANGHAI = timezone(timedelta(hours=8))
ARXIV_ID = re.compile(r"https?://arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?!\d)")
WEIGHT_FILE = re.compile(r"\.(?:safetensors|ckpt|pth|pt|onnx|gguf)(?:\.zip)?$", re.I)


def github(path, *, raw=False):
    headers = {"User-Agent": "VisionResearchDaily/3.0",
               "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = request_data(Request("https://api.github.com" + path, headers=headers), timeout=15)
    return data.decode("utf-8", errors="replace") if raw else json.loads(data)


def within_window(value, since, now):
    if not value:
        return False
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return since <= timestamp <= now


def repository_record(repo, topics, previous, seen):
    license_data = repo.get("license") or {}
    full_name = repo["full_name"]
    return {
        "id": str(repo["id"]),
        "name": full_name,
        "url": "https://github.com/" + full_name,
        "description": (repo.get("description") or "")[:400],
        "created_at": repo["created_at"],
        "first_seen": previous.get("first_seen", seen),
        "license": license_data.get("spdx_id") or "",
        "license_name": license_data.get("name") or "",
        "topics": sorted(set(previous.get("topics", [])) | set(topics)),
        "paper_ids": previous.get("paper_ids", []),
    }


def release_events(repo, releases, since, now, seen):
    for release in releases:
        published = release.get("published_at")
        if release.get("draft") or not within_window(published, since, now):
            continue
        assets = [asset["name"] for asset in release.get("assets", [])]
        yield {
            "id": f"release:{release['id']}",
            "repository_id": repo["id"],
            "kind": "release",
            "date": published,
            "first_seen": seen,
            "title": release.get("name") or release["tag_name"],
            "version": release["tag_name"],
            "prerelease": bool(release.get("prerelease")),
            "weights": [name for name in assets if WEIGHT_FILE.search(name)][:10],
            "url": repo["url"] + "/releases/tag/" + quote(release["tag_name"], safe=""),
        }


def collect(config, previous, now, days):
    since = now - timedelta(days=days)
    seen = now.date().isoformat()
    previous_repos = {repo["id"]: repo for repo in previous.get("repositories", [])}
    repositories = dict(previous_repos)
    events = {event["id"]: event for event in previous.get("events", [])}
    matches = defaultdict(set)
    candidates = {}
    errors = []

    def fetch(path, label, *, raw=False, missing_ok=False):
        try:
            return github(path, raw=raw)
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            if missing_ok and isinstance(error, HTTPError) and error.code == 404:
                return None
            errors.append(label)
            detail = f"HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__
            print(f"GitHub request failed ({label}): {detail}")
            return None

    def add(repo, topic):
        if repo.get("private") or repo.get("archived") or repo.get("fork") or not repo.get("size"):
            return False
        if "source is private" in (repo.get("description") or "").lower():
            return False
        repo_id = str(repo["id"])
        candidates[repo_id] = repo
        matches[repo_id].add(topic)
        return True

    for topic, query in config["topics"].items():
        search = urlencode({
            "q": f"{query} in:name,description fork:false archived:false is:public created:>={since.date()}",
            "order": "desc",
            "per_page": 15,
        })
        result = fetch("/search/repositories?" + search, topic)
        if result is None:
            continue
        if result.get("incomplete_results"):
            errors.append(topic)
        items = [repo for repo in result["items"] if within_window(repo["created_at"], since, now)]
        accepted = 0
        for repo in items:
            if not (repo.get("description") or "").strip():
                continue
            if accepted == 4:
                break
            add(repo, topic)
            accepted += 1

    watched_ids = set()
    for name, topic in config["watch"].items():
        repo = fetch("/repos/" + name, name)
        if repo and add(repo, topic):
            watched_ids.add(str(repo["id"]))

    for repo_id, repo in candidates.items():
        old = previous_repos.get(repo_id, {})
        record = repository_record(repo, matches[repo_id], old, seen)
        fresh = within_window(record["created_at"], since, now)
        if not old.get("paper_ids"):
            readme = fetch(f"/repos/{record['name']}/readme", record["name"] + " README", raw=True, missing_ok=True)
            if readme:
                record["paper_ids"] = sorted(set(ARXIV_ID.findall(readme)))[:25]
        repositories[repo_id] = record
        if not old:
            event_id = f"repo:{repo_id}"
            events[event_id] = {
                "id": event_id,
                "repository_id": repo_id,
                "kind": "new" if fresh else "discovered",
                "date": record["created_at"] if fresh else now.isoformat(timespec="seconds"),
                "first_seen": seen,
                "title": record["name"],
                "url": record["url"],
            }
        if repo_id in watched_ids or fresh or not old:
            releases = fetch(f"/repos/{record['name']}/releases?per_page=15", record["name"] + " Releases")
            for event in release_events(record, releases or [], since, now, seen):
                if event["id"] in events:
                    event["first_seen"] = events[event["id"]]["first_seen"]
                events[event["id"]] = event

    status = ("partial" if candidates else "failed") if errors else "ok"
    print(f"GitHub {status}: {len(candidates)} repositories checked; {len(events)} archived events")
    return {
        "status": status,
        "checked_at": now.isoformat(timespec="seconds"),
        "failed_sources": sorted(set(errors)),
        "repositories": sorted(repositories.values(), key=lambda item: item["name"].lower()),
        "events": sorted(events.values(), key=lambda item: item["date"], reverse=True),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, choices=range(1, 31), metavar="1–30")
    parser.add_argument("--output", type=Path, default=INDEX, help="Write to a separate index for a test run")
    args = parser.parse_args()
    config = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))["github"]
    previous = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else {}
    archive = collect(config, previous, datetime.now(ASIA_SHANGHAI), args.days)
    temp = args.output.with_suffix(".tmp")
    temp.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.output)
    if archive["failed_sources"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
