#!/usr/bin/env zsh

set -euo pipefail

workspace_root="${1:-.}"
project_name="${2:-default}"

if [[ ! -f ".metagit.yml" ]]; then
  echo "ERROR: .metagit.yml not found in current directory"
  exit 2
fi

echo "analyze repo=$(pwd)"
npx gitnexus analyze

tmp_output="$(mktemp)"
uv run python - "$workspace_root" "$project_name" <<'PY' > "$tmp_output"
import sys
from pathlib import Path
import yaml

workspace_root = Path(sys.argv[1]).expanduser().resolve()
project_name = sys.argv[2]
cfg = yaml.safe_load(Path(".metagit.yml").read_text(encoding="utf-8")) or {}
workspace = (cfg.get("workspace") or {})
projects = workspace.get("projects") or []
target = next((p for p in projects if p.get("name") == project_name), None)
if not target:
    print(f"warn project_not_found={project_name}")
    raise SystemExit(0)

for repo in target.get("repos") or []:
    name = repo.get("name")
    if not name:
        continue
    repo_path = workspace_root / project_name / name
    if repo_path.exists() and repo_path.is_dir():
        print(f"repo_path={repo_path}")
    else:
        print(f"skip_missing={repo_path}")
PY

while IFS= read -r line; do
  case "$line" in
    repo_path=*)
      path="${line#repo_path=}"
      echo "analyze repo=${path}"
      (cd "$path" && npx gitnexus analyze) || echo "fail repo=${path}"
      ;;
    *)
      echo "$line"
      ;;
  esac
done < "$tmp_output"

rm -f "$tmp_output"
