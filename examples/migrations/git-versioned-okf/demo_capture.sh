#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 /path/to/public/repo unique-agent-prefix work-dir" >&2
  exit 2
fi

repo=$1
agent_prefix=$2
work_dir=$3
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

clear
echo "MEMANTO + OKF: IN -> OWNED -> PORTABLE"
echo "======================================"
echo
echo "1. Real public source data"
git -C "$repo" log "${MEMANTO_DEMO_REF:-HEAD}" --oneline --max-count=8
sleep 2

echo
echo "2. Live Git -> Memanto -> OKF -> clean-agent round trip"
MEMANTO_DEMO_LIMIT=${MEMANTO_DEMO_LIMIT:-8} \
MEMANTO_DEMO_REF=${MEMANTO_DEMO_REF:-HEAD} \
  "$script_dir/run_demo.sh" "$repo" "$agent_prefix" "$work_dir"
sleep 2

echo
echo "3. Human-readable owned memory"
first_memory=$(find "$work_dir/wiki/okf/memories" -type f \
  -name '*.md' ! -name 'index.md' | sort | head -n 1)
sed -n '1,45p' "$first_memory"
sleep 2

echo
echo "4. Deterministic full-bundle parity"
python "$script_dir/okf_history.py" validate \
  "${HOME}/.memanto/exports/${agent_prefix}-source_okf" \
  "${HOME}/.memanto/exports/${agent_prefix}-roundtrip_okf"
sleep 2

echo
echo "5. Same live recall question before and after migration"
memanto agent activate "${agent_prefix}-source"
memanto recall "Which commit added OKF UI?" --limit 1
memanto agent activate "${agent_prefix}-roundtrip"
memanto recall "Which commit added OKF UI?" --limit 1

echo
echo "DEMO COMPLETE: memory remained readable, portable, and recallable."
