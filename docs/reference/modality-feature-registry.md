# Modality & feature registry

Master index of user-facing Metagit capabilities across **CLI**, **MCP**, **Web**, **documentation**, and **bundled skills**.

- **Source of truth:** [`scripts/modality-parity.yml`](https://github.com/metagit-ai/metagit-cli/blob/main/scripts/modality-parity.yml) (validated in `task qa:prepush`)
- **Registry version:** 1
- **Features tracked:** 20

When you add or change a backend feature:

1. Register it in `scripts/modality-parity.yml` (surfaces + `reference_doc`).
2. Add modality anchor comments in docs/skills: `<!-- modality:FEATURE_ID -->`
3. Run `task generate:modality-registry` (or `task generate:schema`) to refresh this table.
4. Run `task qa:prepush`.

See [Agent profile](agent-profile.md), [Campaigns](campaigns.md), and [Metagit agent](metagit-agent.md) for recent agent-native additions.

## Feature matrix

<!-- registry:table:start -->
| Feature ID | Description | CLI | MCP | Web | Docs | Skills | Reference |
|------------|-------------|-----|-----|-----|------|--------|-----------|
| `provider_source_sync_imperative` | Imperative provider discovery and manifest apply | yes | yes | — | — | — | [cli_reference.md](../cli_reference.md) |
| `provider_source_sync_manifest` | Declarative sync from workspace.projects[].sources[] | yes | yes | yes | — | — | [cli_reference.md](../cli_reference.md) |
| `source_sync_reconcile_approval` | Apply approved reconcile removals to the manifest | yes | — | yes | — | — | [agents.md](../agents.md) |
| `project_sync_refresh_sources` | Manifest source refresh before git clone sync | yes | — | yes | — | — | [cli_reference.md](../cli_reference.md) |
| `agent_profile_apply` | Structured agent_profile in manifest + vendor materialization | yes | — | — | yes | yes | [agent-profile.md](agent-profile.md) |
| `native_campaigns` | Cross-project campaign YAML overlays and CLI lifecycle | yes | — | — | yes | yes | [campaigns.md](campaigns.md) |
| `handoff_lease_heartbeat` | Handoff claim TTL, heartbeat renew, auto-release expired claims | yes | — | — | yes | yes | [agents.md](../agents.md) |
| `coordination_events_scope` | Campaign/objective filters on workspace events poll | yes | — | — | yes | yes | [campaigns.md](campaigns.md) |
| `objective_mr_approval_binding` | Objective mr_url and approval_id fields for review rollups | yes | — | — | yes | yes | [campaigns.md](campaigns.md) |
| `dispatch_profile_capabilities` | Dispatch-plan profile skill hints and apply command suggestion | yes | — | — | yes | yes | [metagit-agent.md](metagit-agent.md) |
| `acl_branch` | ACL agent branch allocate/release/cleanup/archive | yes | yes | — | yes | yes | [agent-coordination.md](agent-coordination.md) |
| `acl_lease` | ACL branch lease acquire/renew/release (distinct from handoff TTL) | yes | yes | — | yes | yes | [agent-coordination.md](agent-coordination.md) |
| `acl_worktree` | ACL isolated git worktree create/destroy/gc/status | yes | yes | — | yes | yes | [agent-coordination.md](agent-coordination.md) |
| `acl_claim` | ACL advisory file-path claims declare/check/release | yes | yes | — | yes | yes | [agent-coordination.md](agent-coordination.md) |
| `acl_manifest` | Agent execution manifest written on worktree create | yes | — | — | yes | yes | [agent-coordination.md](agent-coordination.md) |
| `task_graph` | Task DAG + intent engine create/expand/ready/complete/bind-acl | yes | yes | — | yes | yes | [task-graph.md](task-graph.md) |
| `context_compile` | Budgeted context compiler from task/objective + project/repo | yes | yes | — | yes | yes | [context-compiler.md](context-compiler.md) |
| `semantic_ownership` | Concept-level ownership declare/query/owners/conflicts plus seed/ingest | yes | yes | — | yes | yes | [semantic-ownership.md](semantic-ownership.md) |
| `merge_orchestrator` | Local merge queue, validation gate, and integration orchestration | yes | yes | — | yes | yes | [merge-orchestrator.md](merge-orchestrator.md) |
| `agent_scheduler` | Score ready task nodes and emit schedule decisions with dispatch hints | yes | yes | — | yes | yes | [agent-scheduler.md](agent-scheduler.md) |
<!-- registry:table:end -->

## Surface legend

| Column | Meaning |
|--------|---------|
| CLI | `metagit …` command group present |
| MCP | MCP tool registered |
| Web | `metagit web serve` HTTP route or SPA |
| Docs | Narrative reference under `docs/` |
| Skills | Bundled skill playbook under `src/metagit/data/skills/` |

A cell shows **yes** when the feature declares markers for that surface in `modality-parity.yml`. **—** means intentionally CLI-only, not yet built, or documented elsewhere.

## Related

- [For AI agents](../agents.md)
- [Skills catalog](../skills.md)
- [Sharing state (multi-agent)](sharing-state.md)
