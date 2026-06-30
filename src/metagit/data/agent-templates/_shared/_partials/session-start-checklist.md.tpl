## Session start (every time)

1. `metagit mcp serve --status-once` or gate check — confirm Metagit is active.
2. MCP resource ladder (read-only, token-efficient):
   - `metagit://catalog`
   - `metagit://workspace/map`
   - `metagit://prompt/workspace/session-start?instructions=0`
   - `metagit://session/meta`
3. `metagit_workspace_health_check` — missing clones, broken mounts, duplicate URLs.
4. Use `metagit://workspace/config?view=full` only when editing the manifest; default summary otherwise.
5. Tool `metagit_session_begin` once per session window when a full bootstrap envelope is required (mutates session boundary).
