# Provider Source Import — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance `metagit project source sync` with filters, idempotent `--ensure`, provider topic enrichment, JSON output, MCP exposure, and declarative `workspace.projects[].sources[]` with approval-gated reconcile removals.

**Architecture:** Extend `SourceSpec` / `SourceSyncService` with a dedicated filter + naming + enrichment pipeline; keep CLI thin. Phase 3 adds `ProjectSource` on `WorkspaceProject` and `source_id` on `ProjectPath`; manifest sync orchestrates per-source plans with partial apply (adds/updates now, removals via `ApprovalService` unless `--force`).

**Tech Stack:** Python 3.12, Pydantic v2, Click, `requests`, existing `ProviderRegistry`, `ApprovalService`, pytest.

**Design spec:** [docs/superpowers/specs/2026-06-11-provider-source-import-design.md](../specs/2026-06-11-provider-source-import-design.md)

---

## File map

| Area | Files |
|------|-------|
| Models | `src/metagit/core/project/source_models.py`, `source_models.py` (`SourceSyncResult`) |
| Filters | `src/metagit/core/project/source_filters.py` (new) |
| Naming | `src/metagit/core/project/source_naming.py` (new) |
| Enrichment | `src/metagit/core/project/source_enrichment.py` (new) |
| Core sync | `src/metagit/core/project/source_sync.py` |
| Manifest sync | `src/metagit/core/project/source_manifest_sync.py` (new, phase 3) |
| Approval executor | `src/metagit/core/project/source_approval_executor.py` (new, phase 3) |
| Workspace schema | `src/metagit/core/workspace/models.py`, `src/metagit/core/project/models.py` |
| CLI | `src/metagit/cli/commands/project_source.py`, `project.py` (`--refresh-sources`) |
| MCP | `src/metagit/core/mcp/services/source_sync.py` (new), `runtime.py` |
| Schema | `schemas/metagit_config.schema.json` (via `task generate:schema`) |
| Fixtures | `scripts/manifest-fixtures.yml`, `examples/` sample snippet |
| Tests | `tests/core/project/test_source_*.py`, `tests/test_project_source_sync.py`, `tests/cli/commands/test_project_source.py`, `tests/core/mcp/test_runtime.py`, `tests/core/project/test_source_manifest_sync.py` |
| Docs | `docs/development.md`, `CHANGELOG.md`, bundled skills, `.mex/ROUTER.md`, `src/metagit/core/prompt/catalog.py` |

**GitNexus:** Run `gitnexus_impact` on `SourceSyncService`, `SourceSpec`, `WorkspaceProject`, `ProjectPath` before editing.

---

## PR 1 — Phase 1: Imperative sync enhancements

Ship a self-contained, backward-compatible enhancement to `metagit project source sync`. No `.metagit.yml` schema changes in this PR.

### Task 1.1: Extend `SourceSpec` and result models

**Files:**
- Modify: `src/metagit/core/project/source_models.py`
- Modify: `tests/test_project_source_models.py`

- [ ] **Step 1: Write failing tests for new fields**

```python
# tests/test_project_source_models.py

def test_source_spec_accepts_filter_fields() -> None:
  spec = SourceSpec(
    provider=SourceProvider.GITHUB,
    org="acme",
    include_patterns=["acme/platform-*"],
    ignore_patterns=["**/deprecated/**"],
    visibility="private",
    name_strategy="namespaced",
    ensure=True,
    refresh_metadata=False,
    enrich_topics=True,
  )
  assert spec.ensure is True
  assert spec.name_strategy == "namespaced"


def test_source_spec_visibility_invalid_raises() -> None:
  with pytest.raises(ValidationError):
    SourceSpec(provider=SourceProvider.GITHUB, org="acme", visibility="secret")
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `uv run pytest tests/test_project_source_models.py -v`

- [ ] **Step 3: Add fields to `SourceSpec`**

```python
from typing import Literal

include_patterns: list[str] = Field(default_factory=list)
ignore_patterns: list[str] = Field(default_factory=list)
ignore_languages: list[str] = Field(default_factory=list)
visibility: Literal["any", "public", "private", "internal"] = "any"
name_strategy: Literal["short", "namespaced"] = "namespaced"
ensure: bool = False
refresh_metadata: bool = False
enrich_topics: bool = True
source_id: str | None = None  # used in phase 3; harmless now
```

Add `SourceSyncResult` pydantic model for `--json` output (`ok`, `applied`, `spec`, `plan`, `errors`).

- [ ] **Step 4: Run tests — expect PASS**

Run: `uv run pytest tests/test_project_source_models.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/project/source_models.py tests/test_project_source_models.py
git commit -m "fix: extend SourceSpec with filter and idempotency fields"
```

### Task 1.2: Filter pipeline module

**Files:**
- Create: `src/metagit/core/project/source_filters.py`
- Create: `tests/core/project/test_source_filters.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/core/project/test_source_filters.py

