# RFC-0027 Component Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a longest-match path→component resolver plus `metagit component list|show|resolve`, MCP tools, and read-only web GET routes on top of the RFC-0026 catalog.

**Architecture:** New `ComponentResolver` in `metagit.core.component.resolve` is the only matching implementation. CLI, MCP, and web are thin adapters. Do not import `catalog` or `resolve` from `metagit.core.component.__init__`.

**Tech Stack:** Python 3.13, Pydantic v2, Click, pytest, existing MCP runtime and `OpsWebHandler`.

## Global Constraints

- Additive and backward compatible; manifests with no `repos[].components` keep today’s behavior (empty list, resolve unmatched).
- Do not import `catalog` or `resolve` from `metagit.core.component.__init__` (circular: config.models → ProjectPath → component package).
- `Component` is not a `ProjectPath` subclass; do not retype `paths[]`.
- Identity is always `project/repo/component`; application manifests use `config.name` twice.
- No detect/init/graph/compile/claims in this slice.
- New `src/metagit/core/component/` files: 4-space indent, `#!/usr/bin/env python` first line, `T | Exception` / `str | ValueError` unions.
- CLI component tests use **subprocess**, not CliRunner (UnifiedLogger enqueue race).
- Do not commit `.vscode/` deletions or untracked `.agents/skills/gitnexus-*` / `.claude/skills/gitnexus-*`.
- Commit on the feature branch `feat/rfc-0027-component-resolve` after each task with `feat:` (additive).

## File map

**Create**

- `src/metagit/core/component/resolve.py`
- `src/metagit/cli/commands/component.py`
- `tests/core/component/test_resolve.py`
- `tests/cli/commands/test_component_cli.py`
- `tests/core/mcp/test_component_tools.py`
- `tests/core/web/test_ops_components.py`

**Modify**

- `src/metagit/cli/main.py` — register `component_group`
- `src/metagit/core/mcp/tool_registry.py` — ACTIVE tool names
- `src/metagit/core/mcp/runtime.py` — schemas + dispatch
- `src/metagit/core/web/ops_handler.py` — GET routes
- `scripts/modality-parity.yml` — `component_resolve`
- `docs/concepts/components.md`, `docs/agents.md`, `llms.txt`, `AGENTS.md`, `CHANGELOG.md`
- `docs/superpowers/specs/2026-09-06-rfc-0026-component-context-graph-index.md`
- `.mex/ROUTER.md`, `.mex/patterns/component-model.md`

---

### Task 1: ComponentResolver

**Files:**
- Create: `src/metagit/core/component/resolve.py`
- Create: `tests/core/component/test_resolve.py`

**Interfaces:**
- Consumes: `ComponentCatalog`, `ResolvedComponent`, `parse_component_id`, `normalize_repo_relative_path`, `MetagitConfig`
- Produces: `resolved_component_payload(row) -> dict[str, Any]`; `ComponentResolver.list/get/resolve` as specified below

- [ ] **Step 1: Write the failing tests**

Create `tests/core/component/test_resolve.py` with 4-space indent. Helper to build the native-nested config:

