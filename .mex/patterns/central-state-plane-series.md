---
name: central-state-plane-series
description: Design and implement RFC-0015–0018 central state plane / org control plane work.
last_updated: 2026-07-31
---

# Central State Plane Series

## When to use
Working on shared central state (DocumentStore, Dynamo/Mongo/HTTP), org catalog without git-as-sole-truth, agentic workload harness, or pluggable ontology adapters.

## Steps
1. Read the series index: `docs/superpowers/specs/2026-07-31-central-state-plane-series-index.md`.
2. Implement **RFC-0015 first** — do not start 0016–0018 until DocumentStore + coord adapters are stable.
3. Keep `local` as default; cloud SDKs only via optional extras.
4. Reuse existing `StateToken` / `StateConflictError` CAS semantics — no second concurrency dialect.
5. Reserved namespaces (`catalog.*`, `harness.*`, `ontology.*`, `acl.*`) are extension points; do not invent parallel stores.
6. After design approval, write plans under `docs/superpowers/plans/2026-07-31-*.md` (gitignored until allowlisted — already allowlisted for 2026-07-31).
7. Update series index status + `.mex/ROUTER.md` when a phase ships.
8. Local document paths must reject traversal and separators, verify resolved paths remain under the state root or exact legacy path, and use locked atomic replacement.
9. Treat `coord.events/document` as derived read-only state: reads may consume an existing legacy file, but all mutations must fail.

## Verify
- Contract tests for DocumentStore backends.
- Existing coordination tests green with no config.
- `metagit://gate/status` → `state_backend` diagnostics without secrets.
- Skills/docs updated (`metagit-sharing-state` for 0015).