def _repo(full_name: str, *, archived=False, fork=False, private=None, language=None):
  return DiscoveredRepo(
    provider=SourceProvider.GITLAB,
    namespace="acme",
    full_name=full_name,
    name=full_name.split("/")[-1],
    clone_url=f"https://example.com/{full_name}.git",
    archived=archived,
    fork=fork,
    private=private,
    language=language,
  )


def test_ignore_pattern_drops_match() -> None:
  spec = SourceSpec(provider=SourceProvider.GITLAB, group="acme", ignore_patterns=["**/deprecated/**"])
  repos = [_repo("acme/good"), _repo("acme/deprecated/old")]
  filtered = apply_source_filters(spec, repos)
  assert [r.full_name for r in filtered] == ["acme/good"]


def test_include_pattern_allowlist() -> None:
  spec = SourceSpec(
    provider=SourceProvider.GITHUB,
    org="acme",
    include_patterns=["acme/platform-*"],
  )
  repos = [_repo("acme/platform-api"), _repo("acme/other")]
  filtered = apply_source_filters(spec, repos)
  assert len(filtered) == 1
  assert filtered[0].full_name == "acme/platform-api"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/core/project/test_source_filters.py -v`

- [ ] **Step 3: Implement `apply_source_filters`**

```python
# src/metagit/core/project/source_filters.py
import fnmatch

def apply_source_filters(spec: SourceSpec, repos: list[DiscoveredRepo]) -> list[DiscoveredRepo]:
  result = list(repos)
  if spec.include_patterns:
    result = [r for r in result if any(fnmatch.fnmatch(r.full_name, p) for p in spec.include_patterns)]
  if spec.ignore_patterns:
    result = [r for r in result if not any(fnmatch.fnmatch(r.full_name, p) for p in spec.ignore_patterns)]
  if not spec.include_archived:
    result = [r for r in result if not r.archived]
  if not spec.include_forks:
    result = [r for r in result if not r.fork]
  if spec.path_prefix:
    result = [r for r in result if r.full_name.startswith(spec.path_prefix)]
  if spec.visibility != "any":
    result = [r for r in result if _visibility_matches(r, spec.visibility)]
  if spec.ignore_languages:
    blocked = {lang.lower() for lang in spec.ignore_languages}
    result = [r for r in result if (r.language or "").lower() not in blocked]
  return result
```

Add optional `language: str | None = None` on `DiscoveredRepo`.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

### Task 1.3: Namespaced naming resolver

**Files:**
- Create: `src/metagit/core/project/source_naming.py`
- Create: `tests/core/project/test_source_naming.py`

- [ ] **Step 1: Write failing collision tests**

```python
def test_namespaced_collision_uses_parent_segment() -> None:
  repos = [
    DiscoveredRepo(provider=SourceProvider.GITLAB, namespace="g", full_name="acme/a/foo", name="foo", clone_url="u1"),
    DiscoveredRepo(provider=SourceProvider.GITLAB, namespace="g", full_name="acme/b/foo", name="foo", clone_url="u2"),
  ]
  names = resolve_manifest_names(repos, strategy="namespaced")
  assert names["u1"] == "foo"
  assert names["u2"] == "b-foo"  # or a-foo / platform-api per spec: last-two segments


def test_short_strategy_uses_repo_name() -> None:
  repos = [DiscoveredRepo(provider=SourceProvider.GITHUB, namespace="o", full_name="o/r", name="r", clone_url="u")]
  assert resolve_manifest_names(repos, strategy="short")["u"] == "r"
```

- [ ] **Step 2–4: Implement `resolve_manifest_names(repos, strategy) -> dict[str, str]`** keyed by clone_url; collision algorithm per spec (last segment → join last two → numeric suffix).

- [ ] **Step 5: Commit**

### Task 1.4: Topic enrichment module

**Files:**
- Create: `src/metagit/core/project/source_enrichment.py`
- Create: `tests/core/project/test_source_enrichment.py`

- [ ] **Step 1: Write failing tag merge test**

```python
def test_merge_tags_preserves_user_keys() -> None:
  existing = {"owner": "platform", "custom": "keep"}
  incoming = {"source": "github", "python": "topic", "custom": "topic"}
  merged = merge_repo_tags(existing, incoming, refresh_metadata=False)
  assert merged["custom"] == "keep"
  assert merged["python"] == "topic"
  assert merged["source"] == "github"