```python
#!/usr/bin/env python
"""Tests for ComponentResolver list/get/resolve."""

from __future__ import annotations

from pathlib import Path

from metagit.core.component.models import Component
from metagit.core.component.resolve import ComponentResolver, resolved_component_payload
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _native() -> MetagitConfig:
    return MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="core",
                            path="./platform",
                            components=[
                                Component(name="web", path="apps/web", kind="application"),
                                Component(name="api", path="apps/api", kind="service"),
                                Component(name="auth", path="apps/web/packages/auth"),
                            ],
                        )
                    ],
                )
            ]
        ),
    )


def test_direct_path_match() -> None:
    row = ComponentResolver().resolve(_native(), "apps/web", project="platform", repo="core")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "web"


def test_nested_file_match() -> None:
    row = ComponentResolver().resolve(
        _native(), "apps/web/src/login.tsx", project="platform", repo="core"
    )
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "web"


def test_overlapping_paths_select_longest() -> None:
    row = ComponentResolver().resolve(
        _native(),
        "apps/web/packages/auth/src/index.ts",
        project="platform",
        repo="core",
    )
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "auth"


def test_unmatched_path_returns_none() -> None:
    row = ComponentResolver().resolve(
        _native(), "docs/readme.md", project="platform", repo="core"
    )
    assert row is None


def test_repo_without_components_returns_none() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[ProjectPath(name="core", path="./platform")],
                )
            ]
        ),
    )
    assert ComponentResolver().resolve(config, "apps/web", project="platform", repo="core") is None
    assert ComponentResolver().list(config) == []


def test_invalid_path_returns_value_error() -> None:
    result = ComponentResolver().resolve(_native(), "../escape", project="platform", repo="core")
    assert isinstance(result, ValueError)


def test_get_by_full_id() -> None:
    row = ComponentResolver().get(_native(), "platform/core/web")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.id == "platform/core/web"


def test_get_unique_bare_name() -> None:
    row = ComponentResolver().get(_native(), "api")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "api"


def test_get_ambiguous_bare_name() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="core",
                            path="./a",
                            components=[Component(name="web", path="apps/web")],
                        ),
                        ProjectPath(
                            name="edge",
                            path="./b",
                            components=[Component(name="web", path="web")],
                        ),
                    ],
                )
            ]
        ),
    )
    result = ComponentResolver().get(config, "web")
    assert isinstance(result, ValueError)
    assert "ambiguous" in str(result).lower()


def test_unscoped_relative_path_two_repos_is_ambiguous() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="core",
                            path="./a",
                            components=[Component(name="web", path="apps/web")],
                        ),
                        ProjectPath(
                            name="edge",
                            path="./b",
                            components=[Component(name="site", path="apps/web")],
                        ),
                    ],
                )
            ]
        ),
    )
    result = ComponentResolver().resolve(config, "apps/web/src/x.ts")
    assert isinstance(result, ValueError)


def test_application_paths_resolve() -> None:
    config = MetagitConfig(
        name="metagit-cli",
        kind="cli",
        paths=[ProjectPath(name="metagit-cli", path="src/metagit")],
    )
    row = ComponentResolver().resolve(config, "src/metagit/cli/main.py")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.id == "metagit-cli/metagit-cli/metagit-cli"


def test_whole_repo_dot_loses_to_nested() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="p",
                    repos=[
                        ProjectPath(
                            name="r",
                            path=".",
                            components=[
                                Component(name="root", path="."),
                                Component(name="web", path="apps/web"),
                            ],
                        )
                    ],
                )
            ]
        ),
    )
    nested = ComponentResolver().resolve(config, "apps/web/x.ts", project="p", repo="r")
    root = ComponentResolver().resolve(config, "README.md", project="p", repo="r")
    assert not isinstance(nested, Exception) and nested is not None
    assert nested.name == "web"
    assert not isinstance(root, Exception) and root is not None
    assert root.name == "root"


def test_filesystem_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "platform"
    target = repo / "apps" / "web" / "src"
    target.mkdir(parents=True)
    (target / "login.tsx").write_text("x\n", encoding="utf-8")
    config = _native()
    row = ComponentResolver().resolve(
        config,
        str(target / "login.tsx"),
        definition_root=tmp_path,
    )
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "web"


def test_payload_shape() -> None:
    row = ComponentResolver().get(_native(), "platform/core/web")
    assert row is not None and not isinstance(row, Exception)
    payload = resolved_component_payload(row)
    assert payload["id"] == "platform/core/web"
    assert payload["path"] == "apps/web"
    assert payload["source"] == "native"
    assert "spec" in payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/component/test_resolve.py -v`

Expected: FAIL collecting or importing `metagit.core.component.resolve`.

- [ ] **Step 3: Write the implementation**

Create `src/metagit/core/component/resolve.py` (4-space indent):

