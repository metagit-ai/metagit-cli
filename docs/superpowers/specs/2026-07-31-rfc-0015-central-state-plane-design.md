# RFC-0015: Central State Plane — Design

**Status:** Proposed  
**Date:** 2026-07-31  
**Series:** [Central State Plane series index](2026-07-31-central-state-plane-series-index.md)  
**Supersedes / extends:** [Remote State Backend Design](2026-07-01-remote-state-backend-design.md) (keeps local + HTTP; generalizes storage)  
**Depends on:** Shipped `metagit.core.state` (`LocalFileBackend`, `RemoteHttpBackend`, `BackendBundle`)  
**Enables:** RFC-0016 (catalog), RFC-0017 (harness), RFC-0018 (ontology)  
**Plan:** (pending — write after design approval)

## Summary

Introduce a **generic document state plane** underneath Metagit’s coordination stores so the same concurrency-safe protocol can back local JSON, today’s HTTP ops API, and optional cloud document stores (DynamoDB, MongoDB). Domain services keep calling familiar backends; new work targets a single `DocumentStore` protocol keyed by `(org_id, workspace_id, namespace, key)`.

RFC-0015 **does not** move the org catalog out of `.metagit.yml` (that is 0016), does not invent a new agent runtime (0017), and does not define an ontology engine (0018). It leaves **reserved namespaces** and a stable CAS model so those RFCs plug in without another storage rewrite.

## Goals

1. Define a single `DocumentStore` protocol: `get`, `put` (CAS), `append`, `list_prefix`, `delete` (CAS), `describe`.
2. Preserve byte-compatible **local** default for objectives / handoffs / approvals / events.
3. Keep **HTTP** (`RemoteHttpBackend`) as a first-class client transport against `/v3/ops/*`.
4. Add at least one **cloud DocumentStore** implementation behind an optional extra (DynamoDB recommended as the reference; MongoDB as second).
5. Adapt existing `BackendBundle` domain protocols onto the plane via `coord.*` namespaces (no CLI verb churn).
6. Expose plane diagnostics on `metagit://gate/status` → `state_backend` (backend kind, org/workspace ids, extras installed — never secrets).
7. Document deployment shapes: direct cloud from agents, or ops server hosting the cloud store while agents use HTTP.
8. Thread-safe within a process; cross-host safety via store-level CAS.

## Non-Goals

- Org catalog / `.metagit.yml` replacement (RFC-0016).
- New task/scheduler/merge/ACL engines (reuse 0007–0013; migrate persistence in later phases).
- Ontology / Atlas / GitNexus query engines (RFC-0018).
- Multi-tenant SaaS product, billing, or hosted Metagit Cloud.
- Strong consistency across namespaces in one transaction (per-document CAS only in v1).
- Changing shapes of `Objective`, `HandoffItem`, `ApprovalRequest`.
- Requiring boto3/pymongo in the base package.
- Push/SSE for events (polling remains).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | **Approach:** generic `DocumentStore` + domain adapters (not per-domain Dynamo classes). |
| D2 | **MVP domains:** `coord.objectives`, `coord.handoffs`, `coord.approvals`, `coord.events` (and existing whole-doc envelopes). |
| D3 | **Phase 2 namespaces (interfaces only in 0015):** `acl.*` reserved; migration plan documented, not required to ship. |
| D4 | **Phase 3 namespaces (interfaces only):** `task.*`, `schedule.*`, `merge.*` reserved. |
| D5 | **Identity:** `org_id` + `workspace_id` on every key; local backend may ignore `org_id` and map `workspace_id` → filesystem root. |
| D6 | **Reference cloud backend:** DynamoDB first (conditional writes map cleanly to CAS). MongoDB second with the same protocol. |
| D7 | **Deps:** `metagit-cli[state-dynamodb]`, `metagit-cli[state-mongodb]` optional extras. |
| D8 | **Config:** extend `StateConfig.backend` literal; env `METAGIT_STATE_BACKEND`, `METAGIT_STATE_ORG_ID`, `METAGIT_STATE_WORKSPACE_ID`, plus backend-specific vars. |
| D9 | **Ops server may host cloud store:** `metagit web serve` resolves DocumentStore the same way clients do; HTTP clients unchanged. |
| D10 | **In-memory store for tests** ships in-tree (no extra). |

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│ CLI / MCP / Web / Skills                                     │
│   ObjectiveService, HandoffService, ApprovalService, …       │
└────────────────────────────┬─────────────────────────────────┘
                             │ BackendBundle (unchanged call shape)
