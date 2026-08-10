# Agent template catalog — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship ten schema-validated agent archetypes with catalog API, workspace overlays at `.metagit/.agent-templates/`, shared partials, JSON Schema generation, and a minimal Metagit Web `/agents` page.

**Architecture:** Extend Pydantic manifest models → generate JSON Schema → layered registry (bundled + `.metagit/.agent-templates/` overlay) → partial-aware renderer → templates in waves → `GET /v3/agents/*` + `AgentsPage.tsx`.

**Tech Stack:** Python 3.12, Pydantic v2, Click CLI, FastAPI-style handlers in `core/web`, existing `InitTemplateRenderer` placeholder pattern.

**Design spec:** [docs/superpowers/specs/2026-06-05-agent-template-catalog-design.md](../specs/2026-06-05-agent-template-catalog-design.md)

---

## File map

| Area | Files |
|------|-------|
| Models | `src/metagit/core/agent/models.py`, `catalog.py` (new) |
| Schema | `src/metagit/core/agent/schema_generator.py` (new) |
| Renderer | `src/metagit/core/agent/renderer.py` (new, wraps partials) |
| Registry | `src/metagit/core/agent/registry.py`, `overlay.py` (new), `service.py` |
| Overlay path | `<manifest-root>/.metagit/.agent-templates/<id>/` |
| CLI | `src/metagit/cli/commands/agent.py` |
| Web | `src/metagit/core/web/agent_handler.py`, `models.py`, `server.py` |
| Schema artifact | `schemas/agent_template.schema.json` |
| Templates | `src/metagit/data/agent-templates/<id>/` × 10 |
| Fixtures | `scripts/agent-template-fixtures.yml` |
| Tests | `tests/core/agent/*`, `tests/cli/commands/test_agent.py`, `tests/core/web/test_agent_web.py` |
| Web UI | `web/src/pages/AgentsPage.tsx`, `agentQueries.ts`, `App.tsx` route, `Layout` nav |
| Docs | `docs/reference/metagit-agent.md`, `docs/reference/metagit-web.md`, `Taskfile.yml` |

---

## Wave 0 — Schema & catalog foundation

### Task 0.1: Extend manifest models

- [ ] Add enums: `AgentArchetype`, `AgentScopeLevel`, `AgentTemplateStatus`
- [ ] Add `AgentUiSpec`, extend `AgentTemplateManifest` with catalog fields
- [ ] Add `AgentCatalogEnvelope`, `AgentCatalogEntry` (API DTOs)
- [ ] Unit test: minimal valid manifest; reject unknown `extra` keys

### Task 0.2: JSON Schema generator

- [ ] Create `schema_generator.py` using `model_json_schema()`
- [ ] CLI: `metagit agent schema --output-path ./schemas/agent_template.schema.json`
- [ ] Wire into `task generate:schema`
- [ ] Test: every field in fixture `template.yaml` validates

### Task 0.3: Overlay resolver

- [ ] `overlay.py`: `resolve_overlay_root(manifest_root) -> .metagit/.agent-templates`
- [ ] `merge_manifest(bundled, overlay) -> merged` with `source` enum
- [ ] `resolve_template_dir(id, manifest_root)` — overlay tpl files override bundled names
- [ ] Tests: bundled-only, overlay-only id, merged fields, invalid overlay rejected

### Task 0.4: Catalog service

- [ ] `AgentCatalogService.list_catalog(manifest_root=None)` — sorted by `ui.sort_order`
- [ ] `validate_all_templates()` — bundled + optional workspace overlays
- [ ] `build_delegation_index()` — populate `delegated_by` from `delegates_to`
- [ ] CLI: `metagit agent validate` ( `--root` for overlay scan)
- [ ] Update `metagit agent list --json` to catalog envelope with `source` field

### Task 0.5: Partial renderer

- [ ] `AgentTemplateRenderer` with `{{ include "name" }}` → `_partials/name.md.tpl`
- [ ] Cycle detection; max depth 3
- [ ] Tests for include resolution and missing partial error

### Task 0.6: Shared partials library

Create `src/metagit/data/agent-templates/_shared/_partials/`:

- [ ] `session-start-checklist.md.tpl`
- [ ] `guarded-sync.md.tpl`
- [ ] `manifest-validate.md.tpl`
- [ ] `cli-fallback.md.tpl`
- [ ] `output-format-health-scope.md.tpl`

### Task 0.7: Migrate orchestration-overseer

- [ ] Add `schema_version`, archetype, scope, prompt_kinds, mcp_tools, ui, delegates_to
- [ ] Refactor body to use includes (export output byte-identical or semantically equivalent)
- [ ] Run `metagit agent validate`

---

## Wave 1 — Execution & graph specialists (4 templates)

### Task 1.1: `repo-implementer`

- [ ] `template.yaml` + body emphasizing subagent-handoff, repo scope only
- [ ] `delegated_by: [orchestration-overseer]`
- [ ] Vendor tpl set (reuse skill wrapper for hermes/codex/windsurf/openclaw)
- [ ] Tests: create dry-run per vendor; preview JSON

### Task 1.2: `graph-curator`

