# Metagit Web

Bundled SPA + local HTTP handler that ships with the **`metagit-cli`** Python package.

## Purpose

Metagit Web is a developer-focused browser UI for workspace awareness and maintenance
while you work in a `.metagit.yml` umbrella. It sits next to `metagit` CLI commands and
the local HTTP handlers (for example `/v2` workspace catalog/layout and `/v3` config
and ops endpoints). Use it when you prefer point-and-click inspection and edits over
printing JSON in the terminal.

## `metagit web serve`

From a directory containing a valid `.metagit.yml` (or pointing at one with `--root`):

```bash
metagit web serve [OPTIONS]
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--root` | `.` | Workspace directory that contains `.metagit.yml`. Resolved to an absolute path for logging and API handlers. |
| `--appconfig` | *(inherit)* | Overrides the usual Metagit app-config file path (`metagit` passes this from CLI context); required if `ctx.obj` is missing — run via installed `metagit` CLI, or pass `--appconfig` explicitly. |
| `--host` | `127.0.0.1` | Bind address for the bundled HTTP server. |
| `--port` | `8787` | TCP port for the bundled HTTP server (OS may probe if busy). |
| `--open` / `--no-open` | `no-open` | When `--open` is set, the default browser opens the UI URL once the server starts. |
| `--status-once` | *(off)* | Bind once, print a single `web_state=ready host=… port=… url=…` line, then exit immediately (agents and scripts use this for startup checks without leaving a process running). |

The server serves:

- Static assets packaged under `src/metagit/data/web/` from the SPA build.
- API routes delegated to workspace config, catalog, ops, and related handlers (`/v2`, `/v3`, etc.). See `.mex/patterns/metagit-web-api.md` in this repo for handler/model patterns.

Typical foreground run:

```bash
cd /path/to/workspace
metagit web serve
```

Browse to the printed URL (default root is `/`).

## UI tour

### Config Studio

**Config Studio** is the paired Metagit and application configuration editors accessed from the top navigation:

- **Metagit config** (`/config/metagit`): schema-backed tree navigation and field edits for `.metagit.yml` semantics (PATCH flows against `/v3` config APIs).
- **App config** (`/config/appconfig`): same interaction model against application configuration persisted via Metagit's app-config path.

These screens share TanStack Query data loading and theme styling with the shell.

Each config editor includes a **YAML preview** panel with three render modes:

| Mode | Meaning |
|------|---------|
| **Normalized** | Full config from the validated Pydantic model (same serializer as `metagit config show --normalized`). |
| **Minimal** | Non-default fields only (`exclude_defaults`), useful for seeing what differs from schema defaults. |
| **On disk** | Raw file contents as stored on disk (no draft overlay). |

When you **Apply** edits without saving, pending operations are merged into the preview and a **Draft** badge appears. Validation errors from draft operations surface above the YAML block. App-config previews redact sensitive tokens (`***` + last four characters).

API: `POST /v3/config/metagit/preview` and `POST /v3/config/appconfig/preview` with `{ "style": "normalized", "operations": [...] }`.

CLI parity (same operation model):

```bash
metagit config tree
metagit config preview --file ops.json
metagit config patch --file ops.json --save
metagit appconfig patch --op set --path workspace.dedupe.enabled --value false --save
```

