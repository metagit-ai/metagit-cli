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

### Workspace Console

The **Workspace Console** is **Workspace** in the chrome (`/workspace`): catalog-level context (projects/repos index, search/filter) plus the **workspace operations** side panel (health/prune/sync style actions routed through `/v3/ops`). This is meant for situational awareness and lightweight maintenance; destructive actions remain gated as in the CLI and API.

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

This runs `npm ci || npm install` under `web/`, then `npm run build`, emitting into
`src/metagit/data/web/` (`emptyOutDir: true`). Commit those generated assets whenever
shipping UI fixes so `metagit web serve` picks them up without a local Node install.

Continuous integration hooks in `task qa:prepush`/`scripts/prepush-gate.py` focus on Python
tests and lint; they do **not** run **`task web:build`**. If you alter source under `web/`,
run **`task web:build`** manually before tagging or merging UI changes unless your team
delegates builds to CI elsewhere.

## Security

- **`--host` defaults to localhost** (`127.0.0.1`): the bundled server expects local-only use.
- **No authentication layer in Web v1** — anyone who can reach the TCP port can call the APIs the UI exposes. Do not expose an open `--host`/`--port` endpoint on shared networks until an auth model lands.
- Treat `metagit web serve` like any other localhost admin utility: firewall exposure is your responsibility once you bind `0.0.0.0` or comparable.
