#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 /path/to/public/repo unique-agent-prefix output.cast" >&2
  exit 2
fi

repo=$1
agent_prefix=$2
output=$3
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
work_dir="${output%.cast}-output"

if ! command -v asciinema >/dev/null 2>&1; then
  echo "asciinema is required: https://docs.asciinema.org/manual/cli/installation/" >&2
  exit 2
fi
if [[ -e "$work_dir" ]]; then
  echo "Refusing to reuse existing demo directory: $work_dir" >&2
  exit 2
fi
if [[ "${TERM:-dumb}" == "dumb" ]]; then
  export TERM=xterm-256color
fi

capture_command=$(printf '%q ' \
  "$script_dir/demo_capture.sh" "$repo" "$agent_prefix" "$work_dir")
asciinema rec \
  --overwrite \
  --idle-time-limit 3 \
  --cols 110 \
  --rows 34 \
  --title "Memanto Git-versioned OKF freedom loop" \
  --command "$capture_command" \
  "$output"

if [[ $(wc -l < "$output") -lt 2 ]]; then
  echo "Recording contains no terminal events; the captured command failed." >&2
  exit 1
fi
echo "Recorded terminal demo: $output"