def test_refresh_metadata_overwrites_topic_values() -> None:
  existing = {"python": "old"}
  incoming = {"python": "topic"}
  merged = merge_repo_tags(existing, incoming, refresh_metadata=True)
  assert merged["python"] == "topic"
```

- [ ] **Step 2–4: Implement `merge_repo_tags` and `enrich_discovered_repos(spec, repos, registry, logger)`** using `ProviderRegistry.get_provider_by_name` + `get_repository_metadata` when `enrich_topics` and count ≤ 100 (or `refresh_metadata`). Populate `DiscoveredRepo.language` and a new `topics: list[str]` field on `DiscoveredRepo`.

- [ ] **Step 5: Commit**

### Task 1.5: Wire pipeline into `SourceSyncService`

**Files:**
- Modify: `src/metagit/core/project/source_sync.py`
- Modify: `tests/test_project_source_sync.py`

- [ ] **Step 1: Write failing ensure-mode test**

```python
def test_plan_ensure_skips_metadata_update() -> None:
  service = _service()
  spec = SourceSpec(provider=SourceProvider.GITHUB, org="acme", ensure=True)
  project = WorkspaceProject(
    name="default",
    repos=[
      ProjectPath(
        name="svc",
        url="https://github.com/acme/svc.git",
        description="old",
        source_provider="github",
        source_namespace="acme",
        source_repo_id="1",
      )
    ],
  )
  discovered = [
    DiscoveredRepo(
      provider=SourceProvider.GITHUB,
      namespace="acme",
      full_name="acme/svc",
      name="svc",
      clone_url="https://github.com/acme/svc.git",
      description="new",
      repo_id="1",
    )
  ]
  plan = service.plan(spec, project, discovered, SourceSyncMode.ADDITIVE)
  assert plan.to_update == []
  assert plan.unchanged == 1


def test_plan_ensure_refresh_metadata_updates() -> None:
  spec = SourceSpec(provider=SourceProvider.GITHUB, org="acme", ensure=True, refresh_metadata=True)
  # same fixture — expect len(plan.to_update) == 1
