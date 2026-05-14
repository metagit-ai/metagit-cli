# CLI Reference

This page contains the auto-generated documentation for the `metagit` command-line interface.

::: mkdocs-click
    :module: metagit.cli.main
    :command: cli
    :prog_name: metagit 

## MCP Command Notes

- Start MCP stdio runtime:
  - `metagit mcp serve`
- Start against a specific workspace root:
  - `metagit mcp serve --root /path/to/workspace`
- Print status snapshot and exit:
  - `metagit mcp serve --status-once`
- When the workspace gate is **active**, the tool **`metagit_repo_search`** searches only repos listed under `workspace.projects[].repos` in `.metagit.yml` (tags, sync status, resolved paths). This is separate from **`metagit_workspace_search`**, which searches existing checkout paths on disk inside the workspace.

## Workspace configuration

Under `workspace.projects[].repos`, each repository entry may include a flat string-to-string `tags` map (for example `tier: "1"`). These tags are carried into the workspace index and into `metagit search` / `metagit find` for filtering.

## Managed repository search

- `metagit search QUERY` — list managed repositories from the workspace definition that match the query (name, URL substring, tag keys/values, project name). Only repos declared under `workspace.projects[].repos` are considered.
- `metagit find QUERY` — alias for `metagit search`.
- `--definition PATH` — `.metagit.yml` to load (default: `.metagit.yml` in the current directory). The workspace root for resolving `path:` entries is the parent directory of that file.
- `--json` — print search results as JSON (matches include `match_reasons` and scores).
- `--path-only` — resolve to exactly one local directory (fails if there is no match or more than one match).
- `--tag key=value` — repeat to require matching tag values (all given pairs must match).
- `--project`, `--exact`, `--synced-only`, and `--limit` narrow or rank results further.

## Local JSON API (`metagit api`)

- `metagit api serve` — bind a `ThreadingHTTPServer` on `--host` / `--port` (default `127.0.0.1:7878`) under `--root` (directory containing `.metagit.yml`).
- `metagit api serve --status-once` — allocate a port (use `--port 0` for ephemeral), print `api_state=ready host=… port=…`, and exit (for tests and automation).
- `GET /v1/repos/search?q=…` — same managed-repo search as the CLI; optional query params: `project`, `exact=true|false`, `synced_only=true|false`, `limit`, repeat `tag=key=value`.
- `GET /v1/repos/resolve?q=…` — single-match resolution; HTTP `404` when not found, `409` when ambiguous (body includes `ManagedRepoResolveResult` JSON).