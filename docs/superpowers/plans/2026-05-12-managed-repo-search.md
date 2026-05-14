# Managed repo search implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add managed-repo lookup to Metagit so CLI users and agents can search only `.metagit.yml`-managed repos, inspect sync status and local path, and reuse the same behavior through MCP and a small local HTTP API.

**Architecture:** Extend the managed repo model with flat metadata tags, enrich workspace repo rows with resolved path and status fields, and build one shared `ManagedRepoSearchService` in `src/metagit/core/project/`. Wrap that service with a thin top-level CLI command (`search` / `find`), a new MCP tool, and a local JSON API served from a new `api` command group.

**Tech Stack:** Python 3.12, Click, Pydantic, standard-library `http.server`, pytest, existing MCP runtime, existing Metagit config/workspace models.

---

### Task 1: Extend managed repo models and shared repo status rows

**Files:**
- Create: `tests/test_workspace_index_service.py`
- Modify: `src/metagit/core/project/models.py`
- Modify: `src/metagit/core/mcp/services/workspace_index.py`
- Modify: `schemas/metagit_config.schema.json`
- Modify: `docs/cli_reference.md`

- [ ] **Step 1: Write the failing tests for tags and enriched repo rows**

```python
#!/usr/bin/env python
from pathlib import Path

from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config(tmp_path: Path) -> MetagitConfig:
  repo_dir = tmp_path / "workspace" / "platform" / "abacus-app"
  repo_dir.mkdir(parents=True)
  (repo_dir / ".git").mkdir()
  return MetagitConfig(
    name="workspace",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="platform",
          repos=[
            ProjectPath(
              name="abacus-app",
              path="platform/abacus-app",
              url="https://github.com/example/abacus-app.git",
              sync=True,
              tags={"code": "abacus", "domain": "terraform"},
            )
          ],
        )
      ]
    ),
  )


def test_workspace_index_builds_managed_repo_status_rows(tmp_path: Path) -> None:
  config = _config(tmp_path)
  rows = WorkspaceIndexService().build_index(
    config=config,
    workspace_root=str(tmp_path / "workspace"),
  )

  assert rows[0]["project_name"] == "platform"
  assert rows[0]["repo_name"] == "abacus-app"
  assert rows[0]["configured_path"] == "platform/abacus-app"
  assert rows[0]["tags"] == {"code": "abacus", "domain": "terraform"}
  assert rows[0]["exists"] is True
  assert rows[0]["is_git_repo"] is True
  assert rows[0]["status"] == "synced"


def test_workspace_index_marks_missing_repo_as_configured_missing(tmp_path: Path) -> None:
  config = MetagitConfig(
    name="workspace",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="platform",
          repos=[ProjectPath(name="missing", path="platform/missing", sync=True)],
        )
      ]
    ),
  )

  rows = WorkspaceIndexService().build_index(
    config=config,
    workspace_root=str(tmp_path / "workspace"),
  )

  assert rows[0]["exists"] is False
  assert rows[0]["status"] == "configured_missing"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_workspace_index_service.py -q`

Expected: FAIL with missing `tags`, `configured_path`, `is_git_repo`, or `status` fields in workspace index rows.

- [ ] **Step 3: Extend `ProjectPath` with flat tags**

```python
class ProjectPath(BaseModel):
  name: str = Field(..., description="Friendly name for the path or project")
  source_provider: Optional[str] = Field(
    None, description="Provider used to discover this repository"
  )
  source_namespace: Optional[str] = Field(
    None, description="Source namespace identifier (org/user/group)"
  )
  source_repo_id: Optional[str] = Field(
    None, description="Provider-native repository identifier"
  )
  protected: Optional[bool] = Field(
    False,
    description="If true, reconcile mode must not remove this repository automatically",
  )
  tags: dict[str, str] = Field(
    default_factory=dict,
    description="Flat metadata tags used for managed repo filtering and lookup",
  )
```

- [ ] **Step 4: Enrich `WorkspaceIndexService.build_index()` with stable managed repo status rows**

