# Provider Source Import — Design Spec

**Date:** 2026-06-11  
**Status:** Draft  
**Approved decisions:** idempotency option C; reconcile approval option A (partial apply)  
**Builds on:** Existing `metagit project source sync` (`SourceSyncService`, `SourceSpec`, `SourceSyncMode`)

## Problem

Users need to bulk-register repositories from GitHub orgs/users or GitLab groups (including nested subgroups) into a workspace project in `.metagit.yml`. The workflow must support:

- Recursive discovery where the provider allows it
- Explicit ignore/include filters
- Idempotent re-runs for automation
- Provider-backed descriptions and topic tags when authenticated
- Safe reconcile semantics for keeping the manifest in sync with upstream scope

Metagit already ships a partial solution via `metagit project source sync`. This spec defines the **enhancement pass** to close gaps without breaking existing callers.

## Non-goals

- GitHub GraphQL batch enrichment for very large orgs (phase 2 optimization)
- Hosted HTTP API parity beyond optional v2 route in phase 2
- Automatic `metagit detect` per imported repo
- Atomic reconcile plans where adds wait on removal approval (rejected; see partial apply)

## Current baseline

| Capability | Implementation |
|------------|----------------|
| GitHub org/user listing | `SourceSyncService._discover_github` |
| GitLab group + subgroups | `_discover_gitlab` with `include_subgroups` |
| Modes | `discover`, `additive`, `reconcile` |
| Basic filters | `include_archived`, `include_forks`, `path_prefix` |
| Provenance | `source_provider`, `source_namespace`, `source_repo_id` |
| Description | From list API |
| Repo tags | Only `source: <provider>` |
| Apply guard | `--apply`; reconcile removals require `--yes` |
| Agent JSON | Not supported |

## Design decisions

### Idempotency (approved: option C)

Both behaviors are exposed; default remains backward compatible.

| Flag state | Re-run behavior |
|------------|-----------------|
| `--mode additive --apply` (no `--ensure`) | Add missing URLs; **update** metadata when name, description, or provenance fields differ (current behavior) |
| `--mode additive --apply --ensure` | Add missing URLs; **noop** for repos whose normalized URL (or `source_repo_id`) already exists |
| `--ensure --refresh-metadata` | With ensure: still update description, topics, and provenance fields without treating as "unchanged" for reporting |

`discover` mode never writes. `reconcile` is unchanged except it respects new filters and naming strategy.

### Reconcile approval (approved: option A — partial apply)

Manifest-driven reconcile (`sources[].mode: reconcile`) uses **partial apply**:

- **Adds and updates** apply immediately when `--from-manifest --apply` runs.
- **Removals** are held until approval resolves or the operator passes **`--force`**.
- Imperative CLI `--mode reconcile --apply` remains **atomic** with `--yes` (no approval queue) for one-shot operator use.

