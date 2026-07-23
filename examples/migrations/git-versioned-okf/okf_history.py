#!/usr/bin/env python3
"""Turn Memanto OKF exports into reviewable, versioned memory snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ENTRY_DELIMITER = "<!-- okf-entry -->"
SKIP_FILES = {"index.md", "log.md"}
KNOWN_FIELDS = {
    "type",
    "title",
    "description",
    "resource",
    "tags",
    "timestamp",
    "x_memanto",
}
SUPPORTING_DATA_MARKER = "\n\n---\n[Supporting data]\n"


@dataclass(frozen=True)
class OkfRecord:
    """A normalized OKF document suitable for stable comparison."""

    key: str
    source_path: str
    title: str
    memory_type: str
    resource: str
    body: str
    metadata: dict[str, Any]

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            {"body": self.body, "metadata": self.metadata},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def _parse_document(text: str, source_path: str) -> OkfRecord | None:
    text = text.strip()
    frontmatter: dict[str, Any] = {}
    body = text
    if text.startswith("---\n"):
        closing = text.find("\n---", 4)
        if closing >= 0:
            raw_frontmatter = text[4:closing]
            parsed = yaml.safe_load(raw_frontmatter) or {}
            if isinstance(parsed, dict):
                frontmatter = parsed
            body = text[closing + 4 :].strip()

    memory_type = str(frontmatter.get("type") or "").strip()
    if memory_type.lower() == "index":
        return None
    title = str(frontmatter.get("title") or "").strip()
    if not body and not title:
        return None

    resource = str(frontmatter.get("resource") or "").strip()
    x_memanto = frontmatter.get("x_memanto")
    if not isinstance(x_memanto, dict):
        x_memanto = {}
    if x_memanto and SUPPORTING_DATA_MARKER in body:
        # Memanto's OKF importer appends a provenance footer on re-import.
        # It is derived transport metadata, not a user knowledge mutation.
        body = body.rsplit(SUPPORTING_DATA_MARKER, 1)[0].rstrip()

    # IDs are deliberately excluded: a valid OKF -> Memanto -> OKF round trip
    # can allocate new storage IDs while preserving the user's knowledge.
    normalized_x = {
        key: value
        for key, value in x_memanto.items()
        if key not in {"id"} and value not in (None, "")
    }
    metadata = {
        key: value
        for key, value in frontmatter.items()
        if key not in {"timestamp", "x_memanto"}
    }
    if normalized_x:
        metadata["x_memanto"] = normalized_x

    identity = "\0".join((memory_type.casefold(), title.casefold(), resource))
    if not identity.strip("\0"):
        identity = f"path:{source_path}"
    key = hashlib.sha256(identity.encode()).hexdigest()[:16]
    return OkfRecord(
        key=key,
        source_path=source_path,
        title=title or source_path,
        memory_type=memory_type or "unknown",
        resource=resource,
        body=body,
        metadata=metadata,
    )


def load_bundle(bundle: Path) -> dict[str, OkfRecord]:
    """Load an OKF bundle without depending on Memanto internals."""
    if not bundle.exists():
        raise FileNotFoundError(f"OKF bundle not found: {bundle}")
    if bundle.is_file():
        files = [bundle]
        root = bundle.parent
    else:
        memories = bundle / "memories"
        scan_root = memories if memories.is_dir() else bundle
        files = sorted(
            path
            for path in scan_root.rglob("*.md")
            if path.name.lower() not in SKIP_FILES
        )
        root = bundle

    records: dict[str, OkfRecord] = {}
    for path in files:
        source_path = str(path.relative_to(root))
        for chunk in path.read_text(encoding="utf-8").split(ENTRY_DELIMITER):
            record = _parse_document(chunk, source_path)
            if record is None:
                continue
            if record.key in records:
                other = records[record.key]
                raise ValueError(
                    "Ambiguous OKF identity for "
                    f"{other.source_path!r} and {record.source_path!r}: "
                    f"{record.memory_type}/{record.title}"
                )
            records[record.key] = record
    return records


def compare_bundles(before: Path, after: Path) -> dict[str, Any]:
    """Return a deterministic semantic diff between two OKF bundles."""
    old = load_bundle(before)
    new = load_bundle(after)
    old_keys, new_keys = set(old), set(new)

    def describe(record: OkfRecord) -> dict[str, Any]:
        return {
            "key": record.key,
            "type": record.memory_type,
            "title": record.title,
            "resource": record.resource or None,
            "source_path": record.source_path,
            "sha256": record.content_hash,
        }

    changed = []
    unchanged = 0
    for key in sorted(old_keys & new_keys):
        if old[key].content_hash == new[key].content_hash:
            unchanged += 1
            continue
        fields = []
        if old[key].body != new[key].body:
            fields.append("body")
        if old[key].metadata != new[key].metadata:
            fields.append("metadata")
        changed.append(
            {
                "key": key,
                "type": new[key].memory_type,
                "title": new[key].title,
                "fields": fields,
                "before_sha256": old[key].content_hash,
                "after_sha256": new[key].content_hash,
            }
        )

    return {
        "schema_version": 1,
        "before": str(before),
        "after": str(after),
        "counts": {
            "before": len(old),
            "after": len(new),
            "added": len(new_keys - old_keys),
            "removed": len(old_keys - new_keys),
            "changed": len(changed),
            "unchanged": unchanged,
        },
        "added": [describe(new[key]) for key in sorted(new_keys - old_keys)],
        "removed": [describe(old[key]) for key in sorted(old_keys - new_keys)],
        "changed": changed,
    }


def _bundle_manifest(bundle: Path, label: str) -> dict[str, Any]:
    records = load_bundle(bundle)
    return {
        "schema_version": 1,
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": [
            {
                "key": item.key,
                "type": item.memory_type,
                "title": item.title,
                "resource": item.resource or None,
                "source_path": item.source_path,
                "sha256": item.content_hash,
            }
            for item in sorted(records.values(), key=lambda item: item.key)
        ],
    }


def snapshot(bundle: Path, wiki: Path, label: str) -> dict[str, Any]:
    """Atomically replace ``wiki/okf`` with a validated export plus manifest."""
    manifest = _bundle_manifest(bundle, label)
    wiki.mkdir(parents=True, exist_ok=True)
    target = wiki / "okf"
    staging_root = Path(tempfile.mkdtemp(prefix=".okf-", dir=wiki))
    staging = staging_root / "okf"
    try:
        if bundle.is_dir():
            shutil.copytree(bundle, staging)
        else:
            staging.mkdir()
            shutil.copy2(bundle, staging / bundle.name)
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        backup = wiki / ".okf-previous"
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.rename(backup)
        staging.rename(target)
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
    return manifest


def validate_parity(before: Path, after: Path) -> dict[str, Any]:
    """Validate knowledge parity while tolerating IDs and transport footers."""
    diff = compare_bundles(before, after)
    counts = diff["counts"]
    passed = not any(counts[name] for name in ("added", "removed", "changed"))
    return {
        "schema_version": 1,
        "passed": passed,
        "before_records": counts["before"],
        "after_records": counts["after"],
        "unchanged_records": counts["unchanged"],
        "failures": {
            "added": diff["added"],
            "removed": diff["removed"],
            "changed": diff["changed"],
        },
    }


def _write_result(result: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Snapshot, diff, and validate Memanto OKF bundles."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snap = subparsers.add_parser("snapshot", help="Sync an export into a wiki.")
    snap.add_argument("--bundle", required=True, type=Path)
    snap.add_argument("--wiki", required=True, type=Path)
    snap.add_argument("--label", required=True)
    snap.add_argument("--output", type=Path)

    diff = subparsers.add_parser("diff", help="Create a semantic bundle diff.")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--output", type=Path)

    validate = subparsers.add_parser(
        "validate", help="Check lossless OKF round-trip parity."
    )
    validate.add_argument("before", type=Path)
    validate.add_argument("after", type=Path)
    validate.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "snapshot":
            result = snapshot(args.bundle, args.wiki, args.label)
        elif args.command == "diff":
            result = compare_bundles(args.before, args.after)
        else:
            result = validate_parity(args.before, args.after)
        _write_result(result, args.output)
        if args.command == "validate" and not result["passed"]:
            return 1
        return 0
    except (FileNotFoundError, OSError, ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
