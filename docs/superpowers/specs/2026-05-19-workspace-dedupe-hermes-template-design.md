# Workspace repo deduplication, Hermes orchestrator template, and config examples

**Status:** Implemented (P0–P2, workspace-only dedupe)  
**Date:** 2026-05-19

## Summary

Three related capabilities for metagit:

1. **App-level workspace deduplication** — when enabled, sync reuses a single canonical checkout per Git URL or resolved local path within one `.metagit.yml` workspace; project folders receive symlinks instead of duplicate clones.
2. **Hermes orchestrator template** — bundled workspace template with fully populated `agent_instructions` for a DevOps / project-management controller, including a `local` project for non-git path repos.
3. **Generated config exemplar** — build-time `metagit config example` producing a commented YAML file with all optional schema fields for documentation.

## Decisions

| Topic | Decision |
|-------|----------|
| Dedupe scope (v1) | **`workspace` only** — same umbrella `.metagit.yml`; no cross-umbrella registry in v1 |
| Dedupe default | `workspace.dedupe.enabled: false` (backward compatible) |
| Physical layout | `{workspace.path}/_canonical/{repo_key}/` holds real trees; `{workspace.path}/{project}/{repo}` symlinks when dedupe applies |
| Global registry | Deferred (v2); not in initial implementation |
| Hermes template | `src/metagit/data/templates/hermes-orchestrator/` + `examples/hermes-orchestrator/` |
| Config example | `metagit config example` integrated with `task generate:schema` |

## 1. Workspace-scoped deduplication

### AppConfig schema (`WorkspaceConfig`)

```yaml
config:
  workspace:
    path: ./.metagit
    dedupe:
      enabled: false
      scope: workspace          # v1: only "workspace" is implemented
      strategy: symlink
      canonical_dir: _canonical
```

Environment overrides (optional, follow existing `METAGIT_WORKSPACE_*` pattern):

- `METAGIT_WORKSPACE_DEDUPE_ENABLED=true|false`

### Identity keys

| Repo type | Key source |
|-----------|------------|
| Remote (`url`) | Normalized Git URL (reuse `source_sync` normalization) |
| Local (`path`) | `Path(path).expanduser().resolve()` |
| Branch-sensitive | If `branches` or `ref` differ materially, **do not** dedupe (separate canonical entries) |

`repo_key`: stable slug derived from identity (not display `name`).

### Sync algorithm (`ProjectManager`)

When `dedupe.enabled` and `scope == workspace`:

1. Resolve `repo_key` for the repo entry.
2. Canonical path: `{workspace.path}/{canonical_dir}/{repo_key}/`.
3. If canonical exists and is valid → ensure `{workspace.path}/{project}/{repo.name}` is a symlink to canonical (repair if broken).
4. If canonical missing → clone/copy into canonical, then symlink project mount.
5. Update in-memory index used by health (optional tag `metagit.canonical_key` on write).

When `dedupe.enabled` is false: preserve current behavior (clone/symlink directly under project dir).

### Catalog and MCP

- `WorkspaceCatalogService` / `metagit project repo add`: before add, check workspace index for existing `repo_key`; suggest link or block duplicate URL/path with actionable message.
- `metagit_workspace_health_check`: extend duplicate URL warning with dedupe-aware actions (`review_config`, `repair_mount`, `resync_canonical`).

### Prune (`project repo prune`)

- Reference-count project mounts pointing at each canonical path.
- Remove canonical directory only when refcount is zero and repo is not `protected`.

### Edge cases

- Broken symlink → recommend repair via re-sync.
- macOS/Linux: `os.symlink`; document Windows junction limitations separately if needed.
- Local path repos: same as remote (canonical may be the resolved source tree or a symlink to it — prefer symlink to source when `path` is outside workspace to avoid copying).

### Out of scope (v1)

- `~/.config/metagit/repo-registry.yml` global dedupe
- Automatic cross-machine dedupe
- `strategy: manifest_only` (manual `path:` only)

## 2. Hermes orchestrator template

### Artifacts

