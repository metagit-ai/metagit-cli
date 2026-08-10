# Metagit Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `metagit web serve` — a localhost SPA for schema-aware config editing (`.metagit.yml` + app config) and workspace operations (browse synced/missing, sync, health, prune).

**Architecture:** Extend the existing `ThreadingHTTPServer` pattern with a dedicated `WebServer` composing v2 catalog handlers plus new `/v3/config/*` and `/v3/ops/*` routes. A new `SchemaTreeService` walks Pydantic models server-side; a Vite+React SPA in `web/` builds to `src/metagit/data/web/`.

**Tech Stack:** Python 3.12, Click, Pydantic v2, stdlib HTTP; Vite, React 18, TypeScript, TanStack Query, Zustand.

**Spec:** [2026-05-20-metagit-web-design.md](../specs/2026-05-20-metagit-web-design.md)

---

## File map

| File | Responsibility |
|------|----------------|
| `src/metagit/core/web/models.py` | API request/response pydantic models |
| `src/metagit/core/web/schema_tree.py` | `SchemaTreeService`, path apply ops |
| `src/metagit/core/web/job_store.py` | In-memory sync job + SSE events |
| `src/metagit/core/web/config_handler.py` | `/v3/config/*` routes |
| `src/metagit/core/web/ops_handler.py` | `/v3/ops/*` routes |
| `src/metagit/core/web/static_handler.py` | Serve bundled SPA |
| `src/metagit/core/web/server.py` | `build_web_server()` |
| `src/metagit/cli/commands/web.py` | `metagit web serve` |
| `src/metagit/cli/main.py` | Register `web` command |
| `web/*` | React SPA source |
| `src/metagit/data/web/*` | Built assets (package data) |
| `tests/core/web/test_schema_tree.py` | Schema tree unit tests |
| `tests/core/web/test_config_handler.py` | Config API tests |
| `tests/core/web/test_ops_handler.py` | Ops API tests |
| `tests/cli/commands/test_web.py` | CLI smoke |
| `docs/reference/metagit-web.md` | User docs |

---

### Task 1: Web API pydantic models

**Files:**
- Create: `src/metagit/core/web/__init__.py`
- Create: `src/metagit/core/web/models.py`
- Test: `tests/core/web/__init__.py` (empty ok)

- [ ] **Step 1: Create package init**

```python
#!/usr/bin/env python
"""Local web UI server components."""
```

- [ ] **Step 2: Create models**

```python
#!/usr/bin/env python
"""Pydantic models for metagit web API."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConfigOpKind(str, Enum):
  ENABLE = "enable"
  DISABLE = "disable"
  SET = "set"


class ConfigOperation(BaseModel):
  op: ConfigOpKind
  path: str
  value: Any | None = None


class ConfigPatchRequest(BaseModel):
  save: bool = False
  operations: list[ConfigOperation] = Field(default_factory=list)


class SchemaFieldNode(BaseModel):
  path: str
  key: str
  type: str
  description: str | None = None
  required: bool = False
  enabled: bool = False
  editable: bool = True
  sensitive: bool = False
  default_value: Any | None = None
  value: Any | None = None
  children: list["SchemaFieldNode"] = Field(default_factory=list)


class ConfigTreeResponse(BaseModel):
  ok: bool
  target: Literal["metagit", "appconfig"]
  config_path: str
  tree: SchemaFieldNode
  validation_errors: list[dict[str, str]] = Field(default_factory=list)
  saved: bool = False


class SyncJobRequest(BaseModel):
  repos: list[str] | None = None
  mode: Literal["fetch", "pull", "clone"] = "fetch"
  dry_run: bool = False
  allow_mutation: bool = True
  max_parallel: int = 4


class SyncJobStatus(BaseModel):
  job_id: str
  state: Literal["pending", "running", "completed", "failed"]
  summary: dict[str, Any] = Field(default_factory=dict)
  results: list[dict[str, Any]] = Field(default_factory=list)
  error: str | None = None
```