```python
from metagit.core.utils.common import is_git_repository


class WorkspaceIndexService:
  def build_index(self, config: MetagitConfig, workspace_root: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not config.workspace:
      return rows

    for project in config.workspace.projects:
      for repo in project.repos:
        resolved_path = self._resolve_repo_path(
          workspace_root=workspace_root,
          configured_path=repo.path,
          repo_name=repo.name,
        )
        exists = os.path.isdir(resolved_path)
        is_git_repo = bool(is_git_repository(resolved_path)) if exists else False
        status = "synced" if exists and is_git_repo else "configured_missing"
        rows.append(
          {
            "project_name": project.name,
            "repo_name": repo.name,
            "configured_path": repo.path,
            "repo_path": resolved_path,
            "exists": exists,
            "is_git_repo": is_git_repo,
            "status": status,
            "url": str(repo.url) if repo.url else None,
            "sync": repo.sync if repo.sync is not None else False,
            "tags": dict(repo.tags),
          }
        )
    return rows
```

- [ ] **Step 5: Regenerate the schema and update CLI reference docs**

```bash
task generate:schema
```

Add a short reference entry to `docs/cli_reference.md` noting that managed repo entries now support flat `tags` maps for search and filtering.

- [ ] **Step 6: Run the focused tests again**

Run: `uv run pytest tests/test_workspace_index_service.py -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/metagit/core/project/models.py src/metagit/core/mcp/services/workspace_index.py tests/test_workspace_index_service.py schemas/metagit_config.schema.json docs/cli_reference.md
git commit -m "feat: add managed repo tags and status rows"
```

### Task 2: Build the shared managed repo search service

**Files:**
- Create: `src/metagit/core/project/search_models.py`
- Create: `src/metagit/core/project/search_service.py`
- Create: `tests/test_project_search_service.py`

- [ ] **Step 1: Write the failing unit tests for search and resolve behavior**

```python
#!/usr/bin/env python
from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.project.search_service import ManagedRepoSearchService
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config(tmp_path: Path) -> MetagitConfig:
  workspace_root = tmp_path / "workspace"
  app_repo = workspace_root / "platform" / "abacus-app"
  module_repo = workspace_root / "shared" / "abacus-module"
  app_repo.mkdir(parents=True)
  module_repo.mkdir(parents=True)
  (app_repo / ".git").mkdir()
  (module_repo / ".git").mkdir()
  return MetagitConfig(
    name="workspace",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="platform",
          repos=[
            ProjectPath(
              name="abacus-app",
              path="platform/abacus-app",
              url="https://github.com/example/abacus-app.git",
              sync=True,
              tags={"code": "abacus", "domain": "terraform"},
            )
          ],
        ),
        WorkspaceProject(
          name="shared",
          repos=[
            ProjectPath(
              name="abacus-module",
              path="shared/abacus-module",
              url="https://github.com/example/abacus-module.git",
              sync=True,
              tags={"code": "abacus", "domain": "terraform-module"},
            )
          ],
        ),
      ]
    ),
  )


def test_search_prioritizes_exact_repo_name(tmp_path: Path) -> None:
  service = ManagedRepoSearchService()
  result = service.search(
    config=_config(tmp_path),
    workspace_root=str(tmp_path / "workspace"),
    query="abacus-app",
  )
  assert result.matches[0].repo_name == "abacus-app"
  assert "repo_name:exact" in result.matches[0].match_reasons


def test_search_can_filter_by_tag(tmp_path: Path) -> None:
  service = ManagedRepoSearchService()
  result = service.search(
    config=_config(tmp_path),
    workspace_root=str(tmp_path / "workspace"),
    query="abacus",
    tags={"domain": "terraform-module"},
  )
  assert [match.repo_name for match in result.matches] == ["abacus-module"]


def test_resolve_one_returns_ambiguous_match(tmp_path: Path) -> None:
  service = ManagedRepoSearchService()
  resolved = service.resolve_one(
    config=_config(tmp_path),
    workspace_root=str(tmp_path / "workspace"),
    query="abacus",
    synced_only=True,
  )
  assert resolved.error is not None
  assert resolved.error.kind == "ambiguous_match"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_project_search_service.py -q`

Expected: FAIL because `ManagedRepoSearchService` and its models do not exist yet.

- [ ] **Step 3: Create the runtime-only search models**

```python
#!/usr/bin/env python
from pydantic import BaseModel, Field


class ManagedRepoStatus(BaseModel):
  resolved_path: str
  exists: bool
  is_git_repo: bool
  sync_enabled: bool
  status: str


class ManagedRepoMatch(BaseModel):
  project_name: str
  repo_name: str
  url: str | None = None
  configured_path: str | None = None
  tags: dict[str, str] = Field(default_factory=dict)
  status: ManagedRepoStatus
  match_reasons: list[str] = Field(default_factory=list)
  score: int


class ManagedRepoSearchResult(BaseModel):
  query: str
  matches: list[ManagedRepoMatch] = Field(default_factory=list)


class ManagedRepoError(BaseModel):
  kind: str
  message: str
  matches: list[ManagedRepoMatch] = Field(default_factory=list)


class ManagedRepoResolveResult(BaseModel):
  match: ManagedRepoMatch | None = None
  error: ManagedRepoError | None = None
```

