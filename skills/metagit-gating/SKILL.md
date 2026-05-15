---
name: metagit-gating
description: Use when implementing or operating Metagit MCP server activation and tool exposure rules based on .metagit.yml presence and validity.
---

# Metagit MCP Gating Skill

Use this skill whenever you need to control whether Metagit MCP tools/resources are exposed.

## Purpose

Ensure high-risk tooling and multi-repo context are only available when a valid `.metagit.yml` exists at the resolved workspace root.

## Local Script Wrapper (Use First)

Use this token-efficient wrapper for all gating checks:
- `./scripts/gate-status.zsh [root_path]`

Expected output (single line, tab-delimited):
- `state=<value>\troot=<path|none>\ttools=<count>`

## Activation Workflow

1. Resolve workspace root:
   - `METAGIT_WORKSPACE_ROOT`
   - CLI `--root`
   - upward directory walk
2. Check for `.metagit.yml` in resolved root.
3. Validate config through existing Metagit config models.
4. Derive activation state: missing, invalid, or active.
5. Register tool surface based on state.

## Tool Exposure Contract

### Inactive (missing or invalid config)
Expose only:
- `metagit_workspace_status`
- `metagit_bootstrap_config_plan_only`

### Active (valid config)
Expose full set:
- `metagit_workspace_status`
- `metagit_workspace_index`
- `metagit_workspace_search`
- `metagit_upstream_hints`
- `metagit_repo_inspect`
- `metagit_repo_sync`
- `metagit_bootstrap_config`

## Error Handling

- Return explicit, machine-readable state and reason.
- Avoid stack traces in user-facing outputs.
- Log parser/validation errors with enough detail for debugging.

## Safety Rules

- Never expose mutation-capable tools in inactive state.
- Never operate outside validated workspace boundaries.
- Keep defaults read-only unless user/agent explicitly opts in.