┌────────────────────────────▼─────────────────────────────────┐
│ Domain adapters (coord.* → DocumentStore)                    │
│   objectives.json envelope ↔ namespace coord.objectives       │
└────────────────────────────┬─────────────────────────────────┘
                             │ DocumentStore Protocol
┌────────────────────────────▼─────────────────────────────────┐
│ StatePlane resolver                                          │
│   local | http | dynamodb | mongodb | memory                 │
└───┬──────────┬──────────┬──────────┬──────────┬──────────────┘
    │          │          │          │          │
 LocalJSON  HttpOps   DynamoDB*  MongoDB*   Memory
 (default)  (today)   (extra)    (extra)    (tests)
```

**Package layout (proposed):**

```text
src/metagit/core/state/
  base.py           # existing BackendBundle protocols (kept)
  document.py       # NEW: DocumentStore Protocol, DocumentRef, StateRecord
  plane.py          # NEW: StatePlane facade, namespace constants
  resolver.py       # EXTEND: resolve DocumentStore + BackendBundle
  local.py          # EXTEND: implement DocumentStore on files
  remote.py         # EXTEND: HttpDocumentStore over /v3/ops or new /v3/state/*
  dynamodb.py       # NEW (optional import): DynamoDocumentStore
  mongodb.py        # NEW (optional import): MongoDocumentStore
  memory.py         # NEW: InMemoryDocumentStore
  adapters/
    coord.py        # NEW: BackendBundle ← DocumentStore for coord.*
  errors.py         # existing
  retry.py          # existing
```

### Key model

```text
DocumentRef:
  org_id: str          # e.g. "acme" or "_" for single-tenant local
  workspace_id: str    # e.g. hash/path id or configured name
  namespace: str       # e.g. "coord.objectives"
  key: str             # e.g. "document" for whole-doc, or entity id later

StateRecord:
  ref: DocumentRef
  body: dict[str, Any] # JSON-serializable envelope
  token: StateToken    # opaque; SHA-256 for local/http; Dynamo version attr, etc.
```

### DocumentStore protocol (normative)

```python
class DocumentStore(Protocol):
  def get(self, ref: DocumentRef) -> StateRecord | None: ...
  def put(
    self,
    ref: DocumentRef,
    body: dict[str, Any],
    *,
    expected: StateToken,
  ) -> StateToken: ...
  def append(
    self,
    ref: DocumentRef,
    item: dict[str, Any],
  ) -> dict[str, Any]: ...
  def list_prefix(
    self,
    org_id: str,
    workspace_id: str,
    namespace: str,
    *,
    prefix: str = "",
    limit: int = 100,
  ) -> list[DocumentRef]: ...
  def delete(
    self,
    ref: DocumentRef,
    *,
    expected: StateToken,
  ) -> None: ...
  def describe(self) -> dict[str, Any]: ...
```

**CAS rules (all backends):**

- Empty / missing document: `get` returns `None`; first `put` uses `expected=""` or `expected=None` per existing remote contract (`If-Match: ""`).
- Stale `expected` → raise `StateConflictError`.
- `append` is a backend-defined atomic append for log-like keys (handoffs create path, events); may use composite keys under the namespace.
- Mutating services keep using `state.conflict_retries`.

### Reserved namespaces

| Namespace | Owner RFC | Phase |
|-----------|-----------|-------|
| `coord.objectives` | 0015 | MVP |
| `coord.handoffs` | 0015 | MVP |
| `coord.approvals` | 0015 | MVP |
| `coord.events` | 0015 | MVP |
| `acl.branches` | 0015 phase 2 / 0007 migrate | later |
| `acl.leases` | 0015 phase 2 | later |
| `acl.claims` | 0015 phase 2 | later |
| `acl.worktrees` | 0015 phase 2 | later |
| `acl.agents` | 0015 phase 2 | later |
| `task.graphs` | 0015 phase 3 / 0008 | later |
| `schedule.policy` | 0015 phase 3 / 0012 | later |
| `merge.queue` | 0015 phase 3 / 0011 | later |
| `catalog.workspace` | 0016 | later |
| `ontology.*` | 0018 | later |

Unknown namespaces are allowed for forward compatibility; core never writes them in 0015.

## Interfaces

### App config

```yaml
config:
  state:
    backend: local          # local | http | dynamodb | mongodb | memory
    url: ""                 # http only
    token: ""               # http bearer
    conflict_retries: 1
    org_id: ""              # default "_" when empty
    workspace_id: ""        # default: derived from session/manifest root
    dynamodb:
      table: ""
      region: ""
      endpoint_url: ""      # localstack / dynalite
    mongodb:
      uri: ""
      database: ""
      collection: "metagit_state"