- [ ] Body: graph-discover (report-only) + graph-maintain + ingest + group sync
- [ ] recommended_skills: graph-maintain, gitnexus
- [ ] delegates_to: []

### Task 1.3: `repo-enricher`

- [ ] Scope repo; repo-enrich prompt workflow; detect/source sync mentions
- [ ] delegated_by: [catalog-bootstrapper]

### Task 1.4: `agent-access-optimizer`

- [ ] Scope repo; agent-access skill; subagent-prompt reference
- [ ] delegated_by: [repo-implementer]

---

## Wave 2 — Workspace operations (4 templates)

### Task 2.1: `catalog-bootstrapper`

- [ ] catalog-edit, projects, bootstrap, config-refresh
- [ ] delegates_to: [repo-enricher]

### Task 2.2: `upstream-triage`

- [ ] upstream-scan/triage skills; workspace grep; health-preflight

### Task 2.3: `release-auditor`

- [ ] release-audit skill; objectives/approvals; prepush gate references

### Task 2.4: `secret-bootstrapper`

- [ ] external_skills: secretzero only; no secret values in template
- [ ] Narrow tools list in copilot/claude frontmatter

---

## Wave 3 — IaC template + API + Agents page (phase 1 complete)

### Task 3.1: `iac-coordinator`

- [ ] Fork overseer partials; add IaC doc links, platform project focus
- [ ] archetype: control_plane; distinct ui.category

### Task 3.2: Web catalog API

- [ ] Pydantic models in `web/models.py` (`source`, `overlay_path` on entries)
- [ ] `AgentWebHandler` with catalog, detail, preview routes (overlay-aware)
- [ ] Register in `build_web_server`
- [ ] Tests with httpx TestClient + overlay fixture in tmp workspace

### Task 3.3: CLI preview

- [ ] `metagit agent preview <id> [--vendor] [--answers-file] [--json]`
- [ ] Respects `.metagit/.agent-templates/` when `--root` / `-c` set

### Task 3.4: Minimal Agents page

- [ ] `web/src/api/client.ts` — types + fetch helpers for `/v3/agents/*`
- [ ] `web/src/pages/agentQueries.ts` — TanStack Query hooks
- [ ] `web/src/pages/AgentsPage.tsx` + `AgentsPage.module.css`
- [ ] Card grid by `ui.category`; badge for `source` (bundled/overlay/merged)
- [ ] Detail drawer: metadata, delegation, skills, preview tab with vendor `<select>`
- [ ] Install command copy box (read-only)
- [ ] `App.tsx` route `/agents`; nav link in `Layout`
- [ ] `task web:build`; update `docs/reference/metagit-web.md` UI tour section

### Task 3.5: QA integration

- [ ] `scripts/agent-template-fixtures.yml` + prepush step `agent_templates`
- [ ] Extend `task generate:schema`
- [ ] Update `docs/reference/metagit-agent.md` (archetypes + overlay path)
- [ ] Update `.mex/ROUTER.md`

---

## Phase 2 (deferred)

- Overlay editor in web UI (validate + save to `.metagit/.agent-templates/`)
- `POST /v3/agents/templates/{id}/install` one-click vendor install
- Richer Agent Studio (delegation graph visualization, diff bundled vs overlay)

---

## Per-template checklist (repeat for each new ID)

- [ ] `template.yaml` validates against JSON Schema
- [ ] All 8 vendors declared in `vendors:` block
- [ ] `recommended_skills` exist in `src/metagit/data/skills/`
- [ ] `prompt_kinds` exist in `prompt/catalog.py`
- [ ] `metagit agent export <id> --no-prompt` succeeds
- [ ] `metagit agent create <id> --vendor claude_code --dry-run` succeeds
- [ ] Catalog entry appears in `metagit agent list --json`

---

## Suggested commit sequence

1. `feat(agent): schema v1 models, json schema, validate command`
2. `feat(agent): partial renderer and shared partials`
3. `refactor(agent): migrate orchestration-overseer to schema v1`
4. `feat(agent): add repo-implementer, graph-curator, repo-enricher, agent-access-optimizer`
5. `feat(agent): add catalog-bootstrapper, upstream-triage, release-auditor, secret-bootstrapper`
6. `feat(agent): add iac-coordinator`
7. `feat(agent): workspace overlay resolver (.metagit/.agent-templates)`
8. `feat(web): v3 agents catalog API + Agents page`
9. `docs: agent archetype catalog, overlay path, prepush fixtures`

---

## Test commands

```bash
uv run metagit agent validate
uv run metagit agent list --json | jq '.templates | length'   # expect 10
uv run pytest tests/core/agent tests/cli/commands/test_agent.py -q
task generate:schema
task qa:prepush
```

---

## Risk notes

| Risk | Mitigation |
|------|------------|
| Template body drift across vendors | Shared `body.md.tpl` + vendor frontmatter fragments only |
| UI coupling to YAML shape | JSON Schema + Pydantic; API returns DTOs not raw YAML |
| Large prepush time | Fixture step validates manifests only, not full render × vendors |
| GitNexus index size | Templates are data, not symbols; analyze still runs at handoff |
