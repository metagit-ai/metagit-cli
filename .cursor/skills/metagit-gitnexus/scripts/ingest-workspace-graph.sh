#!/usr/bin/env bash

set -euo pipefail

config_path=".metagit.yml"
gitnexus_repo=""
dry_run=false
tool_calls_file=""

usage() {
  cat <<'EOF'
Usage: ingest-workspace-graph.sh [options]

Export metagit workspace graph tool_calls and run gitnexus cypher for each.

Options:
  -c, --config PATH        Manifest path (default: .metagit.yml)
  --gitnexus-repo NAME     Target GitNexus repo name (default: manifest name)
  --tool-calls FILE        Use existing tool-calls JSON instead of exporting
  --dry-run                Print queries without executing
  -h, --help               Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--config)
      config_path="${2:-}"
      shift 2
      ;;
    --gitnexus-repo)
      gitnexus_repo="${2:-}"
      shift 2
      ;;
    --tool-calls)
      tool_calls_file="${2:-}"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ingest_py="$script_dir/ingest_workspace_graph.py"
tmp_file=""

cleanup() {
  if [[ -n "$tmp_file" && -f "$tmp_file" ]]; then
    rm -f "$tmp_file"
  fi
}
trap cleanup EXIT

if [[ -z "$tool_calls_file" ]]; then
  tmp_file="$(mktemp)"
  export_args=(config graph export -c "$config_path" --format tool-calls)
  if [[ -n "$gitnexus_repo" ]]; then
    export_args+=(--gitnexus-repo "$gitnexus_repo")
  fi
  echo "export config=$config_path"
  uv run metagit "${export_args[@]}" --output "$tmp_file"
  tool_calls_file="$tmp_file"
fi

ingest_args=("$tool_calls_file")
if [[ "$dry_run" == true ]]; then
  ingest_args+=(--dry-run)
fi

uv run python "$ingest_py" "${ingest_args[@]}"
