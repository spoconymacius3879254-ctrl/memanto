# Git-versioned OKF memory wiki

This Path C showcase turns real public Git history into a Memanto agent, exports
the agent through Memanto's shipped OKF tooling, and syncs that export into a
reviewable memory wiki. It then imports the same bundle into a clean agent and
proves that the knowledge survived the complete freedom loop:

```text
real Git commits -> memanto remember -> Memanto -> OKF
                                               -> Git wiki/diff
                                               -> clean Memanto agent -> OKF
```

No private conversation archive is needed. The source facts are extracted from
an actual repository with `git log`; every memory links back to its exact public
commit.

## Why this is useful

Memory portability is more than downloading a file. A useful open format lets a
team review what an agent learned, see semantic changes between sessions, and
verify that moving to a clean agent did not cause amnesia.

`okf_history.py` builds on `memanto memory export --okf` and
`memanto migrate okf`. It adds three workflow operations:

- `snapshot`: atomically sync a validated export into `wiki/okf` and write a
  content-addressed manifest.
- `diff`: compare memories by stable semantic identity and report added,
  removed, and changed knowledge. Generated timestamps, filenames, storage IDs,
  indexes, and native Memanto transport footers do not create false changes.
- `validate`: fail with a non-zero exit code if a clean OKF round trip loses or
  mutates knowledge.

Foreign OKF supporting data remains meaningful. Transport-footer normalization
is applied only when a document contains Memanto's namespaced `x_memanto`
metadata.

## Reproduce in under 15 minutes

Requirements:

- Python 3.10+
- Git
- Memanto installed from this repository
- `MOORCHEH_API_KEY` configured (or `MEMANTO_API_KEY`; the demo maps it without
  printing it)
- enough free capacity for two small demo agents

Use a short, never-before-used agent prefix because the live demo creates two
agents:

```bash
cd examples/migrations/git-versioned-okf
./run_demo.sh /path/to/a/public/git/repository my-okf-demo
```

The command:

1. extracts up to 20 real commits into Memanto batch-memory JSON;
2. creates and populates `my-okf-demo-source`;
3. runs `memanto memory export --okf --split file`;
4. snapshots the export into `demo-output/wiki/okf`;
5. creates the clean `my-okf-demo-roundtrip` agent;
6. runs `memanto migrate okf` and exports that agent; and
7. writes `demo-output/roundtrip-report.json`.

A passing report has `passed: true` and identical before/after record counts.
The included public run contains 8 source records, 8 mapped memories, 8 imported
memories, and 8 unchanged records after re-export.

## Review changes between sessions

After another `memanto memory export --okf`, compare the checked-in snapshot
with the new bundle:

```bash
python okf_history.py diff \
  demo-output/wiki/okf \
  ~/.memanto/exports/my-okf-demo-source_okf \
  --output demo-output/session-diff.json
```

Review `session-diff.json`, then update the wiki:

```bash
python okf_history.py snapshot \
  --bundle ~/.memanto/exports/my-okf-demo-source_okf \
  --wiki demo-output/wiki \
  --label "session 2"
git -C demo-output/wiki diff -- okf
```

The JSON semantic diff is suitable for CI policy checks; the Markdown diff is
human-readable in an ordinary pull request.

## Source-to-memory mapping

| Git source field | Memanto / OKF field | Reason |
| --- | --- | --- |
| commit subject | `title` | concise review label |
| hash, author, date, subject, body | memory `content` / OKF body | complete public event |
| commit hash | `tags` | searchable stable reference |
| origin URL + full hash | `source_ref` / OKF `resource` | auditable provenance |
| author timestamp | `created_at` / OKF `timestamp` | preserves chronology |
| generated record | `event` | a commit is an observed project event |
| Git | `source` | makes provenance explicit |

The extractor caps titles at Memanto's 100-character schema limit and rejects
invalid batch sizes. It invokes Git with an argument array, not a shell command.

## Included evidence

- `sample/git-memories.json`: generated from 8 real public commits in this
  repository.
- `sample/okf-export/`: the human-inspectable output of a live
  `memanto memory export --okf --split file`.
- `sample/roundtrip-report.json`: passing semantic parity evidence after
  importing the sample into a clean live agent and exporting it again.
- `MIGRATION_REPORT.md`: commands, counts, timing, limitations, and an honest
  savings assessment.
- `RECALL_REPORT.md`: the same live recall question returning the same commit as
  rank #1 from both the source and clean round-trip agents.

Run the local checks:

```bash
pytest -q examples/migrations/git-versioned-okf/tests
ruff check examples/migrations/git-versioned-okf
```

## Tradeoffs and safety

- Semantic identity uses type, title, and resource. Duplicate identities are
  rejected rather than silently paired.
- IDs and timestamps are not knowledge, so they are excluded from content
  hashes. Actual body and metadata changes remain visible.
- The snapshot operation replaces only the exact `wiki/okf` directory and keeps
  the previous copy until the new validated bundle is in place.
- The deterministic validator proves structural and content parity, not
  equivalent LLM phrasing. A live recall demo can supplement it in the video.
- Git commit metadata is often public but can contain personal names or email
  addresses. Review the generated JSON before sending a private repository to a
  hosted service.
- The demo creates two remote agent namespaces and does not delete them.

## Video walkthrough

For a truthful recording, show:

1. `git log` and the generated real-data JSON;
2. the single-command live run;
3. Memanto's `8 -> 8` import summary;
4. the readable Markdown export and a Git diff;
5. `roundtrip-report.json` with `passed: true`; and
6. the same recall question against source and round-trip agents.

The video and social-post URLs belong in the pull-request description; they
cannot be generated by this repository.
