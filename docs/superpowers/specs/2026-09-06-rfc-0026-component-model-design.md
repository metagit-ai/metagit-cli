# RFC-0026: Component Model — Design

**Status:** Implemented
**Date:** 2026-09-06
**Series:** [Component Context Graph index](2026-09-06-rfc-0026-component-context-graph-index.md)
**Plan:** [2026-09-06-rfc-0026-component-model.md](../plans/2026-09-06-rfc-0026-component-model.md)
**Depends on:** existing `.metagit.yml` models (`ProjectPath`, `AgentProfile`, `MetagitConfig`), `metagit config validate`

## Summary

Introduce a first-class **Component** configuration entity nested under workspace repositories, plus a runtime **catalog** that also maps application-manifest `paths[]` (and path-bearing top-level `components[]`) into the same type. Validate components as part of `metagit config validate`. Do not add a `metagit component` command group, graph endpoints, or context-compile flags in this slice.

## Goals

- Optional `workspace.projects[].repos[].components[]` on `ProjectPath`.
- `Component` Pydantic model with required `name` + `path` and the full declarative optional schema (kind, language, commands, `depends_on`, produces, deploys_to, skills, tags, agent instructions/profile).
- Stable identity `project/repo/component`.
- Catalog adapter so application manifests participate without retyping `paths` / top-level `components`.
- Path normalization and structural validation (duplicates, escape, same-repo `depends_on`, cycles, missing dirs when the repo is cloned).
- Extend `agent_profile` reference checks to catalog rows.
- Backward compatible: no `components` key continues to load and validate.

## Non-Goals

- `metagit component list|show|resolve|detect|init|graph`
- Path → component longest-match resolver (RFC-0027)
- `GraphEndpoint.component` and graph traversal (RFC-0028)
- `context compile --component` / profile inheritance merge (RFC-0029)
- Component claims / semantic ownership (RFC-0030)
- Derived working sets (RFC-0032)
- MCP component tools
- Rewriting existing `paths` YAML to `Component`
- Auto-creating a whole-repo component when `components` is absent
- LLM-based discovery or ranking

## Decisions (locked)

1. **One Component model, two attachment points.** Native YAML: `repos[].components[]`. Adapter YAML: application `paths[]` and top-level `components[]` that have a local `path`. `ref`-only top-level `components[]` stay out of the catalog.
2. **Do not retype `paths` / top-level `components`.** They remain `list[ProjectPath]`. `local_workspace_project` and cross-project dependency MCP keep current types.
3. **`Component` is not a `ProjectPath` subclass.** Git-only fields (`url`, `sync`, `branches`, `ci`, `derived_from`, `source_*`, `ref`, `protected`) are forbidden on `Component`.
4. **PathMetadata is a shared helper, not a Pydantic parent of `ProjectPath`.** Subclassing would reorder `ProjectPath` YAML keys and churn `metagit fmt`. `path_metadata.py` exports overlapping field names and `path_metadata_kwargs()` for the adapter. `Component` redeclares those fields after `name` / `path`.
5. **Identity is always a 3-tuple:** `project/repo/component`. Application manifests use `config.name` for project and repo.
6. **Tags stay `dict[str, str]`.** Agent instructions stay a scalar `str` (with `agent_prompt` alias), matching `ProjectPath`.
7. **`Component.skills` are capability tags**, not `agent_profile.skills` install ids.
8. **`kind` is an open string.** Recommended values are documented, not a closed enum.
9. **`depends_on` items are `str | ComponentRef`.** Bare string = same-repo component name. Do not coerce strings into objects on dump (YAML roundtrip).
10. **Validation is hard-error** via `config validate` (same abort pattern as graph/profile). Nested paths are allowed. Filesystem existence is checked only when the repo directory exists.
11. **No new CLI group.** Hook `validate_components` next to `validate_graph_relationships`.

## Architecture

```text
.metagit.yml
  workspace.projects[].repos[].components[] ──► native Component
  paths[] (application) ─────────────────────► adapter Component
  components[] with path ────────────────────► adapter Component
  components[] ref-only ─────────────────────► not in catalog

ComponentCatalog.list(config)
        │
        ▼
 ResolvedComponent (id, source, project, repo, spec)
        │
        ▼
 validate_components(config, definition_root)
        │
        ▼
 metagit config validate  (abort on issues)
```

### Catalog sources

| Source enum | Origin | Identity |
|-------------|--------|----------|
| `native` | `repos[].components[]` | `{project}/{repo}/{component}` |
| `path` | application `paths[]` with a `path` | `{config.name}/{config.name}/{name}` |
| `legacy_component` | top-level `components[]` with a `path` | `{config.name}/{config.name}/{name}` |

Workspace repos with omitted or empty `components` contribute nothing. Catalog order is deterministic: workspace projects then repos in manifest order, then components in list order; then application adapter rows in list order (`paths` before top-level `components`).

### Types

**`ComponentRef`**

- `component: str` (required)
- `project: str | None`
- `repo: str | None`
- `extra = "forbid"`

**`ComponentCommand`**

- `command: str` (non-empty after strip)
- `extra = "forbid"`

**`Component`**

Required: `name`, `path`.

Optional:

