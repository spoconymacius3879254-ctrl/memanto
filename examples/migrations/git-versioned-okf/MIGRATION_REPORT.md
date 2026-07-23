# Migration report: public Git history to owned OKF

Run date: 2026-07-23  
Source repository: `https://github.com/moorcheh-ai/memanto.git`  
Source agent: `memanto-okf-git-public-20260723`  
Clean target: `memanto-okf-roundtrip-20260723`

## Commands and observed results

The source dataset was generated—not hand-written—from the repository:

```bash
python extract_git_memories.py --repo ../../.. --limit 8 \
  --output sample/git-memories.json
memanto remember --batch sample/git-memories.json
memanto memory export \
  --agent memanto-okf-git-public-20260723 \
  --okf --split file --limit 100
```

Observed source write and export:

| Stage | Result |
| --- | ---: |
| real Git commits extracted | 8 |
| memories accepted by Memanto | 8 / 8 |
| OKF event documents exported | 8 |
| batch storage wall time | 4.01 s |
| OKF export wall time | 7.25 s |

The exported bundle was then imported into an empty live agent:

```bash
memanto migrate okf sample/okf-export \
  --agent memanto-okf-roundtrip-20260723
memanto memory export \
  --agent memanto-okf-roundtrip-20260723 \
  --okf --split file --limit 100
python okf_history.py validate \
  sample/okf-export \
  ~/.memanto/exports/memanto-okf-roundtrip-20260723_okf \
  --output sample/roundtrip-report.json
```

Observed round trip:

| Stage | Result |
| --- | ---: |
| OKF nodes loaded | 8 |
| memories mapped | 8 |
| memories skipped | 0 |
| memories imported | 8 |
| import failures | 0 |
| batches | 1 |
| re-exported documents | 8 |
| semantically unchanged | 8 |
| added / removed / changed | 0 / 0 / 0 |
| parity | PASS |

A live recall query, `Which commit added OKF UI?`, also returned commit
`06d11403dd4321a4141f4a7db6d32ff2339d20f5` as the highest-ranked result from
both agents. See `RECALL_REPORT.md` for the observed result and score details.

## Savings assessment

This Path C workflow starts from local Git, not a paid memory provider.
Memanto's OKF importer intentionally has no provider cost/latency comparison
module, so claiming token or dollar savings would be misleading.

The measurable portability result is:

- source extraction requires no LLM calls;
- snapshot/diff/validation require no LLM calls or hosted database;
- the owned artifact is plain Markdown plus one JSON manifest;
- Git stores only content changes between snapshots; and
- validation is deterministic and can run in CI at no inference cost.

Hosted costs are limited to the two small Memanto namespaces used for the live
proof. No private conversation content was uploaded.

## Fidelity notes

Memanto assigns new storage IDs on OKF import and appends a generated
`[Supporting data]` provenance footer. The validator excludes those native
transport details from knowledge hashes. It does not ignore arbitrary foreign
OKF supporting data. Titles, types, resources, tags, confidence, source,
status, and memory bodies survived the observed round trip.
