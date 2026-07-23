import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "extract_git_memories.py"
SPEC = importlib.util.spec_from_file_location("extract_git_memories", MODULE_PATH)
assert SPEC and SPEC.loader
extract_git_memories = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = extract_git_memories
SPEC.loader.exec_module(extract_git_memories)


def test_extract_uses_real_commits_and_respects_schema_limit(tmp_path):
    extract_git_memories.git = lambda _repo, *args: {
        ("rev-parse", "--show-toplevel"): str(tmp_path),
        ("remote", "get-url", "origin"): "https://example.com/project.git",
        (
            "log",
            "HEAD",
            "--max-count=1",
            "--format=%H%x1f%aI%x1f%an%x1f%s%x1f%b%x1e",
        ): (
            "abc123\x1f2026-07-23T00:00:00Z\x1fA Developer\x1f"
            f"{'long subject ' * 20}\x1f"
        ),
    }[args]

    rows = extract_git_memories.extract(tmp_path, 1, "HEAD")

    assert len(rows) == 1
    assert len(rows[0]["title"]) == 100
    assert rows[0]["source"] == "git"
    assert rows[0]["source_ref"].endswith("@abc123")