- [ ] **Step 4: Implement the shared search service around `WorkspaceIndexService` rows**

```python
#!/usr/bin/env python
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.project.search_models import (
  ManagedRepoError,
  ManagedRepoMatch,
  ManagedRepoResolveResult,
  ManagedRepoSearchResult,
)


class ManagedRepoSearchService:
  def __init__(self) -> None:
    self._index = WorkspaceIndexService()

  def search(self, config, workspace_root, query, *, project=None, exact=False, synced_only=False, tags=None, limit=10):
    rows = self._index.build_index(config=config, workspace_root=workspace_root)
    matches = []
    for row in rows:
      if project and row["project_name"] != project:
        continue
      if synced_only and row["status"] != "synced":
        continue
      if tags and any(row["tags"].get(key) != value for key, value in tags.items()):
        continue
      score, reasons = self._match_row(row=row, query=query, exact=exact)
      if score <= 0:
        continue
      matches.append(self._to_match(row=row, score=score, reasons=reasons))
    matches.sort(key=lambda item: (-item.score, item.project_name, item.repo_name))
    return ManagedRepoSearchResult(query=query, matches=matches[:limit])

  def resolve_one(self, config, workspace_root, query, *, project=None, exact=False, synced_only=True, tags=None):
    result = self.search(
      config=config,
      workspace_root=workspace_root,
      query=query,
      project=project,
      exact=exact,
      synced_only=synced_only,
      tags=tags,
      limit=25,
    )
    if not result.matches:
      return ManagedRepoResolveResult(
        error=ManagedRepoError(kind="not_found", message="No managed repository matched the query.")
      )
    if len(result.matches) > 1:
      return ManagedRepoResolveResult(
        error=ManagedRepoError(
          kind="ambiguous_match",
          message="Search matched more than one managed repository.",
          matches=result.matches,
        )
      )
    return ManagedRepoResolveResult(match=result.matches[0])
```

- [ ] **Step 5: Run the focused tests again**

Run: `uv run pytest tests/test_project_search_service.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/metagit/core/project/search_models.py src/metagit/core/project/search_service.py tests/test_project_search_service.py
git commit -m "feat: add managed repo search service"
```

### Task 3: Add `metagit search` and `metagit find`

**Files:**
- Create: `src/metagit/cli/commands/search.py`
- Create: `tests/cli/commands/test_search.py`
- Modify: `src/metagit/cli/main.py`
- Modify: `docs/cli_reference.md`

- [ ] **Step 1: Write the failing CLI tests**

```python
#!/usr/bin/env python
from click.testing import CliRunner

from metagit.cli.main import cli


def test_search_command_returns_json_matches(tmp_path) -> None:
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: abacus-app",
        "          path: platform/abacus-app",
        "          sync: true",
        "          tags:",
        "            code: abacus",
      ]
    ) + "\n",
    encoding="utf-8",
  )
  repo_dir = tmp_path / "platform" / "abacus-app"
  repo_dir.mkdir(parents=True)
  (repo_dir / ".git").mkdir()

  runner = CliRunner()
  with runner.isolated_filesystem(temp_dir=str(tmp_path)):
    result = runner.invoke(
      cli,
      ["search", "abacus", "--json"],
      catch_exceptions=False,
    )

  assert result.exit_code == 0
  assert '"repo_name": "abacus-app"' in result.output


def test_find_alias_matches_search_command(tmp_path) -> None:
  runner = CliRunner()
  result = runner.invoke(cli, ["find", "--help"])
  assert result.exit_code == 0
  assert "metagit search" in result.output or "Search managed repositories" in result.output
```

- [ ] **Step 2: Run the CLI tests to verify they fail**

Run: `uv run pytest tests/cli/commands/test_search.py -q`

Expected: FAIL because `search` and `find` are not registered.

- [ ] **Step 3: Implement the new top-level search command**