```

- [ ] **Step 2: Refactor `discover()` return path**

After provider HTTP loop, call:
1. `apply_source_filters(spec, discovered)`
2. `enrich_discovered_repos(...)` when configured
3. Attach resolved names via `resolve_manifest_names`

- [ ] **Step 3: Update `_to_project_path`** to use resolved name, merge tags from topics, set `language`.

- [ ] **Step 4: Extend `_needs_update`** to compare tags dict and language.

- [ ] **Step 5: Extend `plan()`** with ensure/refresh_metadata logic.

- [ ] **Step 6: Run full source sync tests**

Run: `uv run pytest tests/test_project_source_sync.py tests/core/project/ -v`

- [ ] **Step 7: Commit**

### Task 1.6: CLI flags and `--json`

**Files:**
- Modify: `src/metagit/cli/commands/project_source.py`
- Modify: `tests/cli/commands/test_project_source.py`

- [ ] **Step 1: Add Click options** — `multiple=True` for `--include-pattern` / `--ignore`; booleans for `--ensure`, `--refresh-metadata`, `--no-enrich-topics`; `--name-strategy`; `--json`.

- [ ] **Step 2: Build `SourceSpec` from options**

- [ ] **Step 3: When `--json`**, print `SourceSyncResult.model_dump_json(indent=2)` to stdout; logs to stderr via logger.

- [ ] **Step 4: Write CLI test** asserting JSON contains `plan.discovered_count` keys on dry-run.

Run: `uv run pytest tests/cli/commands/test_project_source.py -v`

- [ ] **Step 5: Commit**

### Task 1.7: Phase 1 docs and QA

**Files:**
- Modify: `docs/development.md`, `CHANGELOG.md`, `skills/metagit-cli/SKILL.md`, `src/metagit/data/skills/metagit-cli/SKILL.md`, `.mex/ROUTER.md`, `src/metagit/core/prompt/catalog.py`

- [ ] Document idempotency table (option C), filter flags, GitHub recursive no-op, namespaced default
- [ ] Run: `task qa:prepush`
- [ ] Run: `task gitnexus:analyze`
- [ ] Commit docs/changelog

**PR 1 merge criteria:** All phase 1 success criteria in spec pass; no schema change.

---

## PR 2 — Phase 2: MCP, alias, post-apply sync

### Task 2.1: MCP service handler

**Files:**
- Create: `src/metagit/core/mcp/services/source_sync.py`
- Modify: `src/metagit/core/mcp/runtime.py`
- Modify: `tests/core/mcp/test_runtime.py`

- [ ] **Step 1: Add `SourceSyncMcpService.run(params) -> SourceSyncResult`** — parse params into `SourceSpec`, load project from gate context, call `SourceSyncService`, optional `apply` + `confirm` (maps to `--yes` for imperative reconcile only).

- [ ] **Step 2: Register tool schema** `metagit_project_source_sync` in `runtime.py` `_tool_schemas` and dispatch in `_handle_tools_call`.

- [ ] **Step 3: Test** tool listed in ACTIVE state; dry-run returns JSON plan; reconcile without `confirm` returns error.

Run: `uv run pytest tests/core/mcp/test_runtime.py -k source_sync -v`

- [ ] **Step 4: Commit**

### Task 2.2: `--sync` post-apply flag

**Files:**
- Modify: `src/metagit/cli/commands/project_source.py`
- Modify: `tests/cli/commands/test_project_source.py`

- [ ] After successful manifest save with `--apply`, when `--sync`, invoke `ProjectManager.sync(project)` (monkeypatch in test).

- [ ] **Commit**

### Task 2.3: Optional `workspace import` alias

**Files:**
- Modify: `src/metagit/cli/commands/workspace.py` (or new `workspace_import.py` registered in main)

- [ ] **Add group command** `metagit workspace import` forwarding to `source sync` with defaults: `--mode additive --ensure --json` plus required `--project` and provider scope flags.

- [ ] **Test** `--help` and one invoke with monkeypatched service.

- [ ] **Commit**

### Task 2.4: Phase 2 docs + QA

- [ ] Update `docs/agents.md` MCP tool table
- [ ] `task qa:prepush` + `task gitnexus:analyze`

---

## PR 3 — Phase 3: Declarative `sources[]` + approval partial apply

Schema change — run `task generate:schema` and update `scripts/manifest-fixtures.yml`.

### Task 3.1: Schema models

**Files:**
- Modify: `src/metagit/core/project/source_models.py` — add `ProjectSource`
- Modify: `src/metagit/core/workspace/models.py` — `sources: list[ProjectSource]`
- Modify: `src/metagit/core/project/models.py` — `source_id: Optional[str]`
- Modify: `tests/test_project_source_models.py`, new `tests/core/workspace/test_project_sources.py`

- [ ] **Step 1: `ProjectSource` model** with `id` slug validator (alphanumeric + hyphen), `to_source_spec() -> SourceSpec` copying all filter fields and setting `source_id=id`.

- [ ] **Step 2: YAML alias** — accept `ignore:` as `ignore_patterns` via `Field(validation_alias=AliasChoices("ignore_patterns", "ignore"))`.

- [ ] **Step 3: Validator** on `WorkspaceProject` — `sources[].id` unique within project; `mode` cannot be `discover`.

- [ ] **Step 4: Run** `task generate:schema`; add fixture manifest under `examples/` or extend `scripts/manifest-fixtures.yml`.

Run: `uv run pytest tests/core/workspace/test_project_sources.py tests/test_project_source_models.py -v`

- [ ] **Step 5: Commit**

### Task 3.2: Reconcile planning with `source_id`

**Files:**
- Modify: `src/metagit/core/project/source_sync.py`

- [ ] **Update `plan()` reconcile branch:** when `spec.source_id` set, only consider removal candidates where `repo.source_id == spec.source_id` (still skip manual repos with `source_id is None`).

- [ ] **Update `_to_project_path`:** set `source_id=spec.source_id` when present.

- [ ] **Tests:** manual repo preserved; wrong `source_id` not removed; protected repo preserved.

- [ ] **Commit**

### Task 3.3: Manifest sync orchestrator

**Files:**
- Create: `src/metagit/core/project/source_manifest_sync.py`
- Create: `tests/core/project/test_source_manifest_sync.py`

- [ ] **Implement `SourceManifestSyncService`:**

```python
class SourceManifestSyncService:
  def sync_project(
    self,
    *,
    project: WorkspaceProject,
    app_config: AppConfig,
    source_id: str | None = None,
    apply: bool = False,
    force: bool = False,
    logger: UnifiedLogger,
  ) -> SourceSyncResult:
    ...
