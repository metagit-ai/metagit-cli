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