- [ ] **Step 3: Commit**

```bash
git add src/metagit/core/web/ tests/core/web/
git commit -m "feat(web): add web API pydantic models"
```

---

### Task 2: SchemaTreeService — tree build and path operations

**Files:**
- Create: `src/metagit/core/web/schema_tree.py`
- Test: `tests/core/web/test_schema_tree.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Tests for SchemaTreeService."""

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.web.models import ConfigOpKind, ConfigOperation
from metagit.core.web.schema_tree import SchemaTreeService


def test_build_metagit_tree_marks_present_fields() -> None:
  config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
  service = SchemaTreeService()
  tree = service.build_tree(config, MetagitConfig)
  name_node = service.find_node(tree, "name")
  assert name_node is not None
  assert name_node.enabled is True
  assert name_node.value == "demo"


def test_disable_optional_field_removes_key() -> None:
  payload = {
    "name": "demo",
    "kind": "application",
    "description": "hello",
  }
  config = MetagitConfig.model_validate(payload)
  service = SchemaTreeService()
  updated, errors = service.apply_operations(
    config,
    MetagitConfig,
    [ConfigOperation(op=ConfigOpKind.DISABLE, path="description")],
  )
  assert errors == []
  dumped = updated.model_dump(exclude_none=True)
  assert "description" not in dumped


def test_enable_optional_field_adds_default() -> None:
  config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
  service = SchemaTreeService()
  updated, errors = service.apply_operations(
    config,
    MetagitConfig,
    [ConfigOperation(op=ConfigOpKind.ENABLE, path="description")],
  )
  assert errors == []
  assert updated.description is not None


def test_set_field_updates_value() -> None:
  config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
  service = SchemaTreeService()
  updated, errors = service.apply_operations(
    config,
    MetagitConfig,
    [ConfigOperation(op=ConfigOpKind.SET, path="name", value="renamed")],
  )
  assert errors == []
  assert updated.name == "renamed"


def test_appconfig_sensitive_field_masked_in_tree() -> None:
  config = AppConfig.model_validate(
    AppConfig.model_json_schema()  # noqa: not valid — use minimal fixture
  )
```

Replace the last test with a concrete fixture:

```python
def test_appconfig_sensitive_field_masked_in_tree() -> None:
  raw = {
    "workspace": {"path": "./sync"},
    "providers": {
      "github": {"enabled": True, "api_token": "ghp_abcdefghijklmnop"},
    },
  }
  config = AppConfig(**raw)
  service = SchemaTreeService()
  tree = service.build_tree(config, AppConfig, mask_secrets=True)
  token_node = service.find_node(tree, "providers.github.api_token")
  assert token_node is not None
  assert token_node.sensitive is True
  assert token_node.value == "***mnop"
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `uv run pytest tests/core/web/test_schema_tree.py -v`  
Expected: FAIL — `SchemaTreeService` not defined

- [ ] **Step 3: Implement SchemaTreeService**

Implement `src/metagit/core/web/schema_tree.py` with:

- `SENSITIVE_KEYS = frozenset({"api_token", "token", "password", "secret"})`
- `build_tree(model_instance, model_class, *, mask_secrets=False) -> SchemaFieldNode`
- `find_node(root, path: str) -> SchemaFieldNode | None`
- `apply_operations(instance, model_class, ops) -> tuple[instance, list[dict]]`
- Path parser supporting `a.b`, `a[0].b` segments
- Walk `model_class.model_fields`; recurse into nested `BaseModel` types and `list[Model]` items using first list element template path `[*]` in tree display and numeric indices in applied paths
- `enable`: insert default via `field_info.get_default()` or `_sample_value(field_info)` helper (copy minimal logic from `ConfigExampleGenerator._sample_scalar`)
- `disable`: delete key from dict representation then re-validate
- `set`: set at path then re-validate via `model_class.model_validate(instance.model_dump(mode="json"))`
- On `ValidationError`, return `[{"path": "...", "message": "..."}]`

- [ ] **Step 4: Run tests — expect PASS**

Run: `uv run pytest tests/core/web/test_schema_tree.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/web/schema_tree.py tests/core/web/test_schema_tree.py
git commit -m "feat(web): add SchemaTreeService for config tree editing"
```

---

### Task 3: Sync job store with SSE events

**Files:**
- Create: `src/metagit/core/web/job_store.py`
- Test: `tests/core/web/test_job_store.py`

- [ ] **Step 1: Write failing test**

```python
#!/usr/bin/env python
"""Tests for sync job store."""