```python
#!/usr/bin/env python
import json

import click

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.project.search_service import ManagedRepoSearchService


def _parse_tag_filters(tag_values: tuple[str, ...]) -> dict[str, str]:
  parsed: dict[str, str] = {}
  for item in tag_values:
    key, value = item.split("=", 1)
    parsed[key] = value
  return parsed


@click.command("search")
@click.argument("query")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--project", default=None)
@click.option("--exact", is_flag=True, default=False)
@click.option("--synced-only", is_flag=True, default=False)
@click.option("--tag", "tag_values", multiple=True)
@click.option("--limit", default=10, type=int, show_default=True)
@click.option("--json", "as_json", is_flag=True, default=False)
@click.option("--path-only", is_flag=True, default=False)
@click.pass_context
def search(ctx: click.Context, query: str, definition_path: str, project: str | None, exact: bool, synced_only: bool, tag_values: tuple[str, ...], limit: int, as_json: bool, path_only: bool) -> None:
  manager = MetagitConfigManager(definition_path)
  config = manager.load_config()
  if isinstance(config, Exception):
    raise click.ClickException(str(config))

  workspace_root = str(Path(definition_path).resolve().parent)
  service = ManagedRepoSearchService()
  result = service.search(
    config=config,
    workspace_root=workspace_root,
    query=query,
    project=project,
    exact=exact,
    synced_only=synced_only,
    tags=_parse_tag_filters(tag_values),
    limit=limit,
  )
  if as_json:
    click.echo(result.model_dump_json(indent=2))
    return
  if path_only:
    resolved = service.resolve_one(
      config=config,
      workspace_root=workspace_root,
      query=query,
      project=project,
      exact=exact,
      synced_only=synced_only,
      tags=_parse_tag_filters(tag_values),
    )
    if resolved.error:
      raise click.ClickException(resolved.error.message)
    click.echo(resolved.match.status.resolved_path)
    return
  if not result.matches:
    raise click.ClickException(f"No managed repository matched '{query}'.")
  for index, match in enumerate(result.matches, start=1):
    click.echo(f"{index}. project={match.project_name} repo={match.repo_name}")
    click.echo(f"   path={match.status.resolved_path}")
    click.echo(
      f"   status={match.status.status} exists={match.status.exists} git={match.status.is_git_repo} sync={match.status.sync_enabled}"
    )
    click.echo(f"   matched={','.join(match.match_reasons)}")
```

- [ ] **Step 4: Register the commands and update CLI reference docs**

```python
from metagit.cli.commands.search import search

cli.add_command(search)
cli.add_command(search, name="find")
```

Add a CLI reference section that shows `search`, `find`, `--json`, `--path-only`, and `--tag key=value`.

- [ ] **Step 5: Run the CLI tests again**

Run: `uv run pytest tests/cli/commands/test_search.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/metagit/cli/main.py src/metagit/cli/commands/search.py tests/cli/commands/test_search.py docs/cli_reference.md
git commit -m "feat: add managed repo search CLI"
```

### Task 4: Add the MCP repo search tool

**Files:**
- Modify: `src/metagit/core/mcp/tool_registry.py`
- Modify: `src/metagit/core/mcp/runtime.py`
- Modify: `tests/core/mcp/test_runtime.py`
- Modify: `tests/integration/test_mcp_workspace_flow.py`

- [ ] **Step 1: Write the failing MCP runtime tests**

```python
def test_tools_list_includes_repo_search_for_active_workspace(tmp_path: Path) -> None:
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos: []",
      ]
    ) + "\n",
    encoding="utf-8",
  )
  runtime = MetagitMcpRuntime(root=str(tmp_path))
  response = runtime._handle_request(
    {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}}
  )
  names = [item["name"] for item in response["result"]["tools"]]
  assert "metagit_repo_search" in names


def test_tools_call_repo_search_returns_matches(tmp_path: Path) -> None:
  repo_dir = tmp_path / "platform" / "abacus-app"
  repo_dir.mkdir(parents=True)
  (repo_dir / ".git").mkdir()
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: abacus-app",
        "          path: platform/abacus-app",
        "          sync: true",
      ]
    ) + "\n",
    encoding="utf-8",
  )
  runtime = MetagitMcpRuntime(root=str(tmp_path))
  response = runtime._handle_request(
    {
      "jsonrpc": "2.0",
      "id": 11,
      "method": "tools/call",
      "params": {"name": "metagit_repo_search", "arguments": {"query": "abacus"}},
    }
  )
  payload = json.loads(response["result"]["content"][0]["text"])
  assert payload["matches"][0]["repo_name"] == "abacus-app"
```

