---
name: metagit-context-pack
description: >-
  Token-efficient workspace onboarding via tiered context packs — map, repo cards,
  session digest, objectives, approvals, repomix profiles. Use at session start or
  when scoping work in a metagit-managed workspace.
metadata:
  internal: true
---
# Metagit context packs

Use this skill for the **most token-efficient** way to onboard into a metagit workspace.
Prefer `metagit context pack --tier N --json` over reading raw trees or full manifests.

Set non-interactive defaults:

```bash
export METAGIT_AGENT_MODE=true
```

Run from the **umbrella repo** that contains `.metagit.yml` (or pass `-c path/to/.metagit.yml`).

## When to use

- Session start in any metagit-managed workspace
- Before editing — need project/repo boundaries and health without cloning everything
- Returning after idle — tier 2 digest shows what changed since last session
- Scoping a bugfix — tier 1 cards + `repomix` profile instead of whole-repo dumps
- Coordinating humans and agents — objectives and approval queue state

Do **not** skip context packs and grep the filesystem when a manifest exists.

## Tier workflow

| Tier | Command | Typical tokens | Contents |
|------|---------|----------------|----------|
| 0 | `metagit context pack --tier 0 --json` | ~100–400 | Workspace map: projects, repos, paths, clone status |
| 1 | `metagit context pack --tier 1 --json` | +200–600/repo | Tier 0 + repo cards (git state, stack hints, health flags) |
| 2 | `metagit context pack --tier 2 --json` | +digest | Tier 1 + session digest; **updates session boundary** |

Escalate tiers only when needed. Narrow tier 1/2 with `--project` and/or `--repo`.

### Primary session command

```bash
metagit context pack --tier 2 --json -c .metagit.yml
```

Pair with operational prompts (paste `--text-only` output into agent context):

```bash
metagit prompt workspace -k session-start --text-only -c .metagit.yml
metagit prompt workspace -k context-pack --text-only -c .metagit.yml   # tier escalation guide
```

### Escalation rules

1. Start **tier 0** when you only need catalog boundaries (search-before-create, layout planning).
2. Move to **tier 1** when git health, stack hints, or per-repo instructions matter.
3. Use **tier 2** at session open/return — digest includes `first_session`, `manifest_changed`, per-repo commit counts, active objective id.
4. **Tier 2 touches the session boundary** — avoid running it from multiple agents simultaneously on a shared manifest (see multi-instance below).

### Scoped packs

```bash
metagit context pack --tier 1 --json --project portfolio --repo api-gateway
metagit context pack --tier 2 --json --project portfolio
```

## Single repo card

When you already know the target repo:

```bash
metagit context repo-card --project P --repo R --json -c .metagit.yml
```

Card fields include: `status`, `health_flags` (`missing_clone`, `dirty`, `behind_remote`, `stale_head_30d`), `stack_hints`, resolved `agent_instructions` excerpts.

## Repomix profiles (scoped snapshots)

Bundled profiles: `bugfix-local`, `config-edit`, `cross-repo-impact`.

```bash
metagit context repomix --profile bugfix-local --project P --repo R -c .metagit.yml
metagit context repomix --profile config-edit --project P --repo R --output /tmp/pack.txt
```

Use profiles instead of raw `repomix` on an entire tree. Pick profile by task:

| Profile | Use when |
|---------|----------|
| `bugfix-local` | Implement or debug in `src/`, `tests/` |
| `config-edit` | Manifest or app config changes |
| `cross-repo-impact` | Graph, schema, reference docs for dependency analysis |

## Objectives (shared human ↔ agent state)

Persisted under `.metagit/sessions/objectives.json`.

```bash
metagit context objective list --json -c .metagit.yml
metagit context objective get --id obj-123 --json

echo '{"id":"obj-123","status":"in_progress","title":"Fix API timeout","repos":["portfolio/api"]}' \
  | metagit context objective set -c .metagit.yml

metagit context objective complete --id obj-123 -c .metagit.yml
metagit context objective cancel --id obj-123 -c .metagit.yml
```

Tier-2 digest surfaces `active_objective_id` when one objective is in progress.

## Approvals (human-in-the-loop)

Queue under `.metagit/approvals/pending.json`.

```bash
metagit context approval request --action repo_sync --requested-by hermes --payload '{"project":"P","repo":"R"}' -c .metagit.yml
metagit context approval list --json -c .metagit.yml
metagit context approval list --status all --json

metagit context approval approve --id apr-001 --note "ok for staging" -c .metagit.yml
metagit context approval deny --id apr-002 --note "needs review" -c .metagit.yml
```

