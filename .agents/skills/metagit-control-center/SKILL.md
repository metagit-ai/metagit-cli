---
name: metagit-control-center
description: Use when running metagit as an MCP control center for multi-repo awareness, guarded sync, and operational knowledge across ongoing agent tasks.
metadata:
  internal: true
---
# Metagit Control Center Skill

Use this skill when an agent should actively coordinate repository context and task execution across a workspace.

## Purpose

Provide a repeatable control-center workflow where Metagit MCP guides awareness, synchronization, and operational continuity over multiple related repositories.

## Bundled scripts (optional)

Helper scripts live under `scripts/` when the **full skill tree** is installed. Hermes
`skill_manage` copies **SKILL.md only** — scripts are not present unless you also run
`metagit skills install --skill metagit-control-center`.

Resolve scripts from the PyPI package (works whenever `metagit-cli` is installed):

```bash
SKILL_ROOT="$(python3 -c "import metagit, pathlib; print(pathlib.Path(metagit.__file__).parent / 'data/skills/metagit-control-center')")"
"$SKILL_ROOT/scripts/control-cycle.sh" [root_path] ["query"] [preset]
```

Or from a full skill install:

```bash
"$HOME/.config/hermes/skills/metagit-control-center/scripts/control-cycle.sh" .
```

Wrapper behavior:
- runs gating status first
- optionally runs upstream discovery for blocker queries
- emits compact, machine-readable lines

### Inline CLI fallback (no scripts)

Use when skill scripts are unavailable (Hermes SKILL-only install, no shell helpers):

```bash
export METAGIT_AGENT_MODE=true
metagit mcp serve --status-once --root .
metagit context pack --tier 1 --json -c .metagit.yml
metagit prompt workspace -k health-preflight --text-only -c .metagit.yml
# blocker may be upstream — search managed repos:
metagit search "error signature" -c .metagit.yml --json
metagit prompt workspace -k sync-safe --text-only -c .metagit.yml
```

## Core Workflows

### 1) Session Initialization
- Run context pack + session prompt first (see **`metagit-context-pack`** skill):

```bash
metagit context pack --tier 2 --json -c .metagit.yml
metagit prompt workspace -k session-start --text-only -c .metagit.yml
```

- Validate active workspace gate (`metagit mcp serve --status-once` or gate script).
- Read `metagit://workspace/config` and `metagit://workspace/repos/status` (MCP) or tier-1 pack JSON (CLI).
- Call `metagit_project_context_switch` when the objective is tied to a workspace project.
- Run `metagit_workspace_health_check` or read `metagit://workspace/health` for maintenance signals.
- Identify stale repos and unresolved blockers from prior activity.

### 2) Active Task Support
- For each coding objective, map impacted repos.
- Use workspace search and upstream hints before broad exploration.
- Sync only repos that are required by the active objective.

### 3) Guarded Synchronization
- Default to `fetch` for visibility.
- Use `pull` or `clone` only with explicit permission and rationale.
- Track sync outcomes in operations log resource.

### 4) Operational Memory
- Before switching projects: `metagit_session_update` (notes + recent repos), optional `metagit_workspace_state_snapshot`.
- After returning: `metagit_workspace_state_restore` when a snapshot was taken (metadata only; git tree is unchanged).

Maintain bounded local records of:
- sync actions
- issue signatures searched
- candidate upstream repos identified
- unresolved dependencies and follow-ups

## Decision Guidelines

- Use metagit search first when blocker appears external to current repo.
- Prefer deterministic evidence over speculative jumps.
- Keep operations minimal and auditable.

## Output Contract

For each control-center cycle, provide:
- current objective
- repositories examined
- actions taken (or intentionally deferred)
- next recommended step

## Safety Rules

- Never mutate repositories without explicit authorization.
- Never broaden scope beyond configured workspace boundaries.
- Always preserve a clear audit trail of control actions.