```python
#!/usr/bin/env python
"""Path-to-component longest-match resolver and identity lookup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metagit.core.component.catalog import ComponentCatalog, ResolvedComponent
from metagit.core.component.identity import parse_component_id
from metagit.core.component.paths import normalize_repo_relative_path
from metagit.core.config.models import MetagitConfig


def resolved_component_payload(row: ResolvedComponent) -> dict[str, Any]:
    """Stable JSON object for CLI/MCP/web adapters."""
    return {
        "id": row.id,
        "project": row.project,
        "repo": row.repo,
        "name": row.name,
        "path": row.spec.path,
        "source": row.source,
        "kind": row.spec.kind,
        "spec": row.spec.model_dump(mode="json"),
    }


def _path_rank(normalized: str) -> int:
    return 0 if normalized == "." else len(normalized.split("/"))


def _matches(query: str, component_path: str) -> bool:
    if component_path == ".":
        return True
    return query == component_path or query.startswith(component_path + "/")


class ComponentResolver:
    """List, look up, and longest-match resolve catalogued components."""

    def __init__(self, catalog: ComponentCatalog | None = None) -> None:
        self._catalog = catalog or ComponentCatalog()

    def list(
        self,
        config: MetagitConfig,
        *,
        project: str | None = None,
        repo: str | None = None,
    ) -> list[ResolvedComponent]:
        rows = self._catalog.list(config)
        if project:
            rows = [row for row in rows if row.project == project]
        if repo:
            rows = [row for row in rows if row.repo == repo]
        return rows

    def get(
        self,
        config: MetagitConfig,
        identity: str,
        *,
        project: str | None = None,
        repo: str | None = None,
    ) -> ResolvedComponent | None | ValueError:
        rows = self.list(config, project=project, repo=repo)
        parsed = parse_component_id(identity)
        if not isinstance(parsed, Exception):
            key = parsed.key
            for row in rows:
                if row.id == key:
                    return row
            return None
        name = str(identity).strip()
        if not name or "/" in name:
            return parsed if isinstance(parsed, ValueError) else ValueError(
                f"invalid component id {identity!r}; expected project/repo/component"
            )
        hits = [row for row in rows if row.name == name]
        if not hits:
            return None
        if len(hits) > 1:
            return ValueError(
                f"ambiguous component name {name!r}; use project/repo/component"
            )
        return hits[0]

    def resolve(
        self,
        config: MetagitConfig,
        path: str,
        *,
        project: str | None = None,
        repo: str | None = None,
        definition_root: str | Path | None = None,
    ) -> ResolvedComponent | None | ValueError:
        mapped = None
        if definition_root is not None:
            mapped = self._map_filesystem_path(
                config, path, definition_root=Path(definition_root)
            )
            if isinstance(mapped, Exception):
                return mapped
        query_raw = path
        scoped_project = project
        scoped_repo = repo
        if mapped is not None:
            scoped_project, scoped_repo, query_raw = mapped
        normalized = normalize_repo_relative_path(query_raw)
        if isinstance(normalized, Exception):
            return normalized
        rows = self.list(config, project=scoped_project, repo=scoped_repo)
        winners: list[ResolvedComponent] = []
        grouped: dict[tuple[str, str], list[ResolvedComponent]] = {}
        for row in rows:
            cpath = normalize_repo_relative_path(row.spec.path)
            if isinstance(cpath, Exception):
                continue
            if not _matches(normalized, cpath):
                continue
            grouped.setdefault((row.project, row.repo), []).append(row)
        for key, matches in grouped.items():
            best = max(matches, key=lambda item: _path_rank(
                str(normalize_repo_relative_path(item.spec.path))
            ))
            winners.append(best)
        if scoped_project or scoped_repo:
            return winners[0] if winners else None
        if not winners:
            return None
        if len(winners) > 1:
            return ValueError(
                "ambiguous component path; pass --project and --repo"
            )
        return winners[0]

    def _map_filesystem_path(
        self,
        config: MetagitConfig,
        path: str,
        *,
        definition_root: Path,
    ) -> tuple[str, str, str] | None | ValueError:
        candidate = Path(path).expanduser()
        abs_candidates: list[Path] = []
        if candidate.is_absolute():
            abs_candidates.append(candidate)
        else:
            cwd_try = (Path.cwd() / candidate)
            root_try = (definition_root / candidate)
            if cwd_try.exists():
                abs_candidates.append(cwd_try.resolve())
            if root_try.exists():
                abs_candidates.append(root_try.resolve())
        if not abs_candidates:
            return None
        target = abs_candidates[0]
        best: tuple[int, str, str, str] | None = None
        rows = self._catalog.list(config)
        seen: set[tuple[str, str]] = set()
        for row in rows:
            key = (row.project, row.repo)
            if key in seen:
                continue
            seen.add(key)
            repo_root = self._repo_root(config, row.project, row.repo, definition_root)
            if repo_root is None:
                continue
            try:
                rel = target.relative_to(repo_root.resolve())
            except ValueError:
                continue
            rel_text = "." if str(rel) in {"", "."} else rel.as_posix()
            rank = len(str(repo_root.resolve()).split("/"))
            if best is None or rank > best[0]:
                best = (rank, row.project, row.repo, rel_text)
        if best is None:
            return None
        return best[1], best[2], best[3]

    def _repo_root(
        self,
        config: MetagitConfig,
        project: str,
        repo: str,
        definition_root: Path,
    ) -> Path | None:
        if config.workspace is not None:
            for wsp in config.workspace.projects:
                if wsp.name != project:
                    continue
                for entry in wsp.repos:
                    if entry.name != repo:
                        continue
                    rel = entry.path or "."
                    return (definition_root / rel).resolve()
            return None
        return definition_root.resolve()
```

Fix `_path_rank` usage so we don't re-normalize in the `max` key if the stored path already normalized. Prefer storing `(rank, row)` while iterating.

