---
name: refreshing-project-config
description: Refresh or bootstrap `.metagit.yml` using deterministic discovery and validation flows. Use when configuration is missing, stale, or incomplete for workspace operations.
---

# Refreshing Project Config

Use this skill to keep `.metagit.yml` accurate and operational.

## Workflow

1. Check workspace activation and config validity.
2. Run bootstrap plan mode first.
3. Review generated changes against expected workspace topology.
4. Apply config updates and validate schema before continuing.

## Command Wrapper

- `zsh ./skills/metagit-mcp-bootstrap/scripts/bootstrap-config.zsh [root_path] [mode] [seed_context]`

## Output Contract

Return:
- config health state before/after
- generated update summary
- any manual follow-up needed

## Safety

- Prefer plan/dry-run first for large config updates.
- Keep changes bounded to target workspace intent.