See [Phase 3](#phase-3-declarative-sources) for approval payload and executor details.

### Command surface

**Primary (extend existing):**

```bash
metagit project --project <name> source sync \
  --provider github|gitlab \
  (--org <org> | --user <user> | --group <group>) \
  [--mode discover|additive|reconcile] \
  [--recursive / --no-recursive] \
  [--include-archived] [--include-forks] \
  [--path-prefix <prefix>] \
  [--include-pattern <glob> ...] \
  [--ignore <glob> ...] \
  [--name-strategy short|namespaced] \
  [--ensure] [--refresh-metadata] \
  [--no-enrich-topics] \
  [--apply] [--yes] \
  [--sync] \
  [--json]
```

**Optional alias (phase 2):** `metagit workspace import` with agent-friendly defaults (`--mode additive --ensure --json`); delegates to the same service.

### Extended `SourceSpec`

New fields on `SourceSpec` (`source_models.py`):

```python
include_patterns: list[str] = []      # fnmatch on full_name; empty = no allowlist
ignore_patterns: list[str] = []       # fnmatch on full_name
ignore_languages: list[str] = []      # applied after enrichment
visibility: Literal["any", "public", "private", "internal"] = "any"
name_strategy: Literal["short", "namespaced"] = "namespaced"
ensure: bool = False
refresh_metadata: bool = False
enrich_topics: bool = True
```

CLI mapping:

- Repeatable `--include-pattern`, `--ignore`
- `--name-strategy` default `namespaced`
- `--ensure`, `--refresh-metadata`, `--no-enrich-topics`
- `--sync` runs `ProjectManager.sync()` for the target project after a successful manifest save

### Filter pipeline

Order after API discovery:

1. `include_patterns` (if any): keep only matching `full_name`
2. `ignore_patterns`: drop matching `full_name`
3. Legacy flags: `include_archived`, `include_forks`, `path_prefix`
4. `visibility` filter on `DiscoveredRepo.private` / GitLab visibility
5. Topic enrichment (optional)
6. `ignore_languages` on enriched language field

Use `fnmatch.fnmatch` on provider `full_name`:

- GitHub: `owner/repo`
- GitLab: `group/subgroup/repo` (`path_with_namespace`)

### Provider metadata enrichment

Reuse `ProviderRegistry` / existing provider classes rather than duplicating HTTP in `SourceSyncService`.

| Field | Source | Target |
|-------|--------|--------|
| `description` | List API (already) | `ProjectPath.description` |
| Topics | GitHub `/topics` or list payload; GitLab `topics[]` | `ProjectPath.tags[topic] = "topic"` |
| `language` | Provider metadata when available | `ProjectPath.language` |
| Provenance | Discovery | `source_*` fields (unchanged) |

Tag merge rules:

- Always set `tags["source"] = provider.value`
- Merge provider topics into existing repo tags; **never remove** user-defined keys
- Never overwrite a non-empty user tag value with a provider topic unless `--refresh-metadata`

Enrichment limits (v1):

- If discovered count > 100 and enrichment would require per-repo calls, log warning and skip per-repo enrichment unless `--refresh-metadata` (list payload fields still applied)
- Retry provider HTTP 429/503 up to 3 times with exponential backoff

### GitLab naming strategy

Default `namespaced` avoids collisions when `--recursive` imports nested subgroups.

| Strategy | Manifest `name` |
|----------|-----------------|
| `short` | GitLab `path` / GitHub `name` (legacy) |
| `namespaced` | Last path segment unless collision; then join last two segments (`platform-api-gateway`); further collisions append `-2`, `-3`, … |

Workspace sync folder layout continues to use manifest `name` under `{workspace.path}/{project}/{repo}/`.

### Planning and apply semantics

**Match key:** normalized clone URL (via `normalize_git_url`); fallback `source_repo_id` when URL changed upstream.

**`plan()` changes:**

- When `ensure=True`, repos matched by URL/id go to `unchanged` (not `to_update`) unless `refresh_metadata=True` and metadata differs
- `to_update` includes description, tags, language, provenance per `_needs_update` extension

**`apply_plan()`:** unchanged structure for imperative CLI; reconcile still skips protected projects/repos and only removes entries matching provenance (`source_id` when manifest-driven, else `source_provider` + `source_namespace`).

**Imperative reconcile (CLI `--mode reconcile`):** unchanged guard — removals require `--yes` (or `--force` when aligned with manifest flow).

**Conflicts:**

- Same manifest `name`, different normalized URL → `CatalogError`-style failure on apply with message naming both URLs; no silent overwrite in v1

### Recursive scope notes

| Provider | Recursive behavior |
|----------|-------------------|
| GitLab | `include_subgroups=true` on group projects API |
| GitHub org/user | Flat repo list; `--recursive` documented as no-op for GitHub |
| GitHub Enterprise | Same flat semantics unless future org-hierarchy API is added |

Document in `docs/development.md` and bundled skills.

### JSON output (`--json`)

Emit a single JSON object (stdout) for agent use:

```json
{
  "ok": true,
  "applied": false,
  "spec": { "...": "..." },
  "plan": {
    "discovered_count": 42,
    "filtered_count": 38,
    "unchanged": 30,
    "to_add": [{ "name": "...", "url": "..." }],
    "to_update": [],
    "to_remove": []
  },
  "errors": []
}
```

On failure: non-zero exit, `"ok": false`, `"errors": [{ "kind": "...", "message": "..." }]`.

Human-readable logs remain on stderr when `--json` is set (same pattern as catalog mutations).

### MCP (phase 2)

Tool: `metagit_project_source_sync`

- Same parameters as CLI (JSON object)
- Requires ACTIVE MCP state and valid workspace manifest
- Returns plan + applied status; mutating calls require explicit `apply: true`
- Reconcile with removals requires `confirm: true` (maps to `--yes`)

### Testing

| Area | Cases |
|------|-------|
| `SourceSpec` | Pattern lists, visibility enum, ensure + refresh_metadata combo |
| Filter engine | include/ignore globs, archived/fork shorthand, visibility |
| Ensure mode | Second run → zero `to_update`/`to_add`; refresh overrides |
| Namespaced naming | GitLab collision resolution |
| Tag merge | Existing manual tags preserved; topics added |
| CLI | `--json` schema; reconcile without `--yes` fails |
| Mock HTTP | Paginated GitHub/GitLab list responses |

Fixtures: extend `scripts/manifest-fixtures.yml` only if schema changes (not required for v1).

### Documentation updates

- `docs/development.md` — full flag reference and idempotency table
- `CHANGELOG.md` — under next release
- Bundled `metagit-cli` skill — import workflow examples
- `.mex/ROUTER.md` — note enhanced filters, `--ensure`, `--json`
- `metagit prompt` `repo-enrich` catalog entry — mention `--ensure` / topic enrichment

## Phased delivery

### Phase 1 (single PR)

- Extended `SourceSpec` + filter pipeline
- `--ensure` / `--refresh-metadata` planning semantics
- Topic enrichment + tag merge
- GitLab `namespaced` naming default
- `--json` on CLI
- Unit + CLI tests; docs/changelog/skills

### Phase 2

- MCP `metagit_project_source_sync`
- Optional `metagit workspace import` alias
- `--sync` post-apply clone
- HTTP v2 route if needed for Web Console

<a id="phase-3-declarative-sources"></a>
### Phase 3 — Declarative sources in `.metagit.yml`

Persist upstream import scope on the workspace project; sync reconciles `repos[]` against it.

#### Schema: `sources[]` on `WorkspaceProject`

New model `ProjectSource` (validated field on `WorkspaceProject`, not nested in `metadata`):

```python
class ProjectSource(BaseModel):
  id: str                              # required; unique within project; slug
  provider: SourceProvider
  org: str | None = None
  user: str | None = None
  group: str | None = None
  mode: SourceSyncMode = ADDITIVE      # additive | reconcile only (not discover)
  recursive: bool = True
  ensure: bool = True
  refresh_metadata: bool = False
  enrich_topics: bool = True
  include_archived: bool = False
  include_forks: bool = False
  path_prefix: str | None = None
  include_patterns: list[str] = []
  ignore_patterns: list[str] = []
  name_strategy: Literal["short", "namespaced"] = "namespaced"
  enabled: bool = True
```

On `WorkspaceProject`:

```python
sources: list[ProjectSource] = Field(default_factory=list)
```

On `ProjectPath` (provenance extension):

```python
source_id: str | None = None   # links to ProjectSource.id
```

| Layer | Role |
|-------|------|
| `sources[]` | **Intent** — upstream scope to import from |
| `repos[]` | **Materialized catalog** — registered repos, clones, search index |

Repos **without** `source_id` are manual entries: never auto-removed by source reconcile. Repos **with** `source_id` are managed by that source’s `mode`.

#### Example manifest

```yaml
workspace:
  projects:
    - name: platform
      description: Platform engineering repos
      sources:
        - id: acme-github-platform
          provider: github
          org: acme-corp
          mode: reconcile
          ensure: true
          refresh_metadata: false
          enrich_topics: true
          ignore:
            - "**/deprecated/**"

        - id: acme-gitlab-infra
          provider: gitlab
          group: acme/infrastructure
          mode: additive
          recursive: true

      repos:
        - name: local-coordinator
          path: ./

        - name: platform-api-gateway
          url: https://gitlab.com/acme/infrastructure/platform/api-gateway.git
          source_id: acme-gitlab-infra
          source_provider: gitlab
          source_namespace: acme/infrastructure
          source_repo_id: "12345"
          tags:
            source: gitlab
```

YAML key `ignore` maps to `ignore_patterns` on load (alias for ergonomics).

#### Manifest-driven commands

```bash
# Plan/apply all enabled sources on a project
metagit project source sync --from-manifest --project platform

# Single source
metagit project source sync --from-manifest --source-id acme-github-platform

# Bootstrap: one-shot CLI import writes a new sources[] entry
metagit project source sync --provider github --org acme-corp \
  --write-source --source-id acme-github-platform --mode reconcile

# Refresh sources before git clone/sync
metagit project sync --project platform --refresh-sources
```

`SourceSpec` at runtime is built from CLI flags **or** by merging one or more `ProjectSource` entries (`ProjectSource.to_source_spec()`).

#### Reconcile approval (approved: option A — partial apply)

When a reconcile source produces `to_remove` entries:

1. **Apply immediately:** all `to_add` and `to_update` entries; persist manifest.
2. **Do not apply removals** unless `--force` or an approved pending request exists.
3. **Enqueue approval** via `ApprovalService` with action `source_sync_reconcile`:

```json
{
  "action": "source_sync_reconcile",
  "requested_by": "agent",
  "payload": {
    "project": "platform",
    "source_id": "acme-github-platform",
    "to_remove": [{ "name": "retired-svc", "url": "..." }]
  }
}
```

4. On `metagit context approval approve --id <id>`, an executor applies pending removals to `repos[]` (and optionally runs prune/sync for dropped checkouts).
5. **`--force`** on `source sync --from-manifest` skips approval and applies removals in the same run (respects `protected` repos/projects unless `--force` on protected catalog).

| Situation | Behavior |
|-----------|----------|
| `mode: additive` | Add/update only; never queue removals |
| `mode: reconcile` + removals | Partial apply (adds/updates now; removals approval-gated) |
| Repo `protected: true` | Never removed |
| Repo without `source_id` | Manual; never removed by source reconcile |
| Project `protected: true` | Block manifest mutations unless `--force` |

Imperative CLI `--mode reconcile` keeps the existing `--yes` confirmation for full apply in one step; manifest-driven flow uses the approval queue instead of `--yes`.

#### Phase 3 deliverables

- Pydantic + JSON schema for `ProjectSource`, `source_id` on `ProjectPath`
- `SourceSyncService.sync_from_manifest()` orchestrating per-source discover/plan/apply
- `SourceSyncApprovalExecutor` (or extend catalog ops) to apply approved removals
- `--from-manifest`, `--write-source`, `--refresh-sources`
- Manifest fixtures + Config Studio tree nodes for `sources[]`
- Tests: partial apply, approval round-trip, manual repo preservation

### Phase 4 (optional)

- Scheduled/agent refresh (`metagit project source sync --from-manifest` in CI/cron)
- Web Console UI for pending source reconcile approvals

## Success criteria

- `metagit project source sync --provider gitlab --group X --recursive --ignore '**/archive/**' --mode additive --ensure --apply --json` is safe to run repeatedly in CI with zero manifest diff on second run
- Re-run without `--ensure` updates description/topics when provider changed
- GitLab recursive import produces unique manifest names for same short `path` in different subgroups
- GitHub topics appear in `repos[].tags` when token configured
- Existing scripts using discover/additive/reconcile without new flags behave as today (except default `namespaced` naming — **breaking for new GitLab imports only**; document migration: re-import or rename)
- Manifest reconcile with removals: adds/updates land on first `--from-manifest --apply`; removals appear in approval queue until approved or `--force`
- Manual repos (no `source_id`) survive reconcile of managed sources on the same project

## Open question (non-blocking)

Default `namespaced` naming changes manifest names for new GitLab recursive imports vs today’s `short` names. Acceptable because it fixes collisions; existing entries are untouched until reconcile/update. If needed, ship with `--name-strategy short` documented as legacy opt-in for one release before flipping default.
