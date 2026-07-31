# RFC-0015 Phase 4: ACL namespace migration (design only)

**Status:** Design-complete — **no code flip** in RFC-0015  
**Date:** 2026-07-31  
**Parent:** [RFC-0015 Central State Plane](2026-07-31-rfc-0015-central-state-plane-design.md)  
**Operator reference:** [central-state-plane.md](../../reference/central-state-plane.md)  
**Current ACL docs:** [agent-coordination.md](../../reference/agent-coordination.md)

## Intent

Reserve DocumentStore namespaces so ACL persistence under `.metagit/` can move
onto the central state plane in a follow-up PR without another storage rewrite.
RFC-0015 ships the mapping and reserved names only; default ACL I/O remains the
local filesystem.

## Filesystem → namespace map

Under the session/manifest root today:

| Legacy path | Plane namespace | Suggested key(s) | Notes |
|-------------|----------------|------------------|-------|
| `.metagit/branches/branches.json` | `acl.branches` | `document` | Whole-document envelope (same CAS model as `coord.*`) |
| `.metagit/leases/leases.json` | `acl.leases` | `document` | Branch lease registry |
| `.metagit/claims/claims.json` | `acl.claims` | `document` | Advisory file claims |
| `.metagit/worktrees/worktrees.json` | `acl.worktrees` | `document` | Worktree registry metadata |
| `.metagit/agents/<agent-id>.json` | `acl.agents` | `<agent-id>` | One document per agent; `list_prefix` for enumeration |

Checkout directories under `workspace.worktrees_path` (default `.worktrees/`) stay
on the local filesystem — they are git working trees, not plane documents.

`presence/presence.json` and `events/acl.jsonl` are **out of scope** for this
mapping table until a follow-up decides whether they become `acl.presence` /
append-only event keys or stay local.

## Key model (when implemented)

```text
DocumentRef(
  org_id=…,
  workspace_id=…,
  namespace="acl.branches",   # or leases | claims | worktrees | agents
  key="document",            # or agent-id for acl.agents
)
```

Local DocumentStore encoding (future): either keep dual-read of legacy paths
(preferred smaller blast radius, matching `coord.*`) or map to
`.metagit/state/{namespace}/{key}.json`. Cloud/http backends use the logical
keyspace only.

## Non-goals for this note

- Changing CLI verbs (`metagit branch|lease|worktree|claim`).
- Flipping default ACL persistence off the filesystem.
- Generic `/v3/state/{namespace}/{key}` HTTP routes (deferred until a migrate
  PR needs them; see RFC-0015 open question #1).
- Moving git worktree directories into Dynamo/Mongo.

## Acceptance for a future implement PR

1. Adapters implement existing ACL store protocols on `DocumentStore`.
2. `local` default continues to round-trip today’s JSON files bit-compatibly
   (or dual-read legacy + plane paths).
3. Contract tests cover CAS for each `acl.*` whole document.
4. Docs/skills updated; modality registry only if a new surface appears.
5. Explicit feature flag or backend opt-in before any cloud ACL default.
