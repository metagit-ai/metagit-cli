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

### Workspace Console

The **Workspace Console** is **Workspace** in the chrome (`/workspace`): catalog-level context (projects/repos index, search/filter) plus the **workspace operations** side panel (health/prune/sync style actions routed through `/v3/ops`). This is meant for situational awareness and lightweight maintenance; destructive actions remain gated as in the CLI and API.

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
