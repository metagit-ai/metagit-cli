# Remote State Backend Design

## Summary

Introduce a pluggable **state backend** behind metagit's workspace-coordination
stores (objectives, handoffs, approvals, session metadata) so a team can share one
canonical coordination spine across machines. Today each store hard-codes local
JSON file persistence under `<workspace_root>/.metagit/`. This design extracts a
narrow `StateBackend` interface, keeps the current filesystem behavior as the
default implementation, and adds an HTTP-backed remote implementation that targets
metagit's existing `/v3/ops/*` server contract (extended to cover handoffs and
events). Concurrency safety is added via optimistic-concurrency tokens on the wire
and advisory file locking for the local backend.

The change is deliberately layered so that the service layer
(`ObjectiveService`, `HandoffService`, `ApprovalService`) and the CLI
(`cli/commands/context.py`) are almost untouched: they continue to call
`load_*` / `save_*`, which now resolve to whichever backend is configured.

## Goals

- Add an opt-in remote state backend for objectives, handoffs, approvals, and
  session metadata.
- Preserve current local-file behavior as the zero-config default with no
  behavioral regression.
- Make concurrent writes safe: no silent lost updates on either backend.
- Support `context events --since <cursor>` against the remote.
- Reuse the existing `/v3/ops/*` HTTP contract and the `api_url` / `api_key`
  app-config fields rather than inventing a new protocol or new config surface.
- Keep the abstraction storage-agnostic so a future SQL/object-store backend can
  be added without touching services.

## Non-Goals

- No hosted multi-tenant service in this change.
- No server-side push (SSE/WebSocket) for events; polling only.
- No SQL/database backend implementation in v1 (the interface must not preclude
  it).
- No new CLI verbs; behavior is selected purely by configuration.
- No change to the shape of the persisted domain models
  (`Objective`, `HandoffItem`, `ApprovalRequest`).

## Current Architecture (as-is)

Persistence is split cleanly into stores and services already:

| Domain    | Store (persistence)                    | Service (logic)      | File on disk |
|-----------|----------------------------------------|----------------------|--------------|
| Objectives| `context/objective_store.py`           | `objective_service.py` | `.metagit/sessions/objectives.json` |
| Handoffs  | `context/handoff_store.py`             | `handoff_service.py`   | `.metagit/sessions/handoffs.json` |
| Approvals | `context/approval_store.py`            | `approval_service.py`  | `.metagit/approvals/pending.json` |
| Sessions  | `mcp/services/session_store.py`        | (used widely)          | `.metagit/sessions/_workspace.json`, `<project>.json` |
| Events    | `context/event_service.py` (derived)   | —                    | derived from the above |

Key observations that shape the design:

- Every store exposes a tiny surface: whole-document `load_*()` returning a list of
  Pydantic models and `save_*(list)` replacing the document. There is **no
  incremental update method** and **no concurrency token** today.
- Services perform read-modify-write: e.g. `ObjectiveService.upsert` loads all
  objectives, mutates the list, and saves the whole list back. This is the race
  window.
- `WorkspaceEventService` (`event_service.py`) is *derived* — it composes objective
  + approval + handoff + snapshot rows into a sorted, cursor-filterable timeline.
  It reads through the services, so once the services read from a remote backend,
  events "just work" locally; the remote server must expose an equivalent endpoint
  for cross-machine polling.
- `core/web/ops_handler.py` already serves `/v3/ops/objectives` (GET/POST/PATCH),
  `/v3/ops/session`, `/v3/ops/session/begin`, and `/v3/ops/approvals` by
  constructing the same services against a resolved `session_root`. The server side
  of remote state is substantially built.

## Proposed Architecture (to-be)

### 1. The `StateBackend` abstraction

Introduce a backend interface that the stores delegate to. The cleanest seam is at
the **store** level (not the service level), because stores already encapsulate the
"where do bytes live" question and services already depend only on stores.

Define per-domain repository protocols in a new package
`src/metagit/core/state/`:

```python
# core/state/base.py
class ObjectiveBackend(Protocol):
    def load(self) -> tuple[list[Objective], StateToken]: ...
    def save(self, objectives: list[Objective], *, expected: StateToken | None) -> StateToken: ...

class HandoffBackend(Protocol):
    def load(self) -> tuple[list[HandoffItem], StateToken]: ...
    def append(self, item: HandoffItem) -> StateToken: ...          # append-only fast path
    def replace(self, items: list[HandoffItem], *, expected: StateToken | None) -> StateToken: ...

class ApprovalBackend(Protocol):
    def load(self) -> tuple[list[ApprovalRequest], StateToken]: ...
    def save(self, requests: list[ApprovalRequest], *, expected: StateToken | None) -> StateToken: ...

class EventsBackend(Protocol):
    def events(self, *, since: str | None) -> WorkspaceEventsResult: ...
```

