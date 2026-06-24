---
name: metagit-workspace-scope
description: Discover active metagit workspace scope, project boundaries, and repository status. Use when an agent starts work in a multi-repo workspace and needs fast, scoped context before editing.
metadata:
  internal: true
---
# Discovering Workspace Scope

Use this skill at session start for workspace-aware tasks. Prefer **`metagit-context-pack`**
for the full tiered pack workflow; this skill focuses on scope boundaries and Hermes wiring.

## Workflow

1. Run context pack (tier 0 minimum, tier 2 at session open):

```bash
export METAGIT_AGENT_MODE=true
metagit context pack --tier 2 --json -c .metagit.yml
metagit prompt workspace -k session-start --text-only -c .metagit.yml
```

2. Run workspace gate and status checks.
3. Build a compact map of active project names, repo names, and sync state from pack JSON.
4. Report a bounded scope for the current objective.

## Hermes session bootstrap

Wire into Hermes (or any orchestrator) **before the first tool call** on a workspace task.

```bash
export METAGIT_AGENT_MODE=true
PACK_JSON="$(metagit context pack --tier 2 --json -c .metagit.yml)"
PROMPT_TEXT="$(metagit prompt workspace -k session-start --text-only -c .metagit.yml)"
```

| Integration point | What to inject |
|-------------------|----------------|
| Hermes system / bootstrap template | `PROMPT_TEXT` verbatim; summarize `PACK_JSON` map + health flags |
| Pre-turn shell hook | Run commands; append stdout to conversation context |
| Subagent dispatch | Tier-1 pack scoped with `--project`/`--repo` + `subagent-handoff` prompt |
| MCP-connected Hermes | `metagit_context_pack` tier 2, then workspace resources |

Token-tight alternative: tier 0 pack + `session-start` prompt only.

See **`metagit-context-pack`** for tier escalation, objectives, approvals, and repomix.

## Commands

Gate check (pick one):

```bash
SKILL_ROOT="$(python3 -c "import metagit, pathlib; print(pathlib.Path(metagit.__file__).parent / 'data/skills/metagit-gating')")"
"$SKILL_ROOT/scripts/gate-status.sh" [root_path]
# inline fallback:
metagit mcp serve --status-once --root .
```

Scope discovery:

```bash
metagit context pack --tier 1 --json -c .metagit.yml
metagit workspace list -c .metagit.yml --json
metagit search "<query>" -c .metagit.yml --json
```

Interactive (human sessions only):

- `metagit workspace select --project <name>`
- MCP `metagit_project_context_switch` with `project_name`
- MCP `metagit_workspace_state_snapshot` before leaving a project for a long switch

## Multi-instance workspaces (Syncthing)

When agents on multiple machines share a manifest via Syncthing:

1. Wait for sync idle, then `metagit config validate` before trusting scope.
2. Designate **one writer** for `.metagit.yml` catalog edits.
3. Only the session-owning agent runs `context pack --tier 2` (updates session boundary).
4. Git clones are local — run `metagit project sync` per machine after manifest changes.
5. Check `digest.manifest_changed` after tier-2 pack if another agent may have edited the manifest.

Full conflict-avoidance table: **`metagit-context-pack`** skill.

## Output Contract

Return:
- active/inactive workspace state and reason
- candidate project to operate on
- top repositories to inspect first (prioritize health flags from pack cards)

## Safety

- Keep operations read-only in this step.
- Do not sync or mutate repositories without explicit request.