from metagit.core.web.job_store import SyncJobStore


def test_job_lifecycle_and_events() -> None:
  store = SyncJobStore()
  job_id = store.create_job()
  store.mark_running(job_id)
  store.append_event(job_id, {"type": "progress", "done": 1, "total": 2})
  store.complete(job_id, summary={"ok": 1}, results=[{"repo": "a"}])
  status = store.get(job_id)
  assert status is not None
  assert status.state == "completed"
  events = store.drain_events(job_id)
  assert len(events) == 1
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `uv run pytest tests/core/web/test_job_store.py -v`

- [ ] **Step 3: Implement SyncJobStore**

Thread-safe in-memory dict:

- `create_job() -> str` (uuid4 hex)
- `mark_running`, `append_event`, `complete`, `fail`
- `get(job_id) -> SyncJobStatus | None`
- `drain_events(job_id) -> list[dict]` — returns and clears pending events for SSE polling

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/web/job_store.py tests/core/web/test_job_store.py
git commit -m "feat(web): add in-memory sync job store"
```

---

### Task 4: Config HTTP handler

**Files:**
- Create: `src/metagit/core/web/config_handler.py`
- Test: `tests/core/web/test_config_handler.py`

- [ ] **Step 1: Write failing integration test**

Use `urllib.request` or `httpx` against `build_web_server` in a temp dir with minimal `.metagit.yml` and appconfig file:

```python
#!/usr/bin/env python
"""Tests for web config handler."""

import json
from http.client import HTTPConnection
from pathlib import Path

from metagit.core.web.server import build_web_server


def _write_minimal_workspace(tmp_path: Path) -> tuple[str, str]:
  definition = tmp_path / "ws"
  definition.mkdir()
  manifest = definition / ".metagit.yml"
  manifest.write_text(
    "name: demo\nkind: application\n",
    encoding="utf-8",
  )
  appconfig = tmp_path / "metagit.config.yaml"
  appconfig.write_text(
    "config:\n  workspace:\n    path: " + str(definition / "sync") + "\n",
    encoding="utf-8",
  )
  return str(definition), str(appconfig)


def test_get_metagit_config_tree(tmp_path: Path) -> None:
  root, appconfig = _write_minimal_workspace(tmp_path)
  server = build_web_server(
    root=root,
    appconfig_path=appconfig,
    host="127.0.0.1",
    port=0,
  )
  host, port = server.server_address
  try:
    conn = HTTPConnection(host, port, timeout=5)
    conn.request("GET", "/v3/config/metagit/tree")
    resp = conn.getresponse()
    assert resp.status == 200
    body = json.loads(resp.read().decode("utf-8"))
    assert body["ok"] is True
    assert body["target"] == "metagit"
    assert body["tree"]["key"] == "root"
  finally:
    server.server_close()
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `uv run pytest tests/core/web/test_config_handler.py -v`

- [ ] **Step 3: Implement config_handler + minimal server stub**

`ConfigWebHandler` class with:

- `handle(method, path, body, respond) -> bool`
- GET `/v3/config/metagit/tree` — load via `MetagitConfigManager`, build tree
- GET `/v3/config/appconfig/tree` — load via `load_config(appconfig_path)`
- PATCH same paths — parse `ConfigPatchRequest`, apply ops, optionally save
- POST `/v3/config/validate` — validate without save

Save paths:

- Metagit: `MetagitConfigManager.save_config`
- App: `save_config(appconfig_path, config)`

- [ ] **Step 4: Implement `build_web_server` skeleton in `server.py`** wiring config handler only (expand in Task 6)

- [ ] **Step 5: Run test — expect PASS**

- [ ] **Step 6: Commit**

```bash
git add src/metagit/core/web/config_handler.py src/metagit/core/web/server.py tests/core/web/test_config_handler.py
git commit -m "feat(web): add config tree HTTP handler"
```

---

### Task 5: Ops HTTP handler (sync, health, prune)

**Files:**
- Create: `src/metagit/core/web/ops_handler.py`
- Test: `tests/core/web/test_ops_handler.py`
- Modify: `src/metagit/core/web/server.py`

- [ ] **Step 1: Write failing tests**

Test health endpoint returns 200 with `ok` key using minimal workspace fixture (mock or real `WorkspaceHealthService` with empty repos).

Test prune preview returns list (empty when sync folder missing).

Test sync POST returns `job_id` and GET status eventually `completed` with `dry_run: true` (fast, no git mutation).

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement OpsWebHandler**

- POST `/v3/ops/health` — resolve workspace root from appconfig, call `WorkspaceHealthService.check`
- POST `/v3/ops/prune/preview` — body `{ "project": "..." }`; use `ProjectManager` pattern from `project_repo.py` (extract shared helper in `core/project/prune_service.py` if needed to avoid duplicating 80 lines)
- POST `/v3/ops/prune` — execute deletes when `force: true`
- POST `/v3/ops/sync` — build index rows from `WorkspaceIndexService`, spawn background thread calling `WorkspaceSyncService.sync_many`, push events to `SyncJobStore`
- GET `/v3/ops/sync/{job_id}` — status
- GET `/v3/ops/sync/{job_id}/events` — SSE: `text/event-stream`, poll store every 500ms until completed

Wire into `build_web_server`.

- [ ] **Step 4: Run tests — expect PASS**

Run: `uv run pytest tests/core/web/test_ops_handler.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/web/ops_handler.py tests/core/web/test_ops_handler.py src/metagit/core/web/server.py
git commit -m "feat(web): add workspace ops HTTP handler"
```

---

### Task 6: Static handler + full WebServer

**Files:**
- Create: `src/metagit/core/web/static_handler.py`
- Modify: `src/metagit/core/web/server.py`
- Create: `src/metagit/data/web/index.html` (placeholder until Task 8 build)

- [ ] **Step 1: Placeholder SPA**

```html
<!doctype html>
<html lang="en">
  <head><meta charset="UTF-8"><title>Metagit Web</title></head>
  <body><div id="root">Metagit Web loading…</div></body>
</html>
```

- [ ] **Step 2: Implement StaticWebHandler**

- Resolve assets from `metagit.DATA_PATH / "web"` via `importlib.resources` or existing `DATA_PATH` pattern in `metagit/__init__.py`
- GET `/` and `/assets/*`
- Fallback to `index.html` for non-API GET paths (exclude `/v1`, `/v2`, `/v3`)

- [ ] **Step 3: Complete build_web_server**

Compose handlers in order: static (GET only for non-API), v2 catalog, v2 layout, v3 config, v3 ops, 404 JSON for unknown API.

Reuse existing `CatalogApiHandler`, `LayoutApiHandler` from `core/api/`.

- [ ] **Step 4: Manual smoke**

