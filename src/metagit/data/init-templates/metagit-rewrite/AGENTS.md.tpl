# Rewrite orchestrator coordinator

This repository was initialized with the `metagit-rewrite` metagit template.

## Orchestrator role

You coordinate a **reference-implementation rewrite**: workspace **{{ name }}** holds
a source repo (spec) and a target repo (implementation). Read root and layered
`agent_instructions` in `.metagit.yml` before changing workspace layout.

## Session checklist

1. `metagit context pack --tier 2 --json -c .metagit.yml`
2. `metagit campaign status --slug {{ campaign_slug }} --json`
3. Read `_rewrite/parity-registry.yml` for module parity
4. Delegate single-repo work to subagents with repo-scoped instructions
5. `metagit campaign set` + objective `mr_url` when PRs land

## Docs

- [Reference rewrite workspace](https://metagit-ai.github.io/metagit-cli/metagit-rewrite-workspace/)
- [Campaigns reference](https://metagit-ai.github.io/metagit-cli/reference/campaigns/)
- Skill: `metagit-rewrite-campaign`
