# RFC-0027: Component Resolution + CLI — Design

**Status:** Implemented
**Date:** 2026-09-06
**Series:** [Component Context Graph index](2026-09-06-rfc-0026-component-context-graph-index.md)
**Depends on:** [RFC-0026 Component model](2026-09-06-rfc-0026-component-model-design.md)
**Plan:** [2026-09-06-rfc-0027-component-resolution.md](../plans/2026-09-06-rfc-0027-component-resolution.md)

## Summary

Add a path→component **longest-match resolver** and lookup-by-identity on top of the RFC-0026 catalog. Expose `metagit component list|show|resolve` plus matching MCP tools and read-only web GET routes that call the same service. Do not add detect, init, graph traversal, or `context compile --component`.

## Goals

- Resolve a repository-relative (or filesystem) path to the most specific catalogued component.
- Look up a component by `project/repo/component` or a unique bare name.
- List catalog rows, optionally filtered by project/repo.
- Thin CLI / MCP / web adapters over one core service.
- Repositories with no `components` stay valid: list is empty; resolve returns no match.

## Non-Goals

- `metagit component detect|init|graph|validate` (validate stays `config validate`)
- `GraphEndpoint.component` / graph walk (RFC-0028)
- `context compile --component` (RFC-0029)
- Component claims (RFC-0030)
- Auto-creating a whole-repo component when `components` is absent
- SPA page for components (API only)
- Rewriting `paths[]` YAML types

## Decisions (locked)

1. **One service:** `ComponentResolver` in `src/metagit/core/component/resolve.py`. CLI, MCP, and web call it. Do not duplicate matching logic.
2. **Do not import `catalog` or `resolve` from `metagit.core.component.__init__`** (circular import with `config.models` → `ProjectPath`).
3. **Longest match** uses normalized POSIX paths. A query matches component path `P` when the query equals `P`, or is `P` plus `/…`, or `P` is `.` (whole-repo). Nested prefixes are allowed; the longest `P` wins. Duplicate normalized paths are already a validate error, so ties do not occur.
4. **No match is not an exception** at the service layer (`None`). CLI/MCP/web map that to a not-found exit/error. Invalid paths (empty, absolute-as-repo-relative, escape) are `ValueError`.
5. **Ambiguous bare names and ambiguous cross-repo relative paths** are `ValueError` (caller must pass `--project`/`--repo` or a full id).
6. **Identity lookup** accepts `project/repo/component`. A single-segment name succeeds only when it is unique in the filtered catalog.
7. **Filesystem mapping is optional.** If `definition_root` is set and the query path exists (or is absolute), map it onto a repo checkout via `repo.path`, then longest-match the remainder. Otherwise treat the query as a repo-relative path.
8. **JSON** uses `metagit.cli.json_output.emit_json` on the CLI (`schema_version: "1.0"`). MCP/web return the same payload dicts without requiring that wrapper.
9. **Modality id** `component_resolve` (new row). Keep `component_model` as schema/validate.
10. **CLI tests for `component` use subprocess**, not `CliRunner`, because UnifiedLogger enqueue can race (same as config validate component tests).

## Architecture

```text
MetagitConfig
    │
    ▼
ComponentCatalog.list(config)          (RFC-0026, unchanged)
    │
    ▼
ComponentResolver
    list(config, project?, repo?)
    get(config, identity, project?, repo?)
    resolve(config, path, project?, repo?, definition_root?)
    │
    ├── metagit component list|show|resolve
    ├── MCP metagit_component_list|show|resolve
    └── GET /v3/ops/components
        GET /v3/ops/components/resolve
```

## Resolver algorithm

### `list`

1. `rows = ComponentCatalog().list(config)`
2. If `project` is set, keep rows with `row.project == project`.
3. If `repo` is set, keep rows with `row.repo == repo`.
4. Return remaining rows in catalog order.
5. Unknown project/repo filters yield an empty list (not an error).

### `get`

1. Apply the same project/repo filters as `list`.
2. If `identity` parses as a three-segment id (`parse_component_id`), return the row whose `id` equals that key, else `None`. If project/repo filters disagree with the id, return `None`.
3. Otherwise treat `identity` as a component name (no `/`). Matching rows by `row.name`:
   - 0 → `None`
   - 1 → that row
   - 2+ → `ValueError("ambiguous component name …; use project/repo/component")`

### `resolve`

1. If `definition_root` is provided, try filesystem mapping:
   - Expand the query (`Path(path).expanduser()`). If it is absolute or exists relative to cwd **or** relative to `definition_root`, compute an absolute path.
   - For each catalog row’s repo, compute `repo_root` (workspace: `definition_root / repo.path`; application adapter rows: `definition_root`).
   - If the absolute path is the repo root or a descendant, set `rel` to the POSIX path relative to `repo_root` (`.` if equal). Restrict candidate rows to that `(project, repo)` and continue at step 3 with `rel`.
   - If several repos contain the path, prefer the longest `repo_root` prefix.
   - If no repo contains it, fall through to repo-relative handling.
2. Normalize the query with `normalize_repo_relative_path`. On `ValueError`, return it.
3. Candidate rows: catalog list filtered by optional `project`/`repo` (and by filesystem-mapped repo when step 1 succeeded).
4. A row matches when, after normalizing `spec.path`:
   - path is `.`, or
   - query equals path, or
   - query starts with `path + "/"`.