Agents: list pending approvals before mutating ops; never self-approve without operator policy.

## Hermes session bootstrap

Wire metagit into Hermes (or any orchestrator) so every objective begins with bounded context.

### When to call

| Trigger | Recommended tier |
|---------|------------------|
| Session / objective open | 2 (full) or 0 (token-tight) |
| Project switch mid-session | 1 scoped to `--project` |
| Subagent handoff to one repo | 1 or `repo-card` + `repomix` |
| Idle return (>1 digest window) | 2 |

### Commands

```bash
export METAGIT_AGENT_MODE=true
PACK_JSON="$(metagit context pack --tier 2 --json -c .metagit.yml)"
PROMPT_TEXT="$(metagit prompt workspace -k session-start --text-only -c .metagit.yml)"
```

### How to inject output

| Host pattern | Injection |
|--------------|-----------|
| Hermes system / bootstrap template | Include `session-start` prompt text; store or summarize pack JSON |
| Pre-turn shell hook | Run commands above; append stdout to conversation context or state file |
| Subagent task prompt | Pass tier-1 JSON for target `--project`/`--repo` plus `subagent-handoff` prompt |
| MCP-connected Hermes | Prefer `metagit_context_pack` (tier 2) then `metagit://workspace/*` resources |

**Token-tight bootstrap:**

```bash
metagit context pack --tier 0 --json
metagit prompt workspace -k session-start --text-only
```

**Default bootstrap:**

```bash
metagit context pack --tier 2 --json
metagit prompt workspace -k context-pack --text-only
metagit prompt workspace -k session-start --text-only
```

Parse pack JSON top-level keys: `workspace_name`, `tier`, `map`, `cards`, `digest`.

## Multi-instance workspaces (Syncthing / shared manifest)

When multiple agents on different machines share a workspace root via Syncthing:

### Conflict zones

| Path | Risk | Mitigation |
|------|------|------------|
| `.metagit.yml` | Simultaneous catalog edits | Single writer; validate before save |
| `.metagit/sessions/*` | Digest boundary race | One coordinator runs tier 2 per session window |
| `.metagit/sessions/objectives.json` | Concurrent upserts | Idempotent objective `id`; list before set |
| `.metagit/approvals/pending.json` | Duplicate rows | List before creating; unique action ids |

### Agent rules

1. **Read after sync settles** — wait for Syncthing idle, then `metagit config validate` and tier 0/1 pack.
2. **One manifest writer** — designate the Hermes controller for catalog mutations (`metagit workspace …`, `metagit config patch --save`).
3. **Tier 2 once per session window** — only the session-owning agent runs `--tier 2`; others use tier 0/1.
4. **Git state is local** — Syncthing syncs manifest/state files, not clone contents; run `metagit project sync` per machine.
5. **Optional coordination file** — teams may touch `.metagit/.manifest-lock` (pid + timestamp) as a human-visible lock; metagit does not enforce it.

### Stale sync detection

```bash
metagit context pack --tier 2 --json    # check digest.manifest_changed
metagit config validate -c .metagit.yml
```

## MCP equivalents (when MCP gate is ACTIVE)

| CLI | MCP tool |
|-----|----------|
| `context pack --tier N` | `metagit_context_pack` (required `tier`) |
| `context repo-card` | `metagit_repo_card` |
| `context objective list/set` | `metagit_objective_list` / `metagit_objective_upsert` |
| `context approval request/list/approve/deny` | `metagit_approval_request` / `metagit_approval_list` / `metagit_approval_resolve` |

Use CLI when operating shell-only (`METAGIT_AGENT_MODE=true`); use MCP when the IDE host exposes metagit tools.

## Output contract

After packing, report to the user or parent agent:

- workspace name and tier used
- project/repo count from `map`
- repos with health flags (from `cards` if tier ≥ 1)
- digest highlights if tier 2 (`first_session`, `manifest_changed`, active objective)
- recommended next step (search, sync, repomix profile, or prompt kind)

## Related skills

- `metagit-cli` — full CLI prompt and catalog reference
- `metagit-workspace-scope` — gate and scope discovery
- `metagit-control-center` — ongoing multi-repo coordination
- `metagit-workspace-sync` — guarded fetch/pull after pack shows stale repos