Keep `get()` treating `parse_component_id` failure for names **without** `/` as a bare-name lookup (do not return the parse ValueError for `"web"`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/component/test_resolve.py tests/core/component/test_catalog.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/component/resolve.py tests/core/component/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: add component path resolver and identity lookup

Longest-match resolve plus list/get so CLI and MCP can share one catalog adapter.

EOF
)"
```

---

### Task 2: CLI `metagit component list|show|resolve`

**Files:**
- Create: `src/metagit/cli/commands/component.py`
- Create: `tests/cli/commands/test_component_cli.py`
- Modify: `src/metagit/cli/main.py` (import `component_group` from `metagit.cli.commands.component` and `cli.add_command(component_group)`)

**Interfaces:**
- Consumes: `ComponentResolver`, `resolved_component_payload`, `MetagitConfigManager`, `resolve_definition_root`, `emit_json`
- Produces: Click group `component` with `list`, `show`, `resolve`

- [ ] **Step 1: Write failing CLI tests (subprocess)**

Create `tests/cli/commands/test_component_cli.py`. Fixture: `tests/fixtures/components/native-nested.yml`. Invoke `[sys.executable, "-m", "metagit.cli.main", "component", ...]`.

Cover:

1. `list -c fixture --json` includes `platform/core/web` and `platform/core/api`
2. `show platform/core/web -c fixture --json` has `"name": "web"`
3. `resolve apps/web/src/login.tsx -c fixture --project platform --repo core --json` has `matched true` and `name web`
4. `resolve docs/nope.md -c fixture --project platform --repo core --json` has `matched false` and non-zero exit
5. `list -c tests/fixtures/components/no-components.yml --json` has `"components": []` and exit 0

- [ ] **Step 2: Run tests — expect FAIL** (`No such command 'component'`)

- [ ] **Step 3: Implement the Click group**

Follow `src/metagit/cli/commands/atlas.py` (group + `--json`) and `context.py` `_load_manifest`.

```python
#!/usr/bin/env python
"""CLI for component catalog list/show/resolve (RFC-0027)."""
```

- `@click.group(name="component")` with `@click.option("--config-path", "-c", "config_path", default=None)` and `@click.pass_context`.
- Resolve manifest path: if `config_path` is None, use `ctx.obj.get("definition_path")` if set, else `.metagit.yml`. Store on `ctx.obj["component_manifest"]`.
- Load config with `MetagitConfigManager`; `ClickException` on load error.
- `definition_root = resolve_definition_root(manifest_path)`.
- `list`: optional `--project`, `--repo`, `--json`. JSON: `emit_json({"components": [resolved_component_payload(r) for r in rows]})`. Human: `{id}\t{path}\t{kind or -}`.
- `show`: argument `identity`. On `ValueError` raise `ClickException`. On `None` echo `component not found: {identity}` to stderr and `raise SystemExit(1)`. JSON: `emit_json(payload)`.
- `resolve`: argument `path`. Pass `definition_root`. On `ValueError` raise `ClickException`. Build `{"matched": bool, "path": path, **payload_if_match}`. JSON via `emit_json`. Human match: `{id}\t{path}`. Human miss: stderr `no component matched: {path}` and exit 1. JSON miss also exit 1.

Register in `main.py` next to other groups (`cli.add_command(component_group)`).

- [ ] **Step 4: Run CLI tests — expect PASS**

`uv run pytest tests/cli/commands/test_component_cli.py -v`

- [ ] **Step 5: Commit** `feat: add metagit component list/show/resolve CLI`

---

### Task 3: MCP tools

**Files:**
- Create: `tests/core/mcp/test_component_tools.py`
- Modify: `src/metagit/core/mcp/tool_registry.py` — add `metagit_component_list`, `metagit_component_show`, `metagit_component_resolve` to the ACTIVE list (near other `metagit_*` workspace tools)
- Modify: `src/metagit/core/mcp/runtime.py` — `_tool_schemas` entries with `additionalProperties: false`; dispatch branch that instantiates `ComponentResolver` and uses `status.root_path` as `definition_root`

**Interfaces:**
- Consumes: `ComponentResolver`, `resolved_component_payload`
- Produces: three ACTIVE tools

Schemas:

- `metagit_component_list`: optional `project`, `repo` strings
- `metagit_component_show`: required `component`; optional `project`, `repo`
- `metagit_component_resolve`: required `path`; optional `project`, `repo`

Dispatch (ACTIVE + config required, else `InvalidToolArgumentsError`):

- list → `{"components": [...]}`
- show → payload dict; `None` or `ValueError` → `InvalidToolArgumentsError`
- resolve → `{matched, path, ...}` including `matched: false` as a normal result (not protocol error). `ValueError` → `InvalidToolArgumentsError`

Tests: copy the pattern in `tests/core/mcp/test_aos_tools.py` (`MetagitMcpRuntime(root=...)`, `tools/list`, `tools/call`). Seed a workspace `.metagit.yml` with nested components like the native-nested fixture. Assert list contains `platform/core/web`, show returns it, resolve `apps/web/src/login.tsx` with project/repo matches web.

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Run — expect FAIL** (tools missing)
- [ ] **Step 3: Implement schemas + registry + dispatch**
- [ ] **Step 4: Run `uv run pytest tests/core/mcp/test_component_tools.py -v` — PASS**
- [ ] **Step 5: Commit** `feat: add MCP component list/show/resolve tools`

---

### Task 4: Web GET, docs, modality, scaffold

**Files:**
- Create: `tests/core/web/test_ops_components.py`
- Modify: `src/metagit/core/web/ops_handler.py`
- Modify: `scripts/modality-parity.yml` (new `component_resolve` id)
- Modify: `docs/concepts/components.md`, `docs/agents.md`, `llms.txt`, `AGENTS.md`, `CHANGELOG.md` Unreleased
- Modify: series index status for 0027
- Modify: `.mex/ROUTER.md`, `.mex/patterns/component-model.md`, `.mex/patterns/INDEX.md` if needed
- Run: `task generate:modality-registry` (or `task generate:schema` if that also refreshes the registry)

**Interfaces:**
- Consumes: `ComponentResolver` (same payloads as MCP)
- Produces: GET `/v3/ops/components`, GET `/v3/ops/components/resolve`

- [ ] **Step 1: Failing web tests** using `_start_server` pattern from `tests/core/web/test_ops_handler.py`. Write a `.metagit.yml` with `workspace.projects[platform].repos[core].components[web, api]`. `urllib.request` GET `/v3/ops/components` → 200 with web id. GET `/v3/ops/components/resolve?path=apps/web/src/x.tsx&project=platform&repo=core` → `matched true`. Missing `path` → 400.

- [ ] **Step 2: Implement handler methods.** In `handle()`, add routes **before** generic prefixes that could swallow them. Parse query with existing `parse_qs`. 400 on `ValueError`. 200 on unmatched resolve with `matched: false`.

- [ ] **Step 3: Docs + modality**

`scripts/modality-parity.yml` new entry:

```yaml
  - id: component_resolve
    description: Component catalog list/show and path-to-component resolve
    service: metagit.core.component.resolve.ComponentResolver
    reference_doc: docs/concepts/components.md
    surfaces:
      cli:
        markers:
          - path: src/metagit/cli/commands/component.py
            contains: "component resolve"
      mcp:
        markers:
          - path: src/metagit/core/mcp/runtime.py
            contains: metagit_component_resolve
      web:
        markers:
          - path: src/metagit/core/web/ops_handler.py
            contains: /v3/ops/components
      documentation:
        markers:
          - path: docs/concepts/components.md
            contains: "modality:component_resolve"
          - path: docs/agents.md
            contains: "modality:component_resolve"
