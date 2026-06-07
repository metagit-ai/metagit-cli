## Session start (every time)

1. `metagit mcp serve --status-once` or gate check — confirm Metagit is active.
2. Context pack tier 2 + session-start prompt:
   - `metagit context pack --tier 2 --json -c {{ manifest_path }}`
   - `metagit prompt workspace -k session-start --text-only -c {{ manifest_path }}`
3. `metagit_workspace_health_check` — missing clones, broken mounts, duplicate URLs.
4. Read `metagit://workspace/config` when you need the full manifest.
