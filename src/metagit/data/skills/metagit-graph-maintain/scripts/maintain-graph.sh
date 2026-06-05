#!/usr/bin/env bash

set -euo pipefail

config_path=".metagit.yml"
min_confidence="medium"
apply=false
ingest=false
gitnexus_repo=""

usage() {
  cat <<'EOF'
Usage: maintain-graph.sh [options]

Suggest and optionally apply graph.relationships, then ingest GitNexus overlay.

Options:
  -c, --config PATH       Manifest path (default: .metagit.yml)
  --min-confidence LEVEL  high | medium | all (default: medium)
  --apply                 Patch graph.relationships on disk
  --ingest                Run ingest-workspace-graph.sh after apply
  --gitnexus-repo NAME    Target GitNexus repo for ingest
  -h, --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--config)
      config_path="${2:-}"
      shift 2
      ;;
    --min-confidence)
      min_confidence="${2:-}"
      shift 2
      ;;
    --apply)
      apply=true
      shift
      ;;
    --ingest)
      ingest=true
      shift
      ;;
    --gitnexus-repo)
      gitnexus_repo="${2:-}"
      shift 2
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

args=(config graph suggest -c "$config_path" --min-confidence "$min_confidence" --json)
if [[ "$apply" == true ]]; then
  args+=(--apply)
fi

echo "suggest config=$config_path min_confidence=$min_confidence apply=$apply"
uv run metagit "${args[@]}"

if [[ "$apply" == true ]]; then
  uv run metagit config validate -c "$config_path"
fi

if [[ "$ingest" == true ]]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ingest_script="$(cd "$script_dir/../../metagit-gitnexus/scripts" && pwd)/ingest-workspace-graph.sh"
  ingest_args=(-c "$config_path")
  if [[ -n "$gitnexus_repo" ]]; then
    ingest_args+=(--gitnexus-repo "$gitnexus_repo")
  fi
  "$ingest_script" "${ingest_args[@]}"
fi
