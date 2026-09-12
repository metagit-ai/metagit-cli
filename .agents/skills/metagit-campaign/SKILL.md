---
name: metagit-campaign
description: Plan and track cross-project multi-repo campaigns — YAML overlays, repo rollups, objective fan-out, and MR status. Use for umbrella-scale coordinated work.
metadata:
  internal: true
---
# Metagit campaign skill

<!-- modality:native_campaigns -->
<!-- modality:campaign_everroom_context -->
<!-- modality:objective_mr_approval_binding -->
<!-- modality:coordination_events_scope -->

Use when coordinating **many repos** under one intent (rollout, migration, tier stamp) with a committed, diffable status overlay.

Docs: [campaigns.md](https://metagit-ai.github.io/metagit-cli/reference/campaigns/) · [campaign-everroom.md](https://metagit-ai.github.io/metagit-cli/reference/campaign-everroom/) · Registry: [modality-feature-registry.md](https://metagit-ai.github.io/metagit-cli/reference/modality-feature-registry/)

## When to use

- One selection query → frozen repo list → per-repo status/MR tracking
- Fan-out spine objectives for parallel agents (`campaign expand`)
- Rollup: merged vs open MR vs blocked without manual spreadsheets
- Combined **Campaign Context** from MetaGit topology plus optional EverRoom evidence

## Configuration

```yaml
# metagit.config.yaml
workspace:
  campaigns_path: _campaigns   # default; or knowledge/campaigns
```

Env: `METAGIT_WORKSPACE_CAMPAIGNS_PATH`

## Lifecycle

```bash
export METAGIT_AGENT_MODE=true

metagit campaign new --slug tier-full --title "Full-tier rollout" \
  --query "platform" --tag agent_tier=full
metagit campaign validate
metagit campaign expand --slug tier-full --dry-run
metagit campaign expand --slug tier-full
metagit campaign set --slug tier-full --repo platform/api --status merged --mr "https://…"
metagit campaign status --slug tier-full --json
```

## Campaign Context (optional EverRoom)

<!-- modality:campaign_everroom_context -->

A campaign is the **technical/work** boundary. An EverRoom Room is the **context/evidence** boundary.

- **MetaGit answers:** "What exists and what is affected?"
- **EverRoom answers:** "What do we know, why did we decide it, and what context surrounds it?"

When operating on a campaign:

1. Identify the campaign slug.
2. Inspect MetaGit technical scope (`campaign status` / `campaign context`).
3. Check whether an EverRoom provider is attached (`campaign everroom status`).
4. Retrieve Campaign Context (`campaign context --json` or MCP `metagit_campaign_context`).
5. Use MetaGit for topology, Git state, and relationships.
6. Use EverRoom for rationale, evidence, decisions, and historical context.
7. Do not treat generated summaries as authoritative over source material.
8. Cite `source=metagit` vs `source=everroom`.
9. Do not retrieve unrelated Room/global context through MetaGit.

```bash
export METAGIT_EVERROOM_URL=http://127.0.0.1:3210
export METAGIT_EVERROOM_TOKEN=…    # never put this in YAML, Git, or prompts

metagit campaign everroom attach --slug terraform-hcp-migration --room room_01J…
metagit campaign context --slug terraform-hcp-migration --json
metagit campaign everroom sync --slug terraform-hcp-migration
metagit campaign everroom detach --slug terraform-hcp-migration
```

If EverRoom is down, `campaign context` still returns MetaGit-only data with a warning. `attach`/`sync` fail instead of mutating blindly.

Never store tokens in `_campaigns/*.yml`. Room id ≠ campaign slug.

## Agent posture before repo work

```bash
metagit agent profile show -p platform -n api --json
metagit agent apply --vendor claude_code --project platform --repo api
```

## Orchestrator polling

```bash
metagit context events --campaign tier-full --since "<iso-cursor>" --json
```

## Related skills

- `metagit-multi-repo` · `metagit-control-center` · `metagit-context-pack`