- [ ] **Step 2: Run the focused MCP tests to verify they fail**

Run: `uv run pytest tests/core/mcp/test_runtime.py -q`

Expected: FAIL because `metagit_repo_search` is not registered or dispatched.

- [ ] **Step 3: Register the new MCP tool**

```python
class ToolRegistry:
  _active_tools: list[str] = [
    "metagit_workspace_status",
    "metagit_workspace_index",
    "metagit_workspace_search",
    "metagit_repo_search",
    "metagit_upstream_hints",
    "metagit_repo_inspect",
    "metagit_repo_sync",
    "metagit_bootstrap_config",
  ]
```

- [ ] **Step 4: Add the tool schema and dispatcher branch in `MetagitMcpRuntime`**

```python
self._tool_schemas["metagit_repo_search"] = {
  "type": "object",
  "required": ["query"],
  "properties": {
    "query": {"type": "string"},
    "project": {"type": "string"},
    "exact": {"type": "boolean"},
    "synced_only": {"type": "boolean"},
    "limit": {"type": "integer", "minimum": 1},
    "tags": {
      "type": "object",
      "additionalProperties": {"type": "string"},
    },
  },
  "additionalProperties": False,
}

if name == "metagit_repo_search":
  if not config or not status.root_path:
    raise InvalidToolArgumentsError("managed repo search requires an active workspace")
  query = str(arguments.get("query", "")).strip()
  if not query:
    raise InvalidToolArgumentsError("query is required")
  result = self._managed_repo_search.search(
    config=config,
    workspace_root=status.root_path,
    query=query,
    project=arguments.get("project"),
    exact=bool(arguments.get("exact", False)),
    synced_only=bool(arguments.get("synced_only", False)),
    tags=arguments.get("tags"),
    limit=int(arguments.get("limit", 10)),
  )
  return result.model_dump(mode="json")
```

- [ ] **Step 5: Run the MCP tests again**

Run: `uv run pytest tests/core/mcp/test_runtime.py tests/integration/test_mcp_workspace_flow.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/metagit/core/mcp/tool_registry.py src/metagit/core/mcp/runtime.py tests/core/mcp/test_runtime.py tests/integration/test_mcp_workspace_flow.py
git commit -m "feat: add managed repo search MCP tool"
```

### Task 5: Add the local HTTP API and `metagit api serve`

**Files:**
- Create: `src/metagit/core/api/server.py`
- Create: `src/metagit/core/api/__init__.py`
- Create: `src/metagit/cli/commands/api.py`
- Create: `tests/api/test_repo_search_api.py`
- Create: `tests/cli/commands/test_api.py`
- Modify: `src/metagit/cli/main.py`

- [ ] **Step 1: Write the failing API tests**

```python
#!/usr/bin/env python
import json
import threading
import urllib.request

from metagit.core.api.server import build_server


def test_repo_search_endpoint_returns_matches(tmp_path) -> None:
  repo_dir = tmp_path / "platform" / "abacus-app"
  repo_dir.mkdir(parents=True)
  (repo_dir / ".git").mkdir()
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: abacus-app",
        "          path: platform/abacus-app",
        "          sync: true",
      ]
    ) + "\n",
    encoding="utf-8",
  )
  server = build_server(root=str(tmp_path), host="127.0.0.1", port=0)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  try:
    url = f"http://127.0.0.1:{server.server_port}/v1/repos/search?q=abacus"
    payload = json.loads(urllib.request.urlopen(url).read().decode("utf-8"))
    assert payload["matches"][0]["repo_name"] == "abacus-app"
  finally:
    server.shutdown()
    thread.join()


def test_api_cli_status_once_reports_bound_port(tmp_path) -> None:
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["api", "serve", "--root", str(tmp_path), "--status-once", "--port", "0"],
  )
  assert result.exit_code == 0
  assert "api_state=ready" in result.output
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run: `uv run pytest tests/api/test_repo_search_api.py -q`

Expected: FAIL because the API server code does not exist yet.

- [ ] **Step 3: Implement a minimal local JSON API server with the shared search service**

```python
#!/usr/bin/env python
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.project.search_service import ManagedRepoSearchService


