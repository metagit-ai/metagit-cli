---
name: metagit-campaign
description: Plan and track cross-project multi-repo campaigns — YAML overlays, repo rollups, objective fan-out, and MR status. Use for umbrella-scale coordinated work.
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

metagit campaign new --slug tier-full --title "Full-tier rollout" \
  --query "platform" --tag agent_tier=full
metagit campaign validate
metagit campaign expand --slug tier-full --dry-run
metagit campaign expand --slug tier-full
metagit campaign set --slug tier-full --repo platform/api --status merged --mr "https://…"
metagit campaign status --slug tier-full --json
```

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
