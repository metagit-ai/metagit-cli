---
name: metagit-rewrite-campaign
description: Orchestrate a reference-implementation rewrite across source and target repos using campaigns, parity registry conventions, objectives, and subagent handoffs.
---
# Metagit rewrite campaign skill

<!-- modality:native_campaigns -->
<!-- modality:objective_mr_approval_binding -->
<!-- modality:coordination_events_scope -->

Use when **one source repo is the specification** and **one target repo is the rewrite** —
for example migrating metagit-cli from Python to Rust — under a single umbrella workspace.

Docs: [metagit-rewrite-workspace.md](https://metagit-ai.github.io/metagit-cli/metagit-rewrite-workspace/) ·
[campaigns.md](https://metagit-ai.github.io/metagit-cli/reference/campaigns/)

## When to use

- Two-repo (or small N-repo) rewrite with frozen `reference_impl`
- Module parity tracked in `_rewrite/parity-registry.yml` (BYO convention)
- Orchestrator + subagents: controller sequences phases; repo agents implement
- MR rollups and objective spine without a separate spreadsheet

## When not to use

- Simple single-repo feature work → `metagit-multi-repo` or repo-scoped skills
- Many-repo rollout without a reference pair → `metagit-campaign` alone
- You need automated AST/module diff gates → extend parity registry + CI yourself

## Quick start

```bash
export METAGIT_AGENT_MODE=true

# Bootstrap coordinator (or copy examples/metagit-rewrite/.metagit.yml)
metagit init ./rewrite-coordinator --create --template metagit-rewrite
cd rewrite-coordinator
metagit config validate
metagit project sync --project rewrite

# Campaign (if not created by init template)
metagit campaign new --slug language-rewrite --title "Language rewrite" \
  --repo rewrite/source --repo rewrite/target \
  --reference rewrite/source \
  --goal "CLI and MCP parity with reference implementation"
metagit campaign validate
metagit campaign expand --slug language-rewrite --dry-run
```

## Granularity model

| Layer | Where it lives | Granularity |
|-------|----------------|-------------|
| Workspace pair | `.metagit.yml` projects/repos | Repo |
| Campaign rollup | `_campaigns/<slug>.yml` | Repo status, MR, notes |
| Module parity | `_rewrite/parity-registry.yml` | Phase → module → paths |
| Active work | `.metagit/sessions/objectives.json` | Objective id + acceptance |
| Cross-repo edge | `graph.relationships` | Source ↔ target semantics |

Objective id convention: `rewrite-<phase>-<module>` (see `objectives.example.json` in examples).

## Orchestrator session loop

### 1) Bootstrap context

```bash
metagit context pack --tier 2 --json -c .metagit.yml
metagit prompt workspace -k session-start --text-only -c .metagit.yml
metagit campaign status --slug language-rewrite --json
```

### 2) Pick the next parity module

Read `_rewrite/parity-registry.yml`. Choose the first module with `status: pending`
in the earliest incomplete phase. Upsert a workspace objective:

```bash
echo '{"id":"rewrite-foundation-config-manager","title":"Parity: config manager","status":"in_progress","repos":["rewrite/target"],"acceptance":"Target loads source manifest fixtures"}' \
  | metagit context objective set
```

### 3) Dispatch subagent (target repo)

```bash
metagit agent profile show -p rewrite -n target --json
metagit agent apply --vendor claude_code --project rewrite --repo target
metagit context repomix --profile rewrite-target --project rewrite --repo target
metagit prompt repo -k subagent-handoff --text-only -c .metagit.yml \
  --project rewrite --repo target
```

Source analysis before large extractions:

```bash
metagit context repomix --profile rewrite-source --project rewrite --repo source
# GitNexus impact on source symbols (when indexed)
```

### 4) Record progress

```bash
metagit campaign set --slug language-rewrite --repo rewrite/target \
  --status mr-open --mr "https://github.com/org/repo/pull/1"
echo '{"id":"rewrite-foundation-config-manager","status":"done","mr_url":"https://…"}' \
  | metagit context objective set
```

Update parity registry module `status` in `_rewrite/parity-registry.yml` when acceptance passes.

### 5) Poll coordination (orchestrator)

```bash
metagit context events --campaign language-rewrite --since "<iso-cursor>" --json
metagit context handoff list --json
metagit campaign status --slug language-rewrite --json
```

## Bundled script

```bash
SKILL_ROOT="$(python3 -c "import metagit, pathlib; print(pathlib.Path(metagit.__file__).parent / 'data/skills/metagit-rewrite-campaign')")"
"$SKILL_ROOT/scripts/rewrite-orchestrator-cycle.sh" . language-rewrite
```

Or from a full skill install:

```bash
./scripts/rewrite-orchestrator-cycle.sh . language-rewrite
```

## Repomix profiles

Bundled profiles for scoped repo context:

| Profile | Use |
|---------|-----|
| `rewrite-source` | Reference implementation analysis |
| `rewrite-target` | Implementation work in the rewrite tree |

```bash
metagit context repomix --profile rewrite-source --project rewrite --repo source
metagit context repomix --profile rewrite-target --project rewrite --repo target
```

## Safety

- Treat **source as spec** until parity is explicitly marked done in the registry
- Commit `_campaigns/` and `_rewrite/` to git for reviewable rollups
- Run `metagit campaign validate` and `metagit config validate` in CI
- Use approvals for schema-breaking or destructive sync operations
- `campaign expand --dry-run` before fanning out many objectives

## Related skills

- `metagit-campaign` — campaign YAML lifecycle and expand
- `metagit-multi-repo` — cross-repo implementation sequencing
- `metagit-control-center` — MCP control-plane polling loop
- `metagit-context-pack` — tier 0/1/2 session boundaries
- `metagit-gitnexus` — impact analysis on the source repo
- `metagit-graph-maintain` — durable `graph.relationships` for source/target edges