5. Among matches, pick the maximum path length (`0` for `.`, otherwise number of `/` segments).
6. If project+repo were specified (or filesystem mapped to one repo): 0 matches → `None`; 1+ → winner.
7. If project/repo were **not** specified: collect one winner per `(project, repo)` that has a match. 0 → `None`; 1 → that row; 2+ → `ValueError` asking for `--project`/`--repo`.

Repos with no components never match.

## JSON payloads

### Component object (list items, show, resolve match)

```json
{
  "id": "platform/core/web",
  "project": "platform",
  "repo": "core",
  "name": "web",
  "path": "apps/web",
  "source": "native",
  "kind": "application",
  "spec": { }
}
```

`spec` is `Component.model_dump(mode="json")`. Helper: `resolved_component_payload(row) -> dict` in `resolve.py`.

### `list`

```json
{ "schema_version": "1.0", "components": [ /* payload objects */ ] }
```

MCP/web omit `schema_version` or include it — CLI `emit_json` adds it when missing. Service returns `{"components": [...]}`.

### `show`

Service returns the payload object or `None` / `ValueError`. CLI `--json` wraps via `emit_json`. Not found: exit 1, human `component not found: …`.

### `resolve`

Match:

```json
{ "matched": true, "path": "<query>", /* component fields */ }
```

No match:

```json
{ "matched": false, "path": "<query>" }
```

CLI `--json` still exits 1 on no match. Human match prints `{id}\t{path}`. Human miss prints `no component matched: {path}` on stderr.

## CLI

```bash
metagit component list [-c .metagit.yml] [--project P] [--repo R] [--json]
metagit component show <name-or-id> [-c .metagit.yml] [--project P] [--repo R] [--json]
metagit component resolve <path> [-c .metagit.yml] [--project P] [--repo R] [--json]
```

- Group option `--config-path/-c` defaults to `.metagit.yml`. If `ctx.obj["definition_path"]` is set (global `-c` pointed at a manifest) and the user did not pass `-c`, use that.
- Load via `MetagitConfigManager` + `resolve_definition_root` (same as `context` pack).
- Register `component_group` in `src/metagit/cli/main.py`.
- Human `list`: one line `{id}\t{path}\t{kind or -}` per row. Empty catalog: exit 0, no lines (JSON `components: []`).

## MCP

ACTIVE-state tools (workspace required):

| Tool | Args | Result |
|------|------|--------|
| `metagit_component_list` | optional `project`, `repo` | `{components: [...]}` |
| `metagit_component_show` | required `component`; optional `project`, `repo` | payload or `-32602` if missing/ambiguous |
| `metagit_component_resolve` | required `path`; optional `project`, `repo` | `{matched, path, …}` — `matched: false` is success (not protocol error) |

`additionalProperties: false` on schemas. Dispatch in `runtime.py` calling `ComponentResolver`. Register names on the ACTIVE list in `tool_registry.py`. Tests in `tests/core/mcp/test_component_tools.py` following `test_aos_tools.py`.

## Web

Read-only:

- `GET /v3/ops/components?project=&repo=` → `{components: [...]}` (200)
- `GET /v3/ops/components/resolve?path=&project=&repo=` → resolve payload (200 even when `matched: false`; 400 on `ValueError`)

Wire in `OpsWebHandler.handle`. No SPA. Tests in `tests/core/web/test_ops_handler.py` (or a focused `test_ops_components.py`).

## Package layout

```text
src/metagit/core/component/resolve.py     # NEW ComponentResolver
src/metagit/cli/commands/component.py     # NEW thin Click group
```

Modify: `main.py`, `tool_registry.py`, `runtime.py` schemas + dispatch, `ops_handler.py`, modality YAML, docs, CHANGELOG, ROUTER, patterns.

## Testing

Unit (`tests/core/component/test_resolve.py`):

- Direct path match (`apps/web` → web)
- Nested file (`apps/web/src/login.tsx` → web)
- Overlap (`apps/web` vs `apps/web/packages/auth` → auth for a file under auth)
- Whole-repo `.` loses to a more specific component
- Repo without components → `None`
- Invalid/escaping path → `ValueError`
- Unique bare name vs ambiguous name
- Full id lookup
- Application `paths[]` adapter identity `{name}/{name}/{name}`
- Unscoped relative path that matches two repos → `ValueError`
- Filesystem mapping under `definition_root` when the file exists

CLI subprocess tests (`tests/cli/commands/test_component_cli.py`) using `tests/fixtures/components/native-nested.yml`.

MCP + web adapter tests as above.

## Documentation

- Update `docs/concepts/components.md` (commands; remove from “not in this release”)
- `docs/agents.md`, `llms.txt`, `AGENTS.md` command table
- `CHANGELOG.md` Unreleased
- Modality `component_resolve` with CLI/MCP/web/docs markers
- Series index: 0027 design+plan; status implementing → implemented at closeout

## Acceptance

- [ ] `metagit component resolve apps/web/src/login.tsx -c native-nested.yml --project platform --repo core --json` yields `name=web`, `matched=true`
- [ ] Overlapping paths select the longest match
- [ ] Manifests with no components: `list --json` is `{components:[]}`; `resolve` is `matched:false`
- [ ] `show platform/core/web` works; two `web` names without a qualifier fail
- [ ] MCP tools appear in ACTIVE `tools/list` and call the resolver
- [ ] GET `/v3/ops/components` returns catalog JSON
- [ ] Existing `config validate` / catalogs unchanged

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0026 catalog, identity, path normalize | RFC-0028 graph endpoints, RFC-0029 compile `--component` |
