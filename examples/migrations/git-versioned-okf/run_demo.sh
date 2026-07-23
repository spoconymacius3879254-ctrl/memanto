#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 /path/to/git/repo agent-id [work-dir]" >&2
  exit 2
fi

repo=$1
agent_prefix=$2
work_dir=${3:-./demo-output}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source_agent="${agent_prefix}-source"
roundtrip_agent="${agent_prefix}-roundtrip"
export_root="${HOME}/.memanto/exports"

if [[ -n "${MEMANTO_API_KEY:-}" && -z "${MOORCHEH_API_KEY:-}" ]]; then
  export MOORCHEH_API_KEY="$MEMANTO_API_KEY"
fi

mkdir -p "$work_dir"
python "$script_dir/extract_git_memories.py" \
  --repo "$repo" \
  --limit 20 \
  --output "$work_dir/git-memories.json"

memanto agent create "$source_agent" \
  --pattern project \
  --description "Public Git history portability demo source"
memanto remember --batch "$work_dir/git-memories.json"
memanto memory export --agent "$source_agent" --okf --split file --limit 100

before="${export_root}/${source_agent}_okf"
memanto agent create "$roundtrip_agent" \
  --pattern project \
  --description "Clean target for OKF round-trip validation"
memanto migrate okf "$before" --agent "$roundtrip_agent"
memanto memory export --agent "$roundtrip_agent" --okf --split file --limit 100
after="${export_root}/${roundtrip_agent}_okf"

python "$script_dir/okf_history.py" snapshot \
  --bundle "$before" \
  --wiki "$work_dir/wiki" \
  --label "Git history import"
python "$script_dir/okf_history.py" validate \
  "$before" "$after" \
  --output "$work_dir/roundtrip-report.json"

echo
echo "Created a real Git -> Memanto -> OKF snapshot in $work_dir/wiki/okf"
echo "Round-trip validation: $work_dir/roundtrip-report.json"