Run: `uv run metagit web serve --root . --port 8787 --status-once` (after Task 7 registers CLI)

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/web/static_handler.py src/metagit/core/web/server.py src/metagit/data/web/index.html
git commit -m "feat(web): serve bundled SPA and compose web server"
```

---

### Task 7: CLI `metagit web serve`

**Files:**
- Create: `src/metagit/cli/commands/web.py`
- Modify: `src/metagit/cli/main.py`
- Test: `tests/cli/commands/test_web.py`

- [ ] **Step 1: Write CLI test**

```python
#!/usr/bin/env python
"""CLI tests for metagit web."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_web_serve_status_once(tmp_path: Path) -> None:
  root = tmp_path / "ws"
  root.mkdir()
  (root / ".metagit.yml").write_text("name: x\nkind: application\n", encoding="utf-8")
  appconfig = tmp_path / "metagit.config.yaml"
  appconfig.write_text(
    f"config:\n  workspace:\n    path: {tmp_path / 'sync'}\n",
    encoding="utf-8",
  )
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(appconfig),
      "web",
      "serve",
      "--root",
      str(root),
      "--status-once",
      "--port",
      "0",
    ],
  )
  assert result.exit_code == 0
  assert "web_state=ready" in result.output
```

- [ ] **Step 2: Implement web.py**

Mirror `api.py` options plus `--appconfig` override and `--open` (use `webbrowser.open`).

Echo: `web_state=ready host=... port=... url=http://...`

- [ ] **Step 3: Register in main.py**

```python
from metagit.cli.commands.web import web
# ...
cli.add_command(web)
```

- [ ] **Step 4: Run test — expect PASS**

Run: `uv run pytest tests/cli/commands/test_web.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/commands/web.py src/metagit/cli/main.py tests/cli/commands/test_web.py
git commit -m "feat(web): add metagit web serve CLI command"
```

---

### Task 8: Frontend scaffold (Vite + React)

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/index.html`
- Create: `web/src/main.tsx`, `web/src/App.tsx`, `web/src/api/client.ts`
- Modify: `Taskfile.yml` — add `web:install`, `web:build`, `web:dev`
- Modify: `.gitignore` — add `web/node_modules`, keep `src/metagit/data/web/` tracked

- [ ] **Step 1: Scaffold with npm**

```bash
cd web && npm create vite@latest . -- --template react-ts
npm install @tanstack/react-query zustand react-router-dom
```

Configure `vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "../src/metagit/data/web",
    emptyOutDir: true,
  },
});
```

- [ ] **Step 2: Add Taskfile tasks**

```yaml
  web:install:
    desc: Install web UI dependencies
    dir: web
    cmds:
      - npm ci

  web:build:
    desc: Build web UI into package data
    deps: [web:install]
    dir: web
    cmds:
      - npm run build

  web:dev:
    desc: Run Vite dev server (proxies /v3 to localhost:8787)
    dir: web
    cmds:
      - npm run dev
```

- [ ] **Step 3: API client stub**

`web/src/api/client.ts` — typed fetch wrappers for `/v3/config/*/tree`, PATCH, `/v2/workspace`, `/v3/ops/*`.

- [ ] **Step 4: Build and verify assets land in data/web**

Run: `task web:build`  
Expected: `src/metagit/data/web/index.html` and `assets/*.js` exist

- [ ] **Step 5: Commit**

```bash
git add web/ Taskfile.yml .gitignore src/metagit/data/web/
git commit -m "feat(web): scaffold Vite React frontend"
```

---

### Task 9: Config Studio UI

**Files:**
- Create: `web/src/pages/ConfigPage.tsx`
- Create: `web/src/components/SchemaTree.tsx`
- Create: `web/src/components/FieldEditor.tsx`
- Create: `web/src/theme/ThemeProvider.tsx`
- Modify: `web/src/App.tsx` — routes

- [ ] **Step 1: Theme provider**

CSS variables for light/dark in `web/src/theme/tokens.css`. Zustand store `useThemeStore` with `theme: 'light' | 'dark' | 'system'`, persist to `localStorage`.

Header toggle sun/moon icon.

- [ ] **Step 2: Schema tree component**

- Recursive render of `SchemaFieldNode`
- Checkbox on optional nodes: calls PATCH `{ op: enable|disable, path }` via TanStack Query mutation
- Disabled nodes: `opacity-0.5`, `pointer-events-none` on value editors
- Selected node highlights; click selects for editor panel

- [ ] **Step 3: Field editor**

Render by `type`: text input, number, boolean switch, enum select, nested read-only summary for objects/arrays (edit via tree children).

Save bar: Revert (refetch) + Save (PATCH with `save: true`).

Show validation errors inline per path.

- [ ] **Step 4: Routes**

- `/config/metagit`
- `/config/appconfig`

Tabs or sidebar switcher between targets.

- [ ] **Step 5: Build + manual test**

Run: `task web:build && uv run metagit web serve --root <fixture> --open`

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(web): add Config Studio UI with schema tree editing"
```

---

### Task 10: Workspace Console UI

**Files:**
- Create: `web/src/pages/WorkspacePage.tsx`
- Create: `web/src/components/RepoTable.tsx`
- Create: `web/src/components/OpsPanel.tsx`
- Create: `web/src/components/SyncDialog.tsx`

- [ ] **Step 1: Fetch workspace data**

TanStack Query: GET `/v2/workspace` — render summary chips (project count, repo count, synced vs missing).

- [ ] **Step 2: Repo table**

Expandable project rows; columns: name, status badge, path, actions.

Filter tabs: All | Synced | Missing.

Search filter client-side on repo name.

- [ ] **Step 3: Sync dialog**

Select repos or project-level "Sync all". Mode select fetch/pull/clone. Dry-run checkbox. Submit POST `/v3/ops/sync`, poll status or subscribe SSE, show progress bar.

- [ ] **Step 4: Health + prune**

- **Health:** button runs POST `/v3/ops/health`, modal with recommendations table
- **Prune:** select project → preview → confirm → execute

- [ ] **Step 5: Build + manual test**

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(web): add Workspace Console with sync health prune"
```

---

### Task 11: Documentation and ROUTER update

**Files:**
- Create: `docs/reference/metagit-web.md`
- Modify: `.mex/ROUTER.md`

- [ ] **Step 1: Write docs/reference/metagit-web.md**

Cover: purpose, `metagit web serve` flags, UI tour, dev workflow (`task web:dev`), security note (localhost).

- [ ] **Step 2: Update ROUTER.md Current Project State**

Add bullet under **Working:** for `metagit web` local UI.

- [ ] **Step 3: Commit**

```bash
git add docs/reference/metagit-web.md .mex/ROUTER.md
git commit -m "docs: add metagit web reference"
```

---

### Task 12: QA gate and CI

**Files:**
- Modify: `Taskfile.yml` or CI workflow if present
- Modify: `scripts/prepush-gate.py` if web build required

- [ ] **Step 1: Ensure web build runs before release QA**

Add `web:build` as dependency of `task qa:prepush` OR document that built assets are committed and CI verifies `index.html` exists.

Preferred: run `task web:build` in prepush when `web/` source changed (optional scope) — minimum: CI step `task web:build`.

- [ ] **Step 2: Run full QA**

Run: `task qa:prepush`  
Expected: green

- [ ] **Step 3: Final commit if any CI/taskfile changes**

```bash
git commit -m "chore: wire web build into QA gate"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| `metagit web serve` CLI | Task 7 |
| Config Studio both configs | Tasks 4, 9 |
| Enable/disable schema fields | Tasks 2, 9 |
| Light/dark mode | Task 9 |
| Workspace synced/missing browse | Task 10 |
| Sync operations + progress | Tasks 5, 10 |
| Health check | Tasks 5, 10 |
| Prune preview/execute | Tasks 5, 10 |
| Localhost security default | Task 7 (`127.0.0.1`) |
| Validation via existing managers | Tasks 2, 4 |
| Bundled SPA in package data | Tasks 6, 8 |
| Documentation | Task 11 |

## Deferred (Phase 3 — out of scope)

- Catalog add/remove in UI
- Layout rename/move in UI
- Source sync wizard

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-20-metagit-web.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration  
2. **Inline Execution** — implement tasks in this session with checkpoints

Which approach do you want?