`StateToken` is an opaque concurrency token: for the local backend it is a content
hash or file mtime+size; for the remote backend it is an HTTP `ETag`. `save` with a
non-matching `expected` token raises `StateConflictError`.

Rationale for keeping distinct per-domain protocols rather than one giant CRUD
interface: it mirrors the existing store split, keeps each remote route mapping
obvious, and lets handoffs expose an append-only fast path (the one operation that
is safe under concurrency without a full compare-and-swap).

### 2. Two implementations

**`LocalFileBackend`** (`core/state/local.py`) — wraps the existing JSON read/write
logic currently duplicated across the three stores, plus:

- Advisory file locking (`fcntl.flock` on POSIX; best-effort no-op elsewhere)
  around read-modify-write so concurrent processes on one host are safe.
- A `StateToken` derived from a SHA-256 of the file bytes, enabling optimistic
  concurrency for callers that pass `expected`.

This becomes the single home for the JSON persistence logic that is presently
copy-pasted in `objective_store.py`, `handoff_store.py`, and `approval_store.py`
(`_read_json` / `_write_json` are near-identical in all three).

**`RemoteHttpBackend`** (`core/state/remote.py`) — a thin HTTP client against the
`/v3/ops/*` contract:

| Backend call                    | HTTP                                            |
|---------------------------------|------------------------------------------------|
| `ObjectiveBackend.load`         | `GET /v3/ops/objectives` → list + `ETag`       |
| `ObjectiveBackend.save`         | `PUT /v3/ops/objectives` w/ `If-Match: <etag>` |
| `HandoffBackend.load`           | `GET /v3/ops/handoffs`                          |
| `HandoffBackend.append`         | `POST /v3/ops/handoffs`                         |
| `HandoffBackend.replace`        | `PUT /v3/ops/handoffs` w/ `If-Match`           |
| `ApprovalBackend.load`          | `GET /v3/ops/approvals`                         |
| `ApprovalBackend.save`          | `PUT /v3/ops/approvals` w/ `If-Match`           |
| `EventsBackend.events`          | `GET /v3/ops/events?since=<cursor>`             |

The client uses only the Python standard library (`urllib.request`) to avoid adding
a runtime dependency, matching metagit's lean dependency posture. Auth is a
`Authorization: Bearer <api_key>` header. On `412 Precondition Failed` it raises
`StateConflictError`; the calling service surfaces a ret/retry message.

Note the existing server today exposes objectives as GET/POST/PATCH-by-id, not a
whole-document PUT. The design adds a whole-document `PUT /v3/ops/objectives`
(guarded by `If-Match`) so the compare-and-swap contract is uniform across domains,
and adds the missing `/v3/ops/handoffs` and `/v3/ops/events` routes. The existing
per-id POST/PATCH endpoints remain for the web UI.

### 3. Store integration

Each store gains a backend rather than opening files directly:

```python
class ObjectiveStore:
    def __init__(self, workspace_root: str, backend: ObjectiveBackend | None = None) -> None:
        self._backend = backend or resolve_backend(workspace_root).objectives()
    def load_objectives(self) -> list[Objective]:
        objectives, self._token = self._backend.load()
        return objectives
    def save_objectives(self, objectives, *, expected=None) -> None:
        self._token = self._backend.save(objectives, expected=expected or self._token)
```

Services keep their current method signatures. To get real concurrency safety, the
read-modify-write services (`ObjectiveService.upsert`, `_set_status`,
`ApprovalService.resolve`, `HandoffService._transition`) thread the token from the
`load` into the `save` and retry once on `StateConflictError` (reload → reapply the
single mutation → save). This is a small, localized change per mutating method and
is the correct place for it — the service owns the mutation intent, so it can replay
it after a conflicting reload.

### 4. Backend resolution & configuration

A single resolver decides local vs. remote:

```python
# core/state/resolver.py
def resolve_backend(workspace_root: str) -> BackendBundle:
    url = os.getenv("METAGIT_STATE_URL") or app_config.api_url
    if not url:
        return LocalBackendBundle(workspace_root)
    token = os.getenv("METAGIT_STATE_TOKEN") or app_config.api_key
    return RemoteBackendBundle(base_url=url, token=token)
```

Configuration reuses what already exists:

- **App config:** the `AppConfig` root already has `api_url`, `api_version`,
  `api_key` fields (currently unused for state). A new nested block is cleaner and
  future-proof; add an optional `state` section:

  ```yaml
  state:
    backend: local        # local | http   (default: local)
    url: ""               # http backend base URL
    token: ""             # bearer token (or via env)
    conflict_retries: 1
  ```

  `backend: local` with no URL is the default and preserves today's behavior.
