---
name: metagit-campaign
description: Plan and track cross-project multi-repo campaigns — YAML overlays, repo rollups, objective fan-out, and MR status. Use for umbrella-scale coordinated work.
metadata:
  internal: true
---
# Metagit campaign skill

<!-- modality:native_campaigns -->
<!-- modality:objective_mr_approval_binding -->
<!-- modality:coordination_events_scope -->

Use when coordinating **many repos** under one intent (rollout, migration, tier stamp) with a committed, diffable status overlay.

Docs: [campaigns.md](https://metagit-ai.github.io/metagit-cli/reference/campaigns/) · Registry: [modality-feature-registry.md](https://metagit-ai.github.io/metagit-cli/reference/modality-feature-registry/)

## When to use

- One selection query → frozen repo list → per-repo status/MR tracking
- Fan-out spine objectives for parallel agents (`campaign expand`)
- Rollup: merged vs open MR vs blocked without manual spreadsheets

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

# 1. Create from find query (+ optional tags)
metagit campaign new --slug tier-full --title "Full-tier rollout" \
  --query "platform" --tag agent_tier=full

# 2. Validate atlas references
metagit campaign validate

# 3. Optional: one objective per repo for spine tracking
metagit campaign expand --slug tier-full --dry-run
metagit campaign expand --slug tier-full

# 4. Work repos; update status as MRs land
metagit campaign set --slug tier-full --repo platform/api \
  --status mr-open --mr "https://gitlab.example.com/…/merge_requests/42"
metagit campaign set --slug tier-full --repo platform/api --status merged

# 5. Rollup
metagit campaign status --slug tier-full --json
```

## Agent posture before repo work

When repos declare `agent_profile`, provision before dispatch:

```bash
metagit agent profile show -p platform -n api --json
metagit agent apply --vendor claude_code --project platform --repo api
```

Skill: `metagit-cli` · Doc: [agent-profile.md](https://metagit-ai.github.io/metagit-cli/reference/agent-profile/)

## Orchestrator polling

```bash
metagit context events --campaign tier-full --since "<iso-cursor>" --json
metagit context handoff list --json
```

## Objective MR binding

When an objective produces an MR or approval, record linkage:

```bash
echo '{"id":"campaign-tier-full-platform-api","mr_url":"https://…","approval_id":"abc"}' \
  | metagit context objective set
```

## Safety

- Commit `_campaigns/` (or configured path) to git
- Run `metagit campaign validate` in CI alongside `metagit config validate`
- Use `campaign expand --dry-run` before writing many objectives

## Related skills

- `metagit-multi-repo` — implement changes across expanded repos
- `metagit-control-center` — dispatch loop with profile apply
- `metagit-context-pack` — tier-2 session boundary before large fan-out
