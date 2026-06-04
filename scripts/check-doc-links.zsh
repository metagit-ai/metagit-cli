#!/usr/bin/env zsh

set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

lychee_bin=""
for candidate in lychee "$HOME/.cargo/bin/lychee"; do
  if command -v "$candidate" >/dev/null 2>&1; then
    lychee_bin="$candidate"
    break
  fi
done

if [[ -z "$lychee_bin" ]]; then
  echo "ERROR: lychee is required but not found in PATH."
  echo "Install: brew install lychee   or   cargo install lychee --locked"
  exit 1
fi

exec "$lychee_bin" --config lychee.toml README.md 'docs/**/*.md'