| Field | Type |
|-------|------|
| `description` | `str \| None` |
| `kind` | `str \| None` |
| `language` | `str \| None` |
| `language_version` | `str \| None` (coerce like `ProjectPath`) |
| `package_manager` | `str \| None` |
| `frameworks` | `list[str]` |
| `commands` | `dict[str, str \| ComponentCommand]` |
| `depends_on` | `list[str \| ComponentRef]` |
| `produces` | `list[str]` |
| `deploys_to` | `list[str]` |
| `skills` | `list[str]` |
| `tags` | `dict[str, str]` |
| `agent_instructions` | `str \| None` (`agent_prompt` alias) |
| `agent_profile` | `AgentProfile \| None` |

Git-only keys are rejected (`extra = "forbid"`).

Recommended `kind` values (not enforced): `application`, `service`, `library`, `package`, `infrastructure`, `worker`, `cli`, `plugin`, `documentation`, `data`, `tool`, `unknown`.

**`ComponentId`**

- Fields: `project`, `repo`, `component` (all non-empty, no `/`)
- `key` / `component_id()` → `project/repo/component`
- `parse_component_id()` requires exactly three segments

**`ResolvedComponent`**

- `project`, `repo`, `source`, `spec: Component`
- `name` from `spec.name`
- `id` from `component_id(...)`

### Path normalization

`normalize_repo_relative_path(raw) -> str | ValueError`:

- Strip; convert `\` to `/`
- Reject empty, absolute (leading `/` or Windows drive)
- Collapse `.` and `..` with `PurePosixPath` semantics
- Reject `..` that would leave the repo root
- Empty remainder after collapse is `.` (whole-repo component)
- Strip trailing `/` except for `.`
- Catalog comparison uses the normalized form; YAML is not rewritten

### Validation

Function: `validate_components(config, *, definition_root: str | Path) -> list[str]`

Message prefix: `component:`.

**Hard errors**

| Rule | Scope |
|------|-------|
| Pydantic load failures | missing name/path, extra git fields, empty command |
| Duplicate `name` (stripped) | per `(project, repo)` catalog group |
| Duplicate **normalized** `path` | per `(project, repo)` |
| Path absolute or escapes repo | per component |
| Same-repo `depends_on` name missing | local refs only |
| Same-repo `depends_on` cycle | including self-edges |
| Unknown `agent_profile` skill/MCP/rule ids | catalog rows; no inheritance merge |

**Same-repo `depends_on`:** a bare string, or a `ComponentRef` whose `project`/`repo` are unset or equal to the current identity. Cross-project/cross-repo refs are stored and ignored by existence/cycle checks.

**Nested paths** (`apps/web` and `apps/web/packages/auth`) are allowed (longest-match is RFC-0027).

**Filesystem:** resolve repo root from `repo.path` relative to `definition_root` (application: `definition_root` itself). If that directory **exists**, the component path must exist as a directory (`.` means the repo root). If the repo is not cloned, skip.

**Hook:** `config_validate` runs profile issues, graph issues, then component issues; abort if any list is non-empty. `AgentProfileService.list_validation_issues` also walks catalog `agent_profile` blocks (`scope="component"`, optional `component` name on `AgentProfileValidationIssue`).

## Package layout

```text
src/metagit/core/project/path_metadata.py
src/metagit/core/component/
  __init__.py
  models.py
  identity.py
  paths.py
  catalog.py
src/metagit/core/config/component_validation.py
```

`ProjectPath.components: list[Component] = []` (or default empty list). Schema generator includes `Component` and the `agent_prompt` alias.

## Persistence / events

No new store. Components live in `.metagit.yml`. No events in this slice.

## Interfaces

### CLI

```bash
metagit config validate [-c PATH]
```

### MCP / Web

None beyond Config Studio schema tree from generated JSON Schema.

### Python

```python
component_id(project: str, repo: str, component: str) -> str
parse_component_id(value: str) -> ComponentId | ValueError
normalize_repo_relative_path(raw: str) -> str | ValueError
ComponentCatalog().list(config: MetagitConfig) -> list[ResolvedComponent]
validate_components(config, *, definition_root) -> list[str]
```

## Testing

Fixtures under `tests/fixtures/components/` (YAML + optional dirs):

- `no-components` — existing umbrella shape
- `native-nested` — `repos[].components[]`
- `application-paths` — `paths[]` adapter
- `legacy-ref-only` — top-level `components` with `ref`, no path
- `nested-paths` — overlapping prefix allowed
- `missing-dir` — cloned repo, missing component directory

Coverage: models, identity, path normalize, catalog sources, validation rules, `config validate` CLI abort, existing manifests still valid.

## Documentation

- `docs/concepts/components.md` — operator model, identity, attachment points, what is not built yet
- `CHANGELOG.md` Unreleased
- Schema example via `task generate:schema`
- Pointers in `docs/agents.md`, `llms.txt`, `docs/reference/metagit-config.md`
- Modality id `component_model` (CLI validate + docs; no MCP/web ops)

## Acceptance

- [ ] Native `repos[].components[]` loads with extra=forbid
- [ ] Application `paths[]` appear in the catalog as `{name}/{name}/{path-name}`
- [ ] `ref`-only top-level `components[]` are absent from the catalog
- [ ] Repos without `components` validate as today
- [ ] Duplicate names/paths, path escape, same-repo unknown deps, cycles fail `config validate`
- [ ] Missing component directory fails only when the repo dir exists
- [ ] Nested component paths do not fail
- [ ] Invalid component `agent_profile` skill ids fail validate
- [ ] JSON schema includes `ProjectPath.components`

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| `ProjectPath`, `AgentProfile`, config validate | RFC-0027 resolver/CLI, RFC-0028 graph, RFC-0029 compiler |

## Open questions

None for this slice. Later slices own resolver, graph, compile, ownership, discovery, and derived sets.
