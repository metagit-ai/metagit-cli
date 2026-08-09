#!/usr/bin/env bash
set -euo pipefail

PROJECT_FILTER="${1:-}"

if [[ -z "${PROJECT_FILTER}" ]]; then
  echo "Usage: $(basename "$0") <project-filter>"
  exit 1
fi

metagit context resume "${PROJECT_FILTER}" --format detailed