```

Add `<!-- modality:component_resolve -->` near the CLI section in `docs/concepts/components.md` (keep `component_model` on the intro). Document `list`/`show`/`resolve` and MCP tool names. Remove those three commands from “Not in this release”. Leave detect/init/graph/compile there.

CHANGELOG Unreleased Added: component list/show/resolve + MCP + GET `/v3/ops/components`.

AGENTS.md / llms.txt / docs/agents.md: `metagit component list|show|resolve`.

Series index: 0027 design + plan links; status Implemented after tests pass.

`.mex/ROUTER.md`: RFC-0027 shipped; next is 0028. Update `component-model.md` gotcha: resolver lives in `resolve.py`; CLI subprocess tests.

- [ ] **Step 4: `task generate:modality-registry` then `uv run pytest tests/core/web/test_ops_components.py tests/cli/commands/test_component_cli.py tests/core/component/test_resolve.py tests/core/mcp/test_component_tools.py -v`**

- [ ] **Step 5: Commit** `feat: expose component resolve on web and document RFC-0027`

---

## Spec coverage

| Spec requirement | Task |
|------------------|------|
| Longest-match resolve | 1 |
| list/get | 1 |
| Filesystem mapping | 1 |
| Ambiguous name/path | 1 |
| CLI | 2 |
| MCP | 3 |
| Web GET | 4 |
| Docs + modality + ROUTER | 4 |
| No detect/graph/compile | all (omitted) |
