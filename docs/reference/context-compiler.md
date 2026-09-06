# Agent Context Compiler (RFC-0009)

<!-- modality:context_compile -->

Compile **minimum viable context** for an agent run from a project/repo scope,
optionally bound to a task node (RFC-0008) or objective. Reuses existing context
pack tiers and optional repomix profile hints — does not fork a second pack
pipeline.

## CLI

```bash
metagit context compile --project P --repo R \
  [--component NAME] [--depth N] \
  [--task-id NODE] [--graph-id G] [--objective-id ID] \
  [--tier 0|1|2] [--budget N] [--profile bugfix-local] [--json]
```

`--project` and `--repo` stay required. `--component` is optional (bare name or
`project/repo/component` that agrees with the resolved project/repo). `--depth`
defaults to `0` (origin only, cap 5) and is ignored when `--component` is
omitted. Unknown components and disagreed three-segment ids are errors, not a
repo-wide fallback. The pack stays project/repo scoped; the extra sections are
`component`, `component_graph`, and optional `effective_profile`.

Writes a `CompiledContext` JSON artifact under:

- `.metagit/tasks/<graph_id>/context/<node_id>.json` when `--task-id` resolves
- otherwise `.metagit/context/compiled/<compile_id>.json`

When a task node is provided, stamps `compiled_context_path` and
`context_budget` on the node.

## MCP

`metagit_context_compile` — required `project_name`, `repo_name`; optional
`component`, `depth`, `tier`, `budget`, `profile`, `task_id`, `graph_id`,
`objective_id`.

## Events

`ContextCompiled` rows append to `.metagit/events/context.jsonl` and appear in
`metagit context events` with `source: context`.

## Token budget

Uses the same char/4 heuristic as `metagit context pack --max-tokens`. No
required tiktoken dependency.

## Related

- [Task graph](task-graph.md) (RFC-0008)
- Context packs skill: `metagit-context-pack`
