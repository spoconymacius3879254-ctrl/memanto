import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "okf_history.py"
SPEC = importlib.util.spec_from_file_location("okf_history", MODULE_PATH)
assert SPEC and SPEC.loader
okf_history = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = okf_history
SPEC.loader.exec_module(okf_history)


def write_bundle(root: Path, docs: list[tuple[str, str, str]]) -> Path:
    memories = root / "memories" / "fact"
    memories.mkdir(parents=True)
    for filename, title, body in docs:
        (memories / filename).write_text(
            "---\n"
            "type: fact\n"
            f"title: {title}\n"
            "timestamp: 2026-07-23T00:00:00Z\n"
            "x_memanto:\n"
            f"  id: id-{filename}\n"
            "  confidence: 0.9\n"
            "  type: fact\n"
            "---\n\n"
            f"{body}\n",
            encoding="utf-8",
        )
    (memories / "index.md").write_text(
        "---\ntype: index\ntitle: facts\n---\n", encoding="utf-8"
    )
    return root


def test_diff_ignores_ids_timestamps_and_paths(tmp_path):
    before = write_bundle(tmp_path / "before", [("old.md", "Database", "Postgres")])
    after = write_bundle(tmp_path / "after", [("new.md", "Database", "Postgres")])

    result = okf_history.compare_bundles(before, after)

    assert result["counts"] == {
        "before": 1,
        "after": 1,
        "added": 0,
        "removed": 0,
        "changed": 0,
        "unchanged": 1,
    }


def test_diff_reports_semantic_changes(tmp_path):
    before = write_bundle(
        tmp_path / "before",
        [("db.md", "Database", "Postgres"), ("old.md", "Removed", "old")],
    )
    after = write_bundle(
        tmp_path / "after",
        [("db.md", "Database", "SQLite"), ("new.md", "Added", "new")],
    )

    result = okf_history.compare_bundles(before, after)

    assert result["counts"]["added"] == 1
    assert result["counts"]["removed"] == 1
    assert result["counts"]["changed"] == 1
    assert result["changed"][0]["fields"] == ["body"]


def test_snapshot_copies_validated_bundle_and_manifest(tmp_path):
    bundle = write_bundle(tmp_path / "bundle", [("db.md", "Database", "Postgres")])
    wiki = tmp_path / "wiki"

    result = okf_history.snapshot(bundle, wiki, "session-1")

    assert result["record_count"] == 1
    assert (wiki / "okf" / "memories" / "fact" / "db.md").exists()
    assert (wiki / "okf" / "manifest.json").exists()


def test_duplicate_semantic_identity_is_rejected(tmp_path):
    bundle = write_bundle(
        tmp_path / "bundle",
        [("one.md", "Same title", "one"), ("two.md", "Same title", "two")],
    )

    with pytest.raises(ValueError, match="Ambiguous OKF identity"):
        okf_history.load_bundle(bundle)


def test_validate_parity_fails_on_loss(tmp_path):
    before = write_bundle(tmp_path / "before", [("db.md", "Database", "Postgres")])
    after = write_bundle(tmp_path / "after", [])

    result = okf_history.validate_parity(before, after)

    assert not result["passed"]
    assert result["failures"]["removed"]


def test_native_roundtrip_ignores_generated_supporting_footer(tmp_path):
    before = write_bundle(tmp_path / "before", [("db.md", "Database", "Postgres")])
    after = write_bundle(
        tmp_path / "after",
        [
            (
                "db.md",
                "Database",
                "Postgres\n\n---\n[Supporting data]\n"
                "- OKF source: memories/fact/db.md",
            )
        ],
    )

    assert okf_history.validate_parity(before, after)["passed"]


def test_foreign_supporting_data_remains_meaningful(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "fact.md").write_text(
        "---\ntype: fact\ntitle: Database\n---\n\nPostgres\n", encoding="utf-8"
    )
    (after / "fact.md").write_text(
        "---\ntype: fact\ntitle: Database\n---\n\n"
        "Postgres\n\n---\n[Supporting data]\n- owner: data-team\n",
        encoding="utf-8",
    )

    assert not okf_history.validate_parity(before, after)["passed"]
