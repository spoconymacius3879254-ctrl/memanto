# Live recall parity report

Run date: 2026-07-23  
Query: `Which commit added OKF UI?`

The same standard semantic-recall query was run against:

1. the source agent populated directly from real Git history; and
2. the clean agent populated only by importing the source agent's OKF export.

## Source agent

Agent: `memanto-okf-git-public-20260723`

Top result:

- title: `Git change: Merge pull request #1588 from moorcheh-ai/add/okf-ui`
- commit: `06d11403dd4321a4141f4a7db6d32ff2339d20f5`
- source reference:
  `https://github.com/moorcheh-ai/memanto.git@06d11403dd4321a4141f4a7db6d32ff2339d20f5`
- rank: 1 of 3 returned
- similarity score: 0.268

## Clean round-trip agent

Agent: `memanto-okf-roundtrip-20260723`

Top result:

- title: `Git change: Merge pull request #1588 from moorcheh-ai/add/okf-ui`
- commit: `06d11403dd4321a4141f4a7db6d32ff2339d20f5`
- source reference:
  `https://github.com/moorcheh-ai/memanto.git@06d11403dd4321a4141f4a7db6d32ff2339d20f5`
- rank: 1 of 3 returned
- similarity score: 0.285

## Result

Recall parity passed for the demonstrated question: both agents returned the
same title, full commit hash, source reference, type, confidence, provenance,
and tags as their highest-ranked result.

The similarity scores and lower-result ordering differ slightly because the two
agents use separate hosted vector namespaces. The claimed fidelity property is
knowledge and top-answer parity, not byte-identical vector scores.

This live result complements `sample/roundtrip-report.json`, which checks all 8
records deterministically and reports zero added, removed, or changed knowledge.