```

- Iterate enabled `project.sources` (or single `source_id`).
- For each: `discover` → `plan` with source's `mode`.
- Aggregate plans.
- **Partial apply (option A):** apply adds/updates across all sources; defer all `to_remove` unless `force`.
- If deferred removals: call `ApprovalService.request(action="source_sync_reconcile", payload={...})`.
- Return combined `SourceSyncResult` including `pending_approval_id` when queued.

- [ ] **Tests:** reconcile source with removals → manifest gains adds, removals not applied, approval row created; `--force` applies removals; additive source never queues approval.

- [ ] **Commit**

### Task 3.4: Approval executor

**Files:**
- Create: `src/metagit/core/project/source_approval_executor.py`
- Modify: `src/metagit/cli/commands/context.py` (approval approve path) or hook in `ApprovalService.resolve`

- [ ] **`SourceSyncApprovalExecutor.apply(config, config_path, request: ApprovalRequest)`** — validate `action == "source_sync_reconcile"`, remove listed repos from project by normalized URL, save config via `MetagitConfigManager`.

- [ ] **Wire:** after `ApprovalService.resolve(..., decision="approved")`, if action is `source_sync_reconcile`, invoke executor (CLI approve command + web ops handler if present).

- [ ] **Tests:** approve applies removals; deny leaves manifest unchanged.

- [ ] **Commit**

### Task 3.5: CLI manifest mode + write-source + refresh-sources

**Files:**
- Modify: `src/metagit/cli/commands/project_source.py`
- Modify: `src/metagit/cli/commands/project.py` (sync command)

- [ ] **Flags:** `--from-manifest`, `--source-id`, `--write-source`, `--source-id` (required with write), `--force`.

- [ ] **`--from-manifest`:** require `--provider` flags absent; delegate to `SourceManifestSyncService`.

- [ ] **`--write-source`:** after imperative dry-run or apply, append/update `ProjectSource` on project from current CLI flags (requires `--source-id`).

- [ ] **`metagit project sync --refresh-sources`:** call manifest sync with `apply=True`, `ensure` from each source, then existing git sync.

- [ ] **CLI tests** for mutual exclusivity (`--from-manifest` vs `--provider`).

- [ ] **Commit**

### Task 3.6: MCP manifest mode

**Files:**
- Modify: `src/metagit/core/mcp/services/source_sync.py`

- [ ] Support `from_manifest: true`, `source_id`, `force`; manifest reconcile removals enqueue approval (no MCP self-approve).

- [ ] **Test** partial apply JSON shape includes `pending_approval_id`.

- [ ] **Commit**

### Task 3.7: Config Studio (minimal)

**Files:**
- Modify: `schemas/metagit_config.schema.json` (generated)
- Optional: `web/` schema tree if `sources` not auto-discovered

- [ ] Verify `SchemaTreeService` exposes `workspace.projects[].sources[]` after schema regen; smoke test PATCH append if needed.

- [ ] **Commit**

### Task 3.8: Phase 3 docs + QA

- [ ] `CHANGELOG.md` — note schema addition (`sources[]`, `source_id`), partial apply behavior
- [ ] Skills: manifest-first workflow example
- [ ] `.mex/ROUTER.md` — declarative sources
- [ ] `task qa:prepush` (includes manifest fixtures)
- [ ] `task gitnexus:analyze`

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Idempotency option C | 1.1, 1.5, 1.6 |
| Include/ignore filters | 1.2, 1.5 |
| Topic enrichment | 1.4, 1.5 |
| Namespaced naming | 1.3, 1.5 |
| `--json` output | 1.1, 1.6 |
| MCP tool | 2.1 |
| `workspace import` alias | 2.3 |
| `--sync` chaining | 2.2 |
| `sources[]` schema | 3.1 |
| `source_id` provenance | 3.1, 3.2 |
| `--from-manifest` | 3.3, 3.5 |
| Partial apply + approval | 3.3, 3.4 |
| `--write-source` | 3.5 |
| `--refresh-sources` | 3.5 |
| Manual repo preservation | 3.2, 3.3 |

---

## Verification commands (end-to-end)

```bash
# Phase 1 — idempotent CI check
metagit project --project default source sync \
  --provider github --org <org> --mode additive --ensure --apply --json

# Phase 2 — MCP (after metagit mcp serve)
# call metagit_project_source_sync with apply:false

# Phase 3 — manifest partial apply
metagit project --project platform source sync --from-manifest --apply --json
metagit context approval list --json
metagit context approval approve --id <id>
```

---

## Execution order

1. Merge **PR 1** before starting PR 2.
2. Merge **PR 2** before PR 3 (MCP reuse).
3. PR 3 requires schema regeneration and fixture updates in the same PR.

**Estimated scope:** PR 1 ~2–3 days; PR 2 ~1 day; PR 3 ~2–3 days.
