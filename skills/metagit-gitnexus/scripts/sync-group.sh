#!/usr/bin/env bash

set -euo pipefail

config_path=".metagit.yml"
group_name=""
prune=false
no_contract_sync=false

usage() {
  cat <<'EOF'
Usage: sync-group.sh [options]

Sync workspace.projects into a GitNexus group and run contract linking.

Options:
  -c, --config PATH     Manifest path (default: .metagit.yml)
  --group-name NAME     GitNexus group name (default: manifest name slug)
  --prune               Remove repos no longer in the workspace
  --no-contract-sync    Update membership only
  -h, --help            Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--config)
      config_path="${2:-}"
      shift 2
      ;;
    --group-name)
      group_name="${2:-}"
      shift 2
      ;;
    --prune)
      prune=true
      shift
      ;;
    --no-contract-sync)
      no_contract_sync=true
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

args=(gitnexus group sync -c "$config_path" --json)
if [[ -n "$group_name" ]]; then
  args+=(--group-name "$group_name")
fi
if [[ "$prune" == true ]]; then
  args+=(--prune)
fi
if [[ "$no_contract_sync" == true ]]; then
  args+=(--no-contract-sync)
fi

uv run metagit "${args[@]}"
