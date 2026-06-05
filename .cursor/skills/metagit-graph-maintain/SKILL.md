---
name: metagit-graph-maintain
description: >-
  Discover, suggest, promote, validate, and ingest cross-repo graph.relationships
  in .metagit.yml for GitNexus overlay and dependency maps. Use for first-time
  graph bootstrap or ongoing workspace graph maintenance.
metadata:
  internal: true
---
# Workspace graph maintenance

Use this skill to discover and keep durable cross-repo edges in `.metagit.yml` `graph.relationships`, then sync them into GitNexus.

## When to use

| Phase | Trigger |
|-------|---------|
| **Discover** | New umbrella workspace, empty `graph.relationships`, or first graph authoring pass |
| **Maintain** | After adding repos, promoting inferred deps, or refreshing GitNexus overlay |

## First-time discovery (report only)

Do **not** apply until the operator approves the discovery report.

```bash
export METAGIT_AGENT_MODE=true
metagit prompt workspace -c .metagit.yml -k graph-discover --text-only
metagit workspace list -c .metagit.yml --json
metagit config graph suggest -c .metagit.yml --json --include-declared --min-confidence all
```

Deliver a **Graph Discovery Report**:

- inferred edges grouped by confidence (`high` / `medium` / `low`)
- gap pairs with no machine path (need operator interview)
- `proposed_manual_edges[]` from interview answers
- `operations_preview` JSON — **not applied**

After sign-off, continue with the maintenance workflow below (or `metagit prompt workspace -k graph-maintain`).

## Maintenance workflow

### 1. Bootstrap context

```bash
export METAGIT_AGENT_MODE=true
metagit prompt workspace -c .metagit.yml -k graph-maintain --text-only
metagit workspace list -c .metagit.yml --json
```

### 2. Suggest candidates

```bash
metagit config graph suggest -c .metagit.yml --json
metagit config graph suggest -c .metagit.yml --min-confidence high --json
```

MCP: `metagit_suggest_graph_relationships`

Review `candidates[]` for `confidence`, `evidence`, and `source_edge_type`. Skip low-confidence edges unless the operator approves.

### 3. Preview and apply

```bash
# Save operations from suggest JSON to ops.json, then:
metagit config preview -c .metagit.yml --file ops.json

# Apply all suggested candidates (medium+ confidence by default)
metagit config graph suggest -c .metagit.yml --apply

# Apply selected ids only
metagit config graph suggest -c .metagit.yml --apply \
  --candidate-id alpha-api-to-beta-worker-depends_on

metagit config validate -c .metagit.yml
```

MCP: `metagit_apply_graph_relationships` (`dry_run: true` to preview, `save: true` to persist)

### 4. Export and ingest GitNexus overlay

```bash
./skills/metagit-gitnexus/scripts/ingest-workspace-graph.sh -c .metagit.yml
```

Or manually:

```bash
metagit config graph export -c .metagit.yml --format tool-calls --output /tmp/graph-tool-calls.json
```

Then run each `gitnexus_cypher` call (or use the ingest script).

### 5. Refresh per-repo indexes

```bash
./skills/metagit-gitnexus/scripts/analyze-targets.sh <workspace_root> <project>
```

## Output contract

Return:

- candidate count and applied count
- validation result after apply
- GitNexus ingest status (schema + statement count)
- repos still stale/missing in GitNexus registry

## Safety

- Default `--min-confidence medium`; require operator approval for `--min-confidence all`
- Never remove or rewrite existing manual relationships
- Use `--dry-run` / `dry_run: true` before first apply in a workspace
- Do not ingest Cypher until `metagit config validate` passes