- **Env overrides** (highest precedence, matching the existing
  `METAGIT_WORKSPACE_SESSION_PATH` pattern): `METAGIT_STATE_URL`,
  `METAGIT_STATE_TOKEN`, `METAGIT_STATE_BACKEND`.

### 5. Serving shared state

The design does not require a new server — it defines the contract. Two deployment
shapes are supported by the same `RemoteHttpBackend`:

1. **One orchestrator serves the spine.** An always-on metagit process runs the ops
   server (extend `metagit api serve` / the existing web ops server) bound to a
   reachable interface with a token. Teammates set `state.url` to it. This matches
   the "orchestrator owns objectives + approval queue" pattern many workspaces
   already declare in `.metagit.yml`.
2. **Any HTTP endpoint implementing the contract.** Because the contract is plain
   REST + `If-Match`, a thin service (or future hosted metagit) can back it.

Server-side concurrency: the ops handler must enforce `If-Match` by comparing
against the current on-disk token before writing (it holds the canonical
`LocalFileBackend`), returning `412` on mismatch. This makes the orchestrator the
serialization point and keeps all clients honest.

## Data & Concurrency Model

- **Objectives / approvals:** mutable documents → full compare-and-swap via
  `StateToken`. Lost-update prevention is mandatory here; this is the class of data
  that makes naive git/file sharing conflict-prone.
- **Handoffs:** append-only with claim semantics → `append` needs no CAS (server
  assigns order); only `claim`/`complete` transitions use CAS. This is why the
  handoff protocol has both `append` and `replace`.
- **Session metadata:** low-contention, last-write-wins is acceptable; still routed
  through the backend for a single source of truth but without mandatory retry.
- **Events:** read-only, derived, cursor-filtered; no concurrency concern.

## Backward Compatibility

- Default path (no `state` config, no env) constructs `LocalFileBackend` pointed at
  the same files as today. Byte-for-byte compatible JSON envelopes
  (`{"objectives": [...]}`, `{"handoffs": [...]}`, `{"requests": [...]}`).
- All store constructors keep `workspace_root` as the first positional arg; the
  `backend` arg is optional and defaults via the resolver, so existing callers
  (services, CLI, web ops, tests) compile unchanged.
- New app-config `state` block is optional with safe defaults; `appconfig`
  validation must treat it as additive.

## Security

- Remote calls require a bearer token; never logged. Reuse the redaction posture
  already applied to `api_key` in `appconfig preview`.
- Token sourced from env in preference to committed config, consistent with
  metagit's secrets-never-in-repo stance.
- Local backend continues to `chmod 0o600` files / `0o700` dirs as the stores do
  today.
- The server binds to an explicit host/port; document that exposing it beyond
  loopback requires the token and, ideally, TLS termination in front.

## Testing Strategy

- **Store-contract unit tests:** a shared test suite parametrized over
  `LocalFileBackend` and a `RemoteHttpBackend` wired to an in-process test server,
  asserting identical semantics for load/save/append/CAS-conflict.
- **Concurrency tests:** two writers, second save with a stale token raises
  `StateConflictError`; service-level retry succeeds and both mutations survive.
- **Events feed:** `since` cursor filtering identical across backends.
- **Regression:** existing `context` CLI tests pass unchanged with the default
  local backend.
- **Integration:** spin the ops server in-process, drive a full
  objective/handoff/approval round trip through `RemoteHttpBackend`, assert the
  orchestrator's on-disk files reflect the writes.

## Risks and Mitigations

- **Risk: subtle divergence between local and remote semantics.** Mitigation: the
  parametrized contract test suite is the single source of truth for behavior; both
  backends must pass it.
- **Risk: concurrency retry loops mask real conflicts.** Mitigation: bounded retry
  (default 1, configurable), and after exhaustion surface a clear conflict error
  rather than looping.
- **Risk: scope creep into a hosted service.** Mitigation: v1 ships only the
  interface + local + HTTP client + the minimal server route additions; hosting is
  explicitly out of scope.
- **Risk: added latency on every CLI call when remote.** Mitigation: single
  round-trip per operation; `load` returns the token so a subsequent `save` needs
  no extra fetch; keep it stdlib/urllib to avoid import overhead.

## Acceptance Criteria

- No config → identical local-file behavior; existing test suite green.
- Configured remote → two machines share objectives/handoffs/approvals via the
  normal CLI.
- Stale-token save is rejected (`StateConflictError` / HTTP 412); service retry
  reconciles without data loss.
- `context events --since <cursor>` works against the remote.
- Local and remote backends pass one shared contract test suite.
- New `state` app-config block validates and is redacted in `appconfig preview`.
