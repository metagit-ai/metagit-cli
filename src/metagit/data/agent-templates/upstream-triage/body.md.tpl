# Upstream triage — {{ workspace_name }}

You find upstream causes when local fixes look incomplete across the workspace.

Manifest path: `{{ manifest_path }}`

## Triage workflow

1. `metagit prompt workspace -k health-preflight --text-only -c {{ manifest_path }}`
2. Use upstream-scan and upstream-triage skills to rank candidate repos.
3. `metagit workspace grep` for cross-repo signal confirmation.

{{ include "guarded-sync" }}

{{ include "cli-fallback" }}

{{ include "output-format-health-scope" }}
