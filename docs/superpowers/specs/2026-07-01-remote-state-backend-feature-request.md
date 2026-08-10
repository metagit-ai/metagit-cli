# Feature Request: Remote State Backend for Workspace Coordination

- **Status:** Proposed
- **Date:** 2026-07-01
- **Area:** `metagit context` (objectives, approvals, handoffs, session meta, events)
- **Related design:** `docs/superpowers/specs/2026-07-01-remote-state-backend-design.md`
- **Related plan:** `docs/superpowers/plans/2026-07-01-remote-state-backend.md`

## Problem

metagit's multi-agent coordination spine — objectives, approvals, handoffs, and
session metadata — is persisted as flat JSON files on the local filesystem under
`<workspace_root>/.metagit/`:

- `objective_store.py` → `.metagit/sessions/objectives.json`
- `handoff_store.py` → `.metagit/sessions/handoffs.json`
- `approval_store.py` → `.metagit/approvals/pending.json`
- `session_store.py` → `.metagit/sessions/_workspace.json` + per-project files

This is correct for a single operator on one machine. It breaks down the moment a
**team** wants one shared coordination spine across multiple people and hosts:

1. **No shared transport.** Each teammate has a private `.metagit/` that never
   reconciles with anyone else's. The manifest can *declare* objectives/approvals
   as "shared TODO/state across agents," but nothing makes them shared.
2. **Git is the wrong carrier for live state.** Teams reach for git to share the
   `.metagit/` tree, but objectives are *mutable, last-write-wins* documents —
   committing them per update produces a merge conflict on essentially every
   `git pull`. (Handoffs are append-only and merge cleanly; objectives and
   approvals do not.)
3. **No concurrency safety.** All stores do read-modify-write of a whole-file JSON
   document with no locking, so two concurrent writers silently clobber each other
   even on a shared filesystem (NFS, sync folder).

The net effect: metagit ships genuine multi-agent primitives (`context handoff`,
`context objective`, `context approval`, `context events --since`) that cannot
actually be shared across a team without hand-rolled, conflict-prone git plumbing.

## Desired outcome

A first-class **remote state backend** so that multiple agents and humans, on
different machines, read and write ONE canonical coordination spine — without git,
without file-level races. Concretely:

- A teammate can point metagit at a shared endpoint and have
  `metagit context objective list`, `handoff claim`, `approval request`, etc.
  operate against shared state transparently — same CLI, same output.
- The existing local-file behavior remains the zero-config default. Remote is opt-in.
- Concurrent writers are safe (no lost updates).
- `context events --since <cursor>` works against the remote so orchestrators can
  poll a shared timeline.

## Why this is tractable now (not a rewrite)

Two facts in the current codebase make this a targeted change rather than a
re-architecture:

1. **The store/service split already isolates persistence.** Every service
   (`ObjectiveService`, `HandoffService`, `ApprovalService`) talks only to a store
   object (`ObjectiveStore`, `HandoffStore`, `ApprovalStore`) whose surface is a
   handful of `load_*` / `save_*` methods. Swapping the storage substrate means
   introducing a store *interface* and a remote implementation — the service and
   CLI layers barely change.
2. **metagit already runs an HTTP ops server.** `core/web/ops_handler.py` already
   serves `/v3/ops/objectives` (GET/POST/PATCH), `/v3/ops/session`,
   `/v3/ops/session/begin`, and `/v3/ops/approvals`. The remote backend can reuse
   and extend this exact contract instead of inventing a new protocol — the server
   side is ~60% built.

## Scope

**In scope**

- A storage-backend abstraction behind the existing stores.
- An HTTP-backed remote implementation targeting the existing `/v3/ops/*` contract
  (extended to cover handoffs and events).
- Concurrency safety: optimistic concurrency (ETag/version) on the wire, and file
  locking for the local backend.
- Config + env plumbing to select and address a backend.
- Auth via a bearer token (reusing the existing `api_url` / `api_key` app-config
  fields).

**Out of scope (future work, called out in the design)**

- A hosted multi-tenant metagit service.
- Real-time server push (SSE/WebSocket) for events — polling only in v1.
- A SQL/database backend (the abstraction must not preclude it, but v1 ships
  file + HTTP only).
- Encryption-at-rest beyond filesystem permissions.

## Acceptance criteria

- With no config, all `metagit context …` commands behave exactly as today
  (local files). No regression.
- With a backend configured, two clients on different machines see each other's
  objectives, handoffs, and approvals through the normal CLI.
- Two concurrent writers to the same object cannot silently lose an update; the
  loser gets a clear conflict error and can retry.
- `context events --since <cursor>` returns a correct incremental feed from the
  remote.
- The remote backend is covered by unit tests (store contract) and an
  integration test (client ↔ in-process server round trip).
