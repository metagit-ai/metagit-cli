---
name: release-0381-defects
description: Defects found against 0.38.0 and the constraints that keep the fixes from drifting.
last_updated: 2026-11-02
---

# 0.38.1 defect fixes

## Gotchas

- `config split` copies original list-item YAML and only reindents. `fmt` must not turn a long single-line scalar into a literal block. An inner newline is a `value` diff; leading or trailing whitespace stays `whitespace-only`.
- Synced checkouts live under `METAGIT_WORKSPACE_PATH` or `./.metagit` beside the manifest (`resolve_sync_root` + `project_mount_path`). An explicit repo `path` stays relative to the manifest directory.
- Pull-request lookup prefers the manifest repo `url`. An SSH host with no dot is resolved with `ssh -G`. JSON reasons are `no pull request`, `forge not supported`, and `lookup failed`.
- Click clears unparsed args before a group callback. `project` and `workspace` save them in `LazyManifestGroup` so `-c` after the subcommand and `--help` work without a manifest.
- `agent dispatch-plan -p` without `-n` merges the workspace and project profiles into `local_skills`. Repo-scoped templates still require both.
- A single-file manifest has no source map. Duplicate-repo warnings fall back to the manifest path.
