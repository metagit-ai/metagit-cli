# RFC-0028–0032 Remaining Series Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the Component Context Graph series on `feat/rfc-0027-component-resolve`: graph endpoints + neighborhood, compile `--component`, claims, detect/init, and derived component selections — then merge.

**Architecture:** Each slice adds one core service (or extends one existing service). CLI, MCP, and web are thin adapters. Never import `catalog`, `resolve`, `graph`, or `detect` from `metagit.core.component.__init__`.

**Tech Stack:** Python 3.13, Pydantic v2, Click, pytest, existing MCP runtime and `OpsWebHandler`.

## Global Constraints

- Additive and backward compatible; manifests with no `repos[].components` keep today’s behavior.
- Do not import catalog/resolve/graph/detect from `metagit.core.component.__init__` (circular: `config.models` → `ProjectPath` → package).
- `Component` is not a `ProjectPath` subclass; do not retype `paths[]`.
- Identity is always `project/repo/component`.
- No monorepo mode. No LLM discovery.
- New `src/metagit/core/component/` files: 4-space indent, `#!/usr/bin/env python` first line.
- CLI `component` tests use **subprocess**, not CliRunner.
- Do not commit `.vscode/` deletions or untracked `.agents/skills/gitnexus-*` / `.claude/skills/gitnexus-*` / `CLAUDE.md`.
- Commit on `feat/rfc-0027-component-resolve` after each task with `feat:` (additive) or `fix:` (behavior corrections).
- Follow designs:
  - `docs/superpowers/specs/2026-09-06-rfc-0028-component-graph-design.md`
  - `docs/superpowers/specs/2026-09-06-rfc-0029-component-compile-design.md`
  - `docs/superpowers/specs/2026-09-06-rfc-0030-component-ownership-design.md`
  - `docs/superpowers/specs/2026-09-06-rfc-0031-component-discovery-design.md`
  - `docs/superpowers/specs/2026-09-06-rfc-0032-derived-components-design.md`
- After each RFC: update `CHANGELOG.md` Unreleased, `docs/concepts/components.md`, series index, `.mex/ROUTER.md`, modality-parity.yml (run `uv run python scripts/generate_modality_registry.py` or the project generate task), `llms.txt` / `AGENTS.md` as needed.
- Register more-specific HTTP paths (`/graph`, `/detect`, `/resolve`) **before** `/v3/ops/components`.

## File map (series)

**Create**

- `src/metagit/core/component/graph.py`
- `src/metagit/core/component/detect.py`
- `tests/core/component/test_graph.py`
- `tests/core/component/test_detect.py`
- `.mex/patterns/component-graph.md`

**Modify (across tasks)**

- `src/metagit/core/config/graph_models.py`, `graph_validation.py`, `graph_resolver.py`, `graph_cypher_export.py`
- `src/metagit/cli/commands/component.py`, `context.py`, `claim.py`, `project_derived.py`
- `src/metagit/core/mcp/runtime.py`, `tool_registry.py`
- `src/metagit/core/web/ops_handler.py`
- `src/metagit/core/context/compiler.py`, `models.py`
- `src/metagit/core/agent/profile_service.py`
- `src/metagit/core/workspace/agent_profile_models.py`
- `src/metagit/core/coordination/models.py`, `claim_service.py`
- `src/metagit/core/workspace/models.py`, `derived_project_service.py`
- `scripts/modality-parity.yml`, docs, CHANGELOG, series index

---

### Task 1: GraphEndpoint.component + validation + resolver ids (RFC-0028)

**Files:**
- Modify: `src/metagit/core/config/graph_models.py`
- Modify: `src/metagit/core/config/graph_validation.py`
- Modify: `src/metagit/core/config/graph_resolver.py`
- Modify: `tests/core/config/test_graph_validation.py`
- Test: `tests/core/config/test_graph_resolver.py` (create if missing)

