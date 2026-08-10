---
name: hermes-install-target-fix
description: Align metagit skills/MCP Hermes targeting with HERMES_HOME and config.yaml.
last_updated: 2026-07-17
---

# Hermes installer targeting fix

## Problem

`metagit skills install --target hermes` and `metagit mcp install --target hermes` assume XDG `~/.config/hermes/` plus a JSON `mcp.json` launched via `uvx metagit-cli`. Real Hermes gateways use:

- `HERMES_HOME` (default `~/.hermes`) for skills at `$HERMES_HOME/skills/`
- MCP registration in `$HERMES_HOME/config.yaml` under `mcp_servers:`
- An installed `metagit` binary (uvx ephemeral envs lack `pkg_resources` / setuptools)

## Decisions

1. **User-scope Hermes home:** `os.environ["HERMES_HOME"]` if set, else `~/.hermes`. No new CLI flag required for v1 (`--hermes-home` deferred).
2. **Skills path:** `$HERMES_HOME/skills` (user); project scope stays `.hermes/skills` under the project install root.
3. **MCP path/format:** Hermes writes/merges YAML `$HERMES_HOME/config.yaml` (project: `.hermes/config.yaml`) key `mcp_servers`. Other targets keep JSON + `mcpServers`.
4. **Launch command (all targets):** prefer `shutil.which("metagit")`, else the running interpreter `python -m metagit mcp serve`. Stop defaulting to `uvx metagit-cli`.
5. **Hermes MCP entry env:** set `METAGIT_AGENT_MODE: "true"` on the server env block so gateway-spawned MCP is non-interactive.
6. **Config merge:** use `ruamel.yaml` for Hermes so existing keys/comments are preserved when possible.

## Out of scope

- Migrating already-copied skills from `~/.config/hermes/`
- OpenClaw / other vendor home env vars
- Changing Hermes gateway restart behavior
