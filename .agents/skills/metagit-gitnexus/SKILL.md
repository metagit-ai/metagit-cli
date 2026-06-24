---
name: metagit-gitnexus
description: Run gitnexus analysis for a target workspace and selected project repositories before graph-dependent tasks. Use when index staleness is detected or cross-repo graph results are needed.
metadata:
  internal: true
---
# Running GitNexus Analysis

Use this skill whenever GitNexus context is stale or missing for target repositories.

## Local Wrapper (Use First)

- `./skills/metagit-gitnexus/scripts/analyze-targets.sh <workspace_root> [project_name]`

## Workflow

1. Analyze the current repository where the command is run.
2. Resolve target project repositories from `.metagit.yml`.
3. Run `npx gitnexus analyze` in each local repository path found.
4. Report per-repository success/failure and next actions.

## Manual workspace graph (`.metagit.yml` → Cypher)

Promote inferred edges first (see `metagit-graph-maintain` skill), then ingest:

```bash
./skills/metagit-gitnexus/scripts/ingest-workspace-graph.sh -c .metagit.yml
./skills/metagit-gitnexus/scripts/ingest-workspace-graph.sh -c .metagit.yml --gitnexus-repo my-umbrella --dry-run
```

Manual export + MCP:

```bash
metagit config graph export -c .metagit.yml --format tool-calls --output /tmp/graph-tool-calls.json
uv run python ./skills/metagit-gitnexus/scripts/ingest_workspace_graph.py /tmp/graph-tool-calls.json
# MCP export: metagit_export_workspace_graph_cypher
```

Schema DDL (`MetagitEntity` / `MetagitLink`) runs once per index; pass `--gitnexus-repo` when the umbrella index name differs from manifest `name`.

## GitNexus group sync (cross-index analysis)

Align `workspace.projects[]` repos with a GitNexus group for `group impact`, `group query`, and contract linking:

```bash
./skills/metagit-gitnexus/scripts/sync-group.sh -c .metagit.yml
metagit gitnexus group sync -c .metagit.yml --json
metagit gitnexus group sync -c .metagit.yml --group-name my-workspace --prune
```

MCP: `metagit_gitnexus_group_sync`

Prerequisites:

1. Each managed repo checkout exists locally and has been analyzed (`gitnexus analyze`).
2. Registry entries exist in `~/.gitnexus/registry.json` for those paths.
3. Multi-repo workspace with `workspace.projects[]` in `.metagit.yml`.

Group paths use `<project>/<repo>`; default group name is a slug of manifest `name` (stored under `~/.gitnexus/groups/<name>/`).

After sync, use GitNexus directly:

```bash
npx gitnexus group status <group>
npx gitnexus group query <group> "authentication flow"
npx gitnexus group impact <group> --repo <registryName> --target <symbol>
```

## Output Contract

Return:
- analyzed repositories
- failures and reasons
- whether graph queries are safe to run now

## Safety

- Skip repositories that do not exist locally.
- Do not mutate repo content; analysis should be read-only indexing.