| Path | Role |
|------|------|
| `src/metagit/data/templates/hermes-orchestrator/.metagit.yml.fragment` | Umbrella manifest template (or full example merged on apply) |
| `src/metagit/data/templates/hermes-orchestrator/AGENTS.md.fragment` | Optional coordinator repo agent file |
| `examples/hermes-orchestrator/.metagit.yml` | Committed example for docs |
| `docs/hermes-orchestrator-workspace.md` | Operator + agent guide (complements `docs/hermes-iac-workspace-guide.md`) |

### Workspace projects (example)

- **`portfolio`** — Git-backed services/apps under management.
- **`local`** — Non-git `path` repos for static sites and local publish targets (`sync: true`).
- **`platform`** (optional in example) — IaC / shared infra pointer to IaC guide patterns.

### Controller `agent_instructions` (root + layers)

Template must populate all four layers with non-overlapping content:

1. `MetagitConfig.agent_instructions` — Hermes controller role: orchestration entrypoint, never create duplicate workspace layout without metagit search.
2. `workspace.agent_instructions` — Portfolio rules: validate after YAML edits, sync policy, documentation requirements.
3. `workspace.projects[].agent_instructions` — Per-group focus (e.g. `local` = no git operations).
4. `repos[].agent_instructions` — Per-repo publish/build notes where applicable.

### Session checklist (embedded in root instructions)

1. `metagit_workspace_status` + health check.
2. Search before create (`metagit_repo_search` / CLI search).
3. Register or reuse via catalog; `metagit config validate`.
4. `metagit_project_context_switch` for focused work.
5. Delegate to subagent when single-repo; stay controller when cross-project.
6. `metagit_workspace_sync` — fetch by default; pull/clone with approval.
7. Ensure each repo has `description`; update manifest when paths or publish targets change.
8. `metagit_session_update` on handoff.

### `local` project pattern

```yaml
- name: local
  description: Local-only paths (no git). Static sites and publish workflows.
  agent_instructions: |
    Repos use `path`, not `url`. Do not git clone/pull.
    Document publish steps in each repo's agent_instructions.
  repos:
    - name: example-site
      path: ~/Sites/example-site
      sync: true
      kind: website
      agent_instructions: |
        Build and publish steps here. Keep .metagit.yml in sync with real paths.
```

Apply via existing `WorkspaceTemplateService` / `metagit_project_template_apply` with template id `hermes-orchestrator`.

## 3. Generated full `.metagit.yml` example

### CLI

```bash
metagit config example \
  --output docs/reference/metagit-config.full-example.yml \
  --include-workspace \
  --comment-style line
```

### Generator behavior

- Walk `MetagitConfig` and nested Pydantic models recursively.
- Emit representative values; attach `Field.description` as YAML `#` comments.
- Merge `src/metagit/data/config-example-overrides.yml` for realistic prose fields (`agent_instructions`, sample URLs).
- Document file as **non-production** exemplar.

### CI

Extend `task generate:schema`:

```yaml
generate:schema:
  cmds:
    - uv run metagit config schema --output-path ./schemas/metagit_config.schema.json
    - uv run metagit appconfig schema --output-path ./schemas/metagit_appconfig.schema.json
    - uv run metagit config example --output docs/reference/metagit-config.full-example.yml --include-workspace
```

## Implementation phases

| Phase | Deliverable |
|-------|-------------|
| P0 | `metagit config example`, overrides file, docs page, CI hook |
| P1 | Hermes template bundle, example manifest, orchestrator guide |
| P2 | `workspace.dedupe` AppConfig, canonical sync in `ProjectManager`, tests, health/catalog hooks |
| P3 | Global registry and advanced prune (future) |

## Testing

- Unit: `repo_key` normalization; symlink target resolution; refcount on prune.
- Integration: tmp workspace, two projects, one URL, dedupe enabled → one canonical + two mounts.
- Regression: dedupe disabled matches current clone layout.

## References

- `src/metagit/core/project/manager.py` — `_sync_local`, `_sync_remote`
- `src/metagit/core/mcp/services/workspace_health.py` — `_duplicate_url_warnings`
- `src/metagit/core/appconfig/models.py` — `WorkspaceConfig`
- `docs/hermes-iac-workspace-guide.md` — IaC-focused Hermes patterns
- `.cursor/skills/metagit-projects/SKILL.md` — check-before-create workflow
