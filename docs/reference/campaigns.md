# Native campaigns

<!-- modality:native_campaigns -->

Cross-project, multi-repo work tracked as **committed YAML overlays** — selection query, frozen repo list, per-repo status, MR URLs, and lessons. CLI: `metagit campaign …`.

Registry: [Modality feature registry](modality-feature-registry.md#feature-matrix).

## Storage

Default directory: **`_campaigns/`** at the manifest root (alongside `.metagit.yml`).

| Setting | Location |
|---------|----------|
| App config | `workspace.campaigns_path` in `metagit.config.yaml` (default `_campaigns`) |
| Env override | `METAGIT_WORKSPACE_CAMPAIGNS_PATH` |
| Files | `<campaigns_root>/<slug>.yml` |

Use `_campaigns` (leading underscore) so the folder does not collide with a workspace **project** named `campaigns` under the sync root. Umbrella workspaces may set `campaigns_path: knowledge/campaigns` to match existing layouts.

## Document shape

```yaml
schema_version: "1.0"
slug: tier-full-rollout
title: Full-tier agent rollout
status: active          # draft | active | completed | archived
objective_id: optional-spine-objective-id
selection:
  query: platform
  tags:
    agent_tier: full
  resolved_at: "2026-07-06T12:00:00+00:00"
repos:
  - project: platform
    repo: api
    role: primary
    status: pending     # pending | routed | mr-open | merged | blocked
    mr: https://gitlab.example.com/…/merge_requests/1
    note: waiting on review
lessons:
  - text: Prefer agent apply before dispatch
    recorded_at: "2026-07-06T18:00:00+00:00"
```

## CLI

| Command | Purpose |
|---------|---------|
| `metagit campaign list` | Summary table + rollup counts |
| `metagit campaign status --slug <s>` | Per-repo status, MRs, notes |
| `metagit campaign new --slug <s> --title "…" --query "…"` | Resolve repos via `metagit find`, freeze `repos[]` |
| `metagit campaign validate` | Schema + every repo exists in atlas |
| `metagit campaign set --slug <s> --repo project/repo --status merged [--mr URL] [--note "…"]` | Update one repo row |
| `metagit campaign expand --slug <s> [--tag k=v] [--dry-run]` | One spine objective per matching repo |

```bash
metagit campaign new --slug tier-full --title "Full tier rollout" --query "platform" \
  --tag agent_tier=full
metagit campaign status --slug tier-full --json
metagit campaign set --slug tier-full --repo platform/api --status mr-open --mr "https://…"
metagit campaign expand --slug tier-full --dry-run
```

## Coordination

### Event scoping

<!-- modality:coordination_events_scope -->

```bash
metagit context events --campaign tier-full --since "2026-07-06T00:00:00Z" --json
metagit context events --objective campaign-tier-full-platform-api --json
```

### Objectives and MR binding

<!-- modality:objective_mr_approval_binding -->

Campaign `expand` creates objectives like `campaign-<slug>-<project>-<repo>`. Objectives support optional:

- `mr_url` — merge request produced by the work item
- `approval_id` — linked approval queue entry

Set via `metagit context objective set` JSON or partial upsert; use in rollups with `campaign status`.

### Handoff leases (multi-agent)

<!-- modality:handoff_lease_heartbeat -->

Documented in [For AI agents](../agents.md#handoffs-and-leases). Campaign orchestrators should use scoped events + handoff TTL when fanning out repo work.

## MCP / Web

CLI-only in v0.13.x. Objectives/approvals/handoffs remain available via MCP and web ops routes; campaign documents are file-based and read through the CLI today.

## Related skills

- `metagit-campaign` — full lifecycle playbook
- `metagit-cli` — command index
- `metagit-multi-repo` — implementation across repos after expand

## Validation

```bash
metagit campaign validate
metagit config validate -c .metagit.yml
```

Commit `_campaigns/` (or your configured path) to git so rollups stay diffable in review.