```

### Environment overrides

| Variable | Purpose |
|----------|---------|
| `METAGIT_STATE_BACKEND` | `local` \| `http` \| `dynamodb` \| `mongodb` \| `memory` |
| `METAGIT_STATE_URL` | HTTP ops base (forces http when set, same as today) |
| `METAGIT_STATE_TOKEN` | Bearer token |
| `METAGIT_STATE_ORG_ID` | Org partition |
| `METAGIT_STATE_WORKSPACE_ID` | Workspace partition |
| `METAGIT_STATE_DDB_TABLE` | DynamoDB table name |
| `METAGIT_STATE_DDB_REGION` | AWS region |
| `METAGIT_STATE_DDB_ENDPOINT` | Optional custom endpoint |
| `METAGIT_STATE_MONGO_URI` | Mongo connection URI |
| `METAGIT_STATE_MONGO_DB` | Database name |

### MCP / diagnostics

`metagit://gate/status` → `state_backend` gains:

```json
{
  "backend": "dynamodb",
  "org_id": "acme",
  "workspace_id": "platform-ws",
  "url": "",
  "token_configured": false,
  "extras": {"dynamodb": true, "mongodb": false},
  "conflict_retries": 1,
  "env_overrides": { "...": true }
}
```

### Skills

Extend **`metagit-sharing-state`**: document plane backends, org/workspace ids, extras install, and “ops server hosts Dynamo” deployment. No new skill in 0015.

### CLI

No new top-level verbs required. Optional diagnostic:

```bash
metagit appconfig show --format json   # includes state block
# optional thin helper (nice-to-have, not required for MVP):
metagit context state doctor --json
```

## Persistence

### Local DocumentStore

Map `DocumentRef` → path under session root:

```text
.metagit/state/{namespace}/{key}.json
```

For MVP adapters, **also** keep reading/writing legacy paths (`sessions/objectives.json`, etc.) so existing installs do not migrate on upgrade. Dual-read: prefer plane path if present, else legacy. Dual-write: write both until a future cleanup RFC, **or** (preferred smaller blast radius) adapters keep legacy paths as the local encoding of `coord.*` whole documents (namespace is logical only). **Locked preference:** local encoding of `coord.*` remains today’s file paths; `DocumentStore` is a logical API over those files for local, and a real keyspace for cloud/http.

### HTTP DocumentStore

- MVP: map `coord.*` whole documents to existing `/v3/ops/objectives|handoffs|approvals|events` (no breaking change).
- Optional later: generic `GET/PUT /v3/state/{namespace}/{key}` for ACL/catalog namespaces when those migrate.

### DynamoDB DocumentStore (reference)

**Table schema (single-table):**

| Attribute | Role |
|-----------|------|
| `pk` | `ORG#{org_id}#WS#{workspace_id}` |
| `sk` | `NS#{namespace}#KEY#{key}` |
| `body` | JSON map / string |
| `token` | string (content hash or version uuid) |
| `updated_at` | ISO-8601 |

Conditional `put`: `attribute_not_exists(pk) OR token = :expected`.

GSI optional for `list_prefix` if needed; MVP may Query on `pk` + `sk begins_with NS#{namespace}#KEY#{prefix}`.

### MongoDB DocumentStore

Collection document:

```json
{
  "_id": {"org_id": "…", "workspace_id": "…", "namespace": "…", "key": "…"},
  "body": {},
  "token": "…",
  "updated_at": "…"
}
```

