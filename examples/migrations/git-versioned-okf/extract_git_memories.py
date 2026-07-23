#!/usr/bin/env python3
"""Extract real repository history into Memanto batch-memory JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.rstrip("\r\n")


def extract(repo: Path, limit: int, ref: str) -> list[dict[str, Any]]:
    if limit < 1 or limit > 100:
        raise ValueError("--limit must be between 1 and 100")
    root = Path(git(repo, "rev-parse", "--show-toplevel"))
    remote = git(root, "remote", "get-url", "origin")
    fields = "%H%x1f%aI%x1f%an%x1f%s%x1f%b%x1e"
    raw = git(root, "log", ref, f"--max-count={limit}", f"--format={fields}")

    memories = []
    for record in raw.split("\x1e"):
        record = record.strip("\r\n")
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) != 5:
            raise ValueError("Unexpected git log record")
        commit, authored_at, author, subject, body = (part.strip() for part in parts)
        details = [
            f"Commit {commit} in {remote}.",
            f"Authored by {author} at {authored_at}.",
            f"Change: {subject}",
        ]
        if body:
            details.append(f"Details: {body}")
        memories.append(
            {
                "content": "\n".join(details),
                # Memanto's MemoryRecord schema caps titles at 100 characters.
                "title": f"Git change: {subject}"[:100],
                "type": "event",
                "confidence": 1.0,
                "tags": ["git-history", "public-source", commit[:12]],
                "source": "git",
                "provenance": "imported",
                "source_ref": f"{remote}@{commit}",
                "created_at": authored_at,
            }
        )
    return memories


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        memories = extract(args.repo, args.limit, args.ref)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(memories, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {len(memories)} real Git memories to {args.output}")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