def build_server(root: str, host: str, port: int) -> ThreadingHTTPServer:
  class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
      parsed = urlparse(self.path)
      params = parse_qs(parsed.query)
      manager = MetagitConfigManager(f"{root}/.metagit.yml")
      config = manager.load_config()
      service = ManagedRepoSearchService()
      if parsed.path == "/v1/repos/search":
        result = service.search(
          config=config,
          workspace_root=root,
          query=params.get("q", [""])[0],
          project=params.get("project", [None])[0],
          exact=params.get("exact", ["false"])[0] == "true",
          synced_only=params.get("synced_only", ["false"])[0] == "true",
          tags=_parse_tag_filters(params.get("tag", [])),
        )
        self._json(200, result.model_dump(mode="json"))
        return
      if parsed.path == "/v1/repos/resolve":
        resolved = service.resolve_one(
          config=config,
          workspace_root=root,
          query=params.get("q", [""])[0],
          project=params.get("project", [None])[0],
          exact=params.get("exact", ["false"])[0] == "true",
          synced_only=params.get("synced_only", ["true"])[0] == "true",
          tags=_parse_tag_filters(params.get("tag", [])),
        )
        code = 200 if resolved.match else 409 if resolved.error and resolved.error.kind == "ambiguous_match" else 404
        self._json(code, resolved.model_dump(mode="json"))
        return
      self._json(404, {"error": {"kind": "not_found", "message": "Unknown endpoint"}})

    def _json(self, status: int, payload: dict) -> None:
      body = json.dumps(payload).encode("utf-8")
      self.send_response(status)
      self.send_header("Content-Type", "application/json")
      self.send_header("Content-Length", str(len(body)))
      self.end_headers()
      self.wfile.write(body)

  return ThreadingHTTPServer((host, port), Handler)
```

- [ ] **Step 4: Add the `api` command group and register it**

```python
@click.group()
def api() -> None:
  """Local JSON API commands."""


@api.command("serve")
@click.option("--root", default=".")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=7878, type=int, show_default=True)
@click.option("--status-once", is_flag=True, default=False)
def serve(root: str, host: str, port: int, status_once: bool) -> None:
  server = build_server(root=root, host=host, port=port)
  if status_once:
    click.echo(f"api_state=ready host={host} port={server.server_port}")
    server.server_close()
    return
  server.serve_forever()
```

- [ ] **Step 5: Run the API and CLI tests again**

Run: `uv run pytest tests/api/test_repo_search_api.py tests/cli/commands/test_api.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/metagit/core/api/__init__.py src/metagit/core/api/server.py src/metagit/cli/commands/api.py src/metagit/cli/main.py tests/api/test_repo_search_api.py tests/cli/commands/test_api.py
git commit -m "feat: add managed repo search API"
```

### Task 6: Full verification, docs, and scaffold updates

**Files:**
- Modify: `.mex/ROUTER.md`
- Modify: `.mex/context/architecture.md`
- Review: `.mex/patterns/INDEX.md`
- Review: `.mex/patterns/`
- Modify: `README.md` (if CLI/API usage belongs there)

- [ ] **Step 1: Update docs and `.mex` scaffold for the new capability**

```markdown
- Add a short router state note that managed repo search now exists across CLI, MCP, and local API
- Update architecture context to mention the shared repo search service and API command surface
- Check whether an existing pattern already covers the final workflow; if not, create `add-managed-repo-search.md` and add it to `INDEX.md`
```

- [ ] **Step 2: Run focused test suites first**

Run: `uv run pytest tests/test_workspace_index_service.py tests/test_project_search_service.py tests/cli/commands/test_search.py tests/core/mcp/test_runtime.py tests/integration/test_mcp_workspace_flow.py tests/api/test_repo_search_api.py tests/cli/commands/test_api.py -q`

Expected: PASS

- [ ] **Step 3: Run repo verification commands**

Run: `task lint`
Expected: PASS

Run: `task test`
Expected: PASS

Run: `task skills:sync generate:schema`
Expected: PASS

Run: `task qa:prepush`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md docs/cli_reference.md .mex/ROUTER.md .mex/context/architecture.md .mex/patterns/INDEX.md
git commit -m "fix: document managed repo search workflows"
```

- [ ] **Step 5: Final manual smoke checks**

Run: `uv run metagit search abacus --json`
Expected: JSON output with `matches`

Run: `uv run metagit find abacus --path-only`
Expected: one resolved path or an ambiguity error

Run: `uv run metagit mcp serve --root . --status-once`
Expected: `mcp_state=active`

Run: `uv run metagit api serve --root . --status-once`
Expected: `api_state=ready`