CAS via `findOneAndUpdate` filter on `_id` + `token`.

## Domain adapters (MVP)

`adapters/coord.py` implements existing `ObjectiveBackend`, `HandoffBackend`, `ApprovalBackend`, `EventsBackend` on top of `DocumentStore`:

- Whole-document keys: `key="document"` for objectives/approvals; handoffs may use `append` to `key="items"` or keep whole-doc + append helper matching today’s semantics.
- Envelope shapes unchanged: `{"objectives":[…]}`, `{"requests":[…]}`, `{"handoffs":[…]}`.

`resolve_backend(workspace_root)` continues to return `BackendBundle`; internally it builds `DocumentStore` then wraps adapters (except pure `RemoteHttpBackend` path may stay as today’s implementation until HttpDocumentStore lands — either is fine if contract tests pass).

## Concurrency & threading

- DocumentStore implementations MUST be safe for concurrent use from multiple threads in one process (no shared mutable cursor without locks).
- Cross-process / cross-host: CAS only; services retry on `StateConflictError`.
- No distributed locks in 0015.

## Security

- Cloud credentials come from the environment / AWS default chain / Mongo URI — never from `.metagit.yml`.
- `state.token`, Mongo URIs, and similar redacted in `appconfig preview`.
- `describe()` never returns secrets.
- HTTP backend keeps scheme allow-list (`http`/`https`).

## Phased delivery

### Phase 0 — Protocol + memory + contract tests

- `DocumentStore`, `DocumentRef`, `StateRecord`, namespace constants.
- `InMemoryDocumentStore`.
- Parametrized contract tests (get/put CAS/append/list_prefix/delete).

### Phase 1 — Local + HTTP as DocumentStore + coord adapters

- Local + HTTP implement `DocumentStore` (HTTP may wrap existing routes).
- `BackendBundle` via adapters; default path green on existing tests.
- Diagnostics extended on `gate/status`.
- Docs + skill updates.

### Phase 2 — DynamoDB extra

- `DynamoDocumentStore` behind lazy import.
- Packaging extra + table bootstrap notes in docs.
- Contract tests against Dynamo local / moto (prefer moto or endpoint_url).

### Phase 3 — MongoDB extra

- `MongoDocumentStore` + extra + contract tests (mongomock or testcontainer — prefer mongomock for unit speed).

### Phase 4 — ACL namespace migration plan (design-complete; optional code)

- Document mapping from `.metagit/{branches,leases,…}` → `acl.*` keys.
- No requirement to flip default persistence in 0015 ship; follow-up PR may implement.

## Acceptance

- Existing local coordination CLI/MCP tests pass with no config change.
- Contract suite passes for `memory`, `local`, and `http` (http against test ops server or mocked urllib).
- With extras installed and test endpoint, Dynamo (and later Mongo) pass the same contract suite.
- Stale CAS write raises `StateConflictError`; retry path still works via `conflict_retries`.
- `gate/status` reports effective backend, org_id, workspace_id, extras presence.
- `metagit-sharing-state` skill documents plane backends and deployment shapes.
- Modality / changelog entry when implementation lands.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| Existing `core/state`, ops HTTP, appconfig `StateConfig` | RFC-0016 catalog documents |
| | RFC-0017 harness envelopes in plane namespaces |
| | RFC-0018 ontology document slices + list/query |
| | Future ACL/task persistence migration |

## Open questions

1. Should HTTP grow generic `/v3/state/{namespace}/{key}` in Phase 1, or only when ACL/catalog needs it?  
   **Recommendation:** defer generic routes until Phase 4 / 0016; map `coord.*` to existing ops routes.
2. Workspace id derivation algorithm when unset (path hash vs manifest `name`)?  
   **Recommendation:** prefer configured id; else stable hash of resolved session root path; document clearly.
3. Dual-write local plane paths vs logical-only namespaces?  
   **Recommendation (locked above):** logical namespaces; local keeps legacy file paths for `coord.*`.

## Spec self-review notes

- No TBD placeholders left that block an implementation plan.
- Scope is one foundation RFC; catalog/harness/ontology are separate designs in this series.
- Concurrency model matches shipped remote-state semantics to avoid two CAS dialects.