**Interfaces:**
- Consumes: `ComponentCatalog` / `ComponentResolver.get` for existence
- Produces: `GraphEndpoint.component: str | None`; `resolve_graph_endpoint_id` → `component:{project}/{repo}/{name}` when component set

- [ ] **Step 1: Write failing tests** for: YAML round-trip `component`; validate error when component without project+repo; unknown component name; path-only still valid; resolver returns `component:platform/core/web`.

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/core/config/test_graph_validation.py tests/core/config/test_graph_resolver.py -q
```

- [ ] **Step 3: Implement** `component` field; in `_validate_endpoint`, if `endpoint.component`: require project and repo, then `ComponentResolver().get(config, f"{project}/{repo}/{component}")` must not be None/ValueError. Resolver: if component set, require project+repo and return `component:{project}/{repo}/{component}` (do not require index rows).

- [ ] **Step 4: Tests PASS. Commit** `feat: add GraphEndpoint.component and catalog validation`

---

### Task 2: ComponentGraphService neighborhood (RFC-0028)

**Files:**
- Create: `src/metagit/core/component/graph.py`
- Create: `tests/core/component/test_graph.py`

**Interfaces:**
- Produces:

```python
def neighborhood(
    self,
    config: MetagitConfig,
    identity: str,
    *,
    project: str | None = None,
    repo: str | None = None,
    depth: int = 1,
    direction: Literal["out", "in", "both"] = "out",
    types: list[str] | None = None,
) -> dict[str, Any] | None | ValueError
```

Payload as RFC-0028 JSON. Use `resolved_component_payload` for nodes. Cap depth at 5. Negative depth is `ValueError`.

- [ ] **Step 1: Failing tests** using the same native config as `tests/core/component/test_resolve.py` (`web` depends_on `api`):
  - depth 0: one node, no edges
  - depth 1 out: web + api, depends_on edge origin `depends_on`
  - declared graph.relationships origin `declared` wins on duplicate
  - path-based declared edge resolves via ComponentResolver
  - unknown identity None; ambiguous bare name ValueError
  - direction `in` from api includes web

- [ ] **Step 2: Implement graph.py. Tests PASS. Commit** `feat: walk component graph neighborhoods`

---

### Task 3: Cypher component nodes + CLI/MCP/web graph (RFC-0028)

**Files:**
- Modify: `src/metagit/core/config/graph_cypher_export.py` (`GraphCypherNode.kind` include `"component"`)
- Modify: `src/metagit/cli/commands/component.py`
- Modify: `src/metagit/core/mcp/runtime.py`, `tool_registry.py`
- Modify: `src/metagit/core/web/ops_handler.py`
- Modify: `scripts/modality-parity.yml`
- Test: `tests/cli/commands/test_component_cli.py`, `tests/core/mcp/test_component_tools.py`, `tests/core/web/test_ops_components.py`, cypher tests
- Docs: `docs/concepts/components.md`, CHANGELOG, series index, `.mex/patterns/component-graph.md`, `.mex/patterns/INDEX.md`

**CLI:** `component graph IDENTITY` with `--depth` default 1, `--direction` default out, `--json`, `-c`. Human: `{id}` lines then `from --type--> to`. Not found exit 1.

**MCP:** ACTIVE `metagit_component_graph`. Not found `-32602`. ValueError `-32602`.

**Web:** GET `/v3/ops/components/graph` registered before `/components`. 404 not found, 400 ValueError.

- [ ] **Implement + tests + modality registry. Commit** `feat: expose component graph via CLI MCP and web`

---

### Task 4: Agent profile component layer (RFC-0029)

**Files:**
- Modify: `src/metagit/core/workspace/agent_profile_models.py`
- Modify: `src/metagit/core/agent/profile_service.py`
- Test: `tests/core/agent/test_agent_profile_service.py`

**Interfaces:**
- `AgentProfileLayer.scope` includes `"component"`
- `EffectiveAgentProfile.component_name: str | None = None`
- Add `effective_profile(..., component_name: str | None = None)` merging component profile after repo when name is set and found on `repo.components`.

- [ ] **Tests:** inherit skills from component; `inherit: false` replaces. **Commit** `feat: merge agent_profile at component scope`

---

### Task 5: context compile --component --depth (RFC-0029)

**Files:**
- Modify: `src/metagit/core/context/models.py`, `compiler.py`
- Modify: `src/metagit/cli/commands/context.py`
- Modify: MCP `metagit_context_compile` schema + handler
- Test: `tests/core/context/test_compiler.py`, CLI context tests

**Interfaces:**
- `CompiledContextInputs.component`, `.depth`
- `CompiledContext.component` optional payload, `.component_graph` optional neighborhood dict
- `compile(..., component: str | None = None, depth: int = 0)`
- Resolve component with `ComponentResolver.get` after `_resolve_scope`. Disagreement with three-segment id → Exception.
- When component set, call `ComponentGraphService.neighborhood` at `depth`.

- [ ] **Tests as design. Commit** `feat: compile context for a component neighborhood`

---

### Task 6: Component claims (RFC-0030)

**Files:**
- Modify: `src/metagit/core/coordination/models.py`, `claim_service.py`
- Modify: `src/metagit/cli/commands/claim.py`
- Modify: MCP claim declare/check
- Test: `tests/core/coordination/test_coordination_services.py` (and CLI claim tests if present)

**Interfaces:**
- `FileClaim.component: str | None = None`
- `declare(..., component: str | None = None, config: MetagitConfig | None = None)`
- When component set, repository must parse as `project/repo` (`parse_component_id(f"{repository}/{component}")` or split repository on `/` into two segments). Expand empty patterns to `{path}/**` or `**`.

Pass config from CLI after loading manifest (`-c` already common). If config missing when component set → error.

- [ ] **Tests as design. Commit** `feat: claim catalogued components without whole-repo globs`

---

### Task 7: Component detect + init (RFC-0031)

**Files:**
- Create: `src/metagit/core/component/detect.py`, `tests/core/component/test_detect.py`
- Modify: `component.py` CLI, MCP, ops_handler, modality-parity
- Fixture: tmp_path trees in tests (do not require committed fixture repos)

**Interfaces:**

```python
class ComponentDetector:
    def detect(self, config, *, project=None, repo=None, definition_root: str) -> dict
    def apply_candidates(self, config, candidates, *, config_path: str) -> MetagitConfig | Exception
    def init_component(self, config, path: str, *, name=None, kind=None, project=None, repo=None) -> Component | ValueError
```

Detect scans checkout; init builds one Component. Apply writes via MetagitConfigManager.save.

- [ ] **Tests as design. Commit** `feat: detect and init repository components`

---

### Task 8: Derived project/repo/component selections (RFC-0032)

**Files:**
- Modify: `src/metagit/core/workspace/models.py` (`DerivedSourceScope.components`)
- Modify: `src/metagit/core/workspace/derived_project_service.py`
- Modify: CLI `project_derived.py`, MCP derived create/include
- Test: `tests/core/workspace/test_derived_project_service.py`

**Interfaces:**
- `parse_selection` → object with `project`, `repo`, `component: str | None`
- Copy `components` on repo-wide derived; filter to one component for three-segment
- `--include-dependencies` on create

- [ ] **Tests as design. Commit** `feat: derive working sets from component graph selections`

---

### Task 9: Series closeout docs + schema

**Files:** series index, `docs/concepts/components.md`, `docs/agents.md`, `llms.txt`, `AGENTS.md`, `.mex/ROUTER.md`, `CHANGELOG.md`, `task generate:schema` / `uv run` schema generator, modality registry

- [ ] Tick definition-of-done in the series index that this branch covers.
- [ ] Commit `docs: complete RFC-0028–0032 component series closeout`