See [metagit-config.md](metagit-config.md#schema-backed-editing-cli) for operation shapes and path examples.

### Workspace Explorer

Use the **Explorer** tab on the workspace toolbar for a tree view of projects and repositories with tag-aware filtering.

| Filter syntax | Example | Matches |
|---------------|---------|---------|
| Free text | `api billing` | Name, path, description, tag text |
| Tag key | `tag:backend` or `#backend` | Project or repo tags |
| Tag key=value | `tag:team=platform` | Exact tag value |
| Project scope | `project:hermes` | Repositories under one project |
| Sync status | `status:synced` or `status:missing` | Clone presence |

Each synced repository shows **VS Code**, **Cursor**, and **Default** open actions. Protocol links use `vscode://file/…` and `cursor://file/…`. **Default** calls `POST /v3/ops/open`, which runs the configured CLI editor (`config.editor` in app config, usually `code`). Paths must be managed workspace repositories that exist on disk; arbitrary paths are rejected.

```bash
curl -sS -X POST http://127.0.0.1:8787/v3/ops/open \
  -H 'Content-Type: application/json' \
  -d '{"path":"/absolute/path/to/managed/repo"}'
```

### Agents catalog

**Agents** (`/agents`) lists bundled agent archetypes from `GET /v3/agents/catalog`.
Cards group by `ui.category` and badge `source` (`bundled`, `overlay`, `merged`).
Select a template for metadata, vendor preview (`GET /v3/agents/templates/{id}/preview`),
and a read-only install command (`metagit agent create …`). Bundled templates expose
**Create team overlay** (`POST /v3/agents/templates/{id}/overlay/init`) to scaffold
`.metagit-agents/<id>/` for git-committed editing (use CLI `--local` for personal overrides).
**Dispatch plan** (`GET /v3/agents/templates/{id}/dispatch-plan?vendor=&project=&repo=&task=`)
returns install, per-vendor launch hints, and handoff CLI commands for overseer subagent routing.

The page now includes three sub-tabs:

- **Templates** — the existing agent catalog, preview, and overlay-init workflow.
- **Objectives** — collaborative objective review/editing backed by `GET /v3/ops/objectives`, `POST /v3/ops/objectives`, and `PATCH /v3/ops/objectives/{id}`. Objectives render grouped by workflow status, show `agent_notes` prominently, and keep `human_notes` editable.
- **Sessions** — a read-only digest from `GET /v3/ops/session` plus an explicit **Begin session** action backed by `POST /v3/ops/session/begin`.

Objectives and Sessions share a lightweight polling control bar:

- **Live update** toggle
- **Update frequency** selector with 30s, 60s, 90s, and 300s options
- default interval of **90 seconds**
- **Refresh now** button for manual refetch when polling is disabled or when immediate sync is useful

The Sessions tab shows a compact begin-session summary rather than the full raw `session/begin` payload. On success it refreshes both the current session digest and objectives view so the workflow context stays aligned.

### Repository Terrain

**Repository Terrain** (`/terrain`) is a Three.js operational map of managed repositories in the current umbrella workspace.

| Signal | Visualization |
|--------|----------------|
| Synced default branch (clean, no unpushed work) | **Flat green** tile at baseline height |
| Local / unpushed work | **Bulges upward** proportional to unpushed commits + uncommitted files |
| Behind remote (needs pull) | **Depressed** orange/red tile |
| Non-default branch | **Branch color** (feature=cyan, develop=purple, hotfix=amber, etc.) |
| Merge conflicts | Red tile with surface crack shaders |
| CI/CD | Beacon above each tile (pass/fail/running/pending) |
| Activity | Pulse on recently active repos; darkened/faded when inactive |
| Dependencies | Toggleable arcs between consumer and dependency repos |
| Ownership | Optional heatmap layer from manifest tags (`owner`, `team`, …) |
| Agent readiness | Holographic markers when `AGENTS.md` / docs score is high |

Data loads from a single normalized API:

```bash
curl -sS 'http://127.0.0.1:8787/v3/ops/terrain?include_pipelines=true'
```

Query parameters: `project`, `detail` (`manifest` | `enriched`), `include_pipelines` (default false), `include_inferred` (default true), `limit` (max 5000).

The SPA loads **`detail=manifest`** first (index rows + layout only, no git/CI I/O), renders tiles immediately, then fetches **`detail=enriched`** in the background and updates the scene when git/activity/dependency data arrives.

Click a tile for the detail panel (path, branches, drift, CI, activity, dependencies). Layer toggles sit in the viewport overlay (top-left); **View** controls (bottom-left) switch layout (hierarchy, grid matrix with column sizes, sphere wrap) and visual style (rich vs solid flat colors, animations on/off). Orbit, pan, and zoom use standard Three.js controls.

Backend assembly lives in `RepositoryTerrainService` (`src/metagit/core/web/terrain_service.py`); the SPA uses instanced meshes for tile/beacon rendering.

### Workspace Console

The **Workspace Console** is **Workspace** in the chrome (`/workspace`): catalog-level context (projects/repos index, search/filter) plus the **workspace operations** side panel (health/prune/sync style actions routed through `/v3/ops`). This is meant for situational awareness and lightweight maintenance; destructive actions remain gated as in the CLI and API.

**Provider source sync (manifest):** use the Operations panel to preview or apply sync from `workspace.projects[].sources[]`, or call:

```bash
curl -sS -X POST http://127.0.0.1:8787/v3/ops/source-sync \
  -H 'Content-Type: application/json' \
  -d '{"project_name":"platform","from_manifest":true,"apply":true}'
```

**Approvals:** pending reconcile removals appear in the Operations panel. Resolve via UI or:

```bash
curl -sS http://127.0.0.1:8787/v3/ops/approvals
curl -sS -X POST http://127.0.0.1:8787/v3/ops/approvals/<id>/resolve \
  -H 'Content-Type: application/json' \
  -d '{"decision":"approved"}'
```

**Objectives + session:** web ops also exposes collaborative objective/session endpoints:

```bash
# List objectives
curl -sS http://127.0.0.1:8787/v3/ops/objectives

# Create objective
curl -sS -X POST http://127.0.0.1:8787/v3/ops/objectives \
  -H 'Content-Type: application/json' \
  -d '{"id":"demo-1","title":"Ship objective editing"}'

# Partial objective edit (status/title/acceptance/human_notes/agent_notes/repos)
curl -sS -X PATCH http://127.0.0.1:8787/v3/ops/objectives/demo-1 \
  -H 'Content-Type: application/json' \
  -d '{"status":"in_progress","human_notes":"pairing with agent"}'

# Session digest and session begin envelope
curl -sS http://127.0.0.1:8787/v3/ops/session
curl -sS -X POST http://127.0.0.1:8787/v3/ops/session/begin \
  -H 'Content-Type: application/json' \
  -d '{"project_name":"platform"}'
```

Git sync jobs accept `refresh_sources: true` and `project_name` to mirror `metagit project sync --refresh-sources` before fetch/pull/clone.

### Shared coordination state

Objectives, handoffs, approvals, and the events feed can be served from a
**single canonical host** so multiple agents and the web UI share one document
set. Run `metagit web serve` on the coordinator; clients set `state.url` or
`METAGIT_STATE_URL` (see [Sharing state across a team](sharing-state.md)).

**Whole-document routes** (used by `RemoteHttpBackend` and automation):

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/v3/ops/objectives` | Returns `ETag` |
| `PUT` | `/v3/ops/objectives` | Body `{"objectives":[…]}`; `If-Match` required |
| `GET` | `/v3/ops/approvals?status=all` | Full queue + `ETag` |
| `PUT` | `/v3/ops/approvals` | Body `{"requests":[…]}`; `If-Match` required |
| `GET` | `/v3/ops/handoffs` | Returns `ETag` |
| `PUT` | `/v3/ops/handoffs` | Body `{"handoffs":[…]}`; `If-Match` required |
| `POST` | `/v3/ops/handoffs` | Append one handoff (no prior token) |
| `GET` | `/v3/ops/events?since=` | Incremental `WorkspaceEventsResult` |

Stale `If-Match` → **412**. Granular SPA routes (`POST`/`PATCH` objectives, approval
resolve) remain unchanged.

Use the **Repositories | Explorer | Search | Graph** toggle on the workspace toolbar:

- **Repositories** — filterable table of projects and repos (synced / missing) with per-repo sync actions.
- **Explorer** — nested tree of projects and repositories with tag chips, filter syntax (see above), and open-in-editor actions.
- **Search** — ripgrep across repository file contents.
- **Graph** — SVG diagram of workspace relationships: manual edges from `.metagit.yml` `graph.relationships`, optional inferred cross-project dependencies, and project → repo structure edges. Checkboxes control inferred and structure layers.

Graph data is loaded from `GET /v3/ops/graph`:

| Query param | Default | Meaning |
|-------------|---------|---------|
| `include_inferred` | `true` | Include edges inferred from cross-project dependency analysis. |
| `include_structure` | `true` | Include project → repo containment edges. |

Response shape: `{ ok, nodes[], edges[], manual_edge_count, inferred_edge_count, structure_edge_count }`. Each node has `id`, `label`, `kind` (`project` \| `repo`). Each edge has `from_id`, `to_id`, `type`, optional `label`, and `source` (`manual` \| `inferred` \| `structure`).

## Frontend development workflow

Prerequisites under `web/`: npm (Node toolchain). Prefer the Task targets from the repo root.

### Hot reload (`task web:dev`)

```bash
task web:dev
```

Runs `npm run dev` (Vite) with a dev-server proxy:

- Paths under `/v2` and `/v3` proxy to **`http://127.0.0.1:8787`** (`web/vite.config.ts`).

Therefore the usual workflow is:

1. In one shell: **`metagit web serve`** (or `--port`/`--host` overrides if you customize Vite targets).
2. In another shell: **`task web:dev`** and open Vite's origin (shown in npm output).

The browser talks to Vite while API calls traverse the proxy to Python.

### Production-like bundle (`task web:build`)

```bash
task web:build
```

This runs `web:assets` (regenerate header logo when `docs/inc/metagit_logo_dark.png` changes),
`npm ci || npm install` under `web/`, then `npm run build`, emitting into
`src/metagit/data/web/` (`emptyOutDir: true`). Commit generated assets under both
`web/src/assets/` and `src/metagit/data/web/` whenever shipping UI fixes so
`metagit web serve` picks them up without a local Node install.

#### Header logo (web-optimized)

| Asset | Role |
|-------|------|
| `docs/inc/metagit_logo_dark.png` | Canonical logo (docs, README) — do not load in the SPA |
| `web/src/assets/metagit_logo_header.{webp,png}` | 128×128 header assets (~3 KB WebP) |

Regenerate after changing the source art:

```bash
task web:assets
# or: uv run python scripts/generate_web_logo.py --force
```

Uses `sips` on macOS (and ImageMagick on Linux if installed). `cwebp` adds WebP when present.
Committed outputs are reused on Linux CI when regeneration tools are unavailable.

Continuous integration hooks in `task qa:prepush`/`scripts/prepush-gate.py` focus on Python
tests and lint; they do **not** run **`task web:build`**. If you alter source under `web/`,
run **`task web:build`** manually before tagging or merging UI changes unless your team
delegates builds to CI elsewhere.

## Security

- **`--host` defaults to localhost** (`127.0.0.1`): the bundled server expects local-only use.
- **No authentication layer in Web v1** — anyone who can reach the TCP port can call the APIs the UI exposes. Do not expose an open `--host`/`--port` endpoint on shared networks until an auth model lands.
- Treat `metagit web serve` like any other localhost admin utility: firewall exposure is your responsibility once you bind `0.0.0.0` or comparable.
