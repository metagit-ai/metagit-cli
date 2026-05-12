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

Under `workspace.projects[].repos`, each repository entry may include a flat string-to-string `tags` map (for example `tier: "1"`). These tags are carried into the workspace index for filtering and for upcoming managed-repo lookup via `metagit search` once that command is available.