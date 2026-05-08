#!/usr/bin/env zsh
set -euo pipefail

ROOT="${1:-$PWD}"
QUERY="${2:-}"
PRESET="${3:-}"
MAX_RESULTS="${4:-20}"

if [[ -z "$QUERY" ]]; then
  echo "status=error\tmessage=query-required"
  exit 1
fi

uv run python - "$ROOT" "$QUERY" "$PRESET" "$MAX_RESULTS" <<'PY'
import sys
from pathlib import Path
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_search import WorkspaceSearchService
from metagit.core.mcp.services.upstream_hints import UpstreamHintService

root = Path(sys.argv[1]).resolve()
query = sys.argv[2]
preset = sys.argv[3] or None
max_results = int(sys.argv[4])

manager = MetagitConfigManager(config_path=root / ".metagit.yml")
cfg = manager.load_config()
if isinstance(cfg, Exception):
    print(f"status=error\tmessage=config-invalid\tdetail={cfg}")
    raise SystemExit(1)

index = WorkspaceIndexService().build_index(config=cfg, workspace_root=str(root))
repo_paths = [row["repo_path"] for row in index if row.get("exists")]
search_hits = WorkspaceSearchService().search(query=query, repo_paths=repo_paths, preset=preset, max_results=max_results)
ranked = UpstreamHintService().rank(blocker=query, repo_context=index)[:5]

print(f"status=ok\trepos={len(index)}\thits={len(search_hits)}")
for row in ranked:
    print(f"hint\trepo={row['repo_name']}\tscore={row['score']}")
for hit in search_hits[:5]:
    print(f"hit\tfile={hit['file_path']}\tline={hit['line_number']}")
PY