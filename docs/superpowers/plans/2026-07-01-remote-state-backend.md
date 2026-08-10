# Remote State Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in remote state backend for metagit's coordination spine
(objectives, handoffs, approvals, session metadata, events) so a team can share one
canonical state across machines, while preserving today's local-file behavior as
the zero-config default and adding concurrency safety to both paths.

**Architecture:** Extract a `StateBackend` abstraction into a new
`src/metagit/core/state/` package. Provide a `LocalFileBackend` (wrapping the JSON
logic currently duplicated in the three stores, plus file locking + content-hash
tokens) and a `RemoteHttpBackend` (stdlib `urllib` client against the existing
`/v3/ops/*` contract, extended with whole-document PUT + `/v3/ops/handoffs` +
`/v3/ops/events`). Stores delegate to a resolver-selected backend; mutating
services thread a concurrency token and retry once on conflict. Config reuses the
`api_url`/`api_key` app-config fields plus a new optional `state` block and env
overrides.

**Tech Stack:** Python 3.12, Pydantic v2, Click, stdlib `urllib`/`fcntl`, pytest,
uv, ruff.

## Global Constraints

- Default (no config, no env) MUST be byte-for-byte compatible with current local
  JSON files; no behavioral regression in existing `context` CLI tests.
- No new runtime dependencies — remote client uses stdlib `urllib.request`.
- Do not change the shape of `Objective`, `HandoffItem`, `ApprovalRequest`.
- Store constructors keep `workspace_root` as the first positional arg; any new arg
  is optional with a resolver default.
- No new CLI verbs; backend selection is configuration-only.
- Secrets (bearer token) never logged; redacted in `appconfig preview`.
- Prefer the smallest diff to services and CLI; concentrate new code in
  `core/state/`.
- Follow repo conventions: `uv run` for all commands, ruff clean, tests colocated
  under `tests/`.

---

### Task 1: Establish the state package and backend interfaces (test-first)

**Files:**
- Create: `src/metagit/core/state/__init__.py`
- Create: `src/metagit/core/state/base.py`
- Create: `src/metagit/core/state/errors.py`
- Create: `tests/core/state/test_backend_contract.py`

**Interfaces:**
- Produces: `StateToken` type, `StateConflictError`, and Protocols
  `ObjectiveBackend`, `HandoffBackend`, `ApprovalBackend`, `EventsBackend`.
- Produces: a reusable, backend-parametrized contract test suite (fixtures only in
  this task; concrete backends registered in later tasks).

- [x] **Step 1: Write the failing contract test skeleton.** Define a pytest
  fixture `backend_bundle` parametrized (initially with a single placeholder) and
  assertions for: `load` returns `([], token)` when empty; `save` then `load`
  round-trips; `save` with a stale token raises `StateConflictError`; handoff
  `append` adds one item without needing a prior token. Mark it `xfail`/skip until a
  concrete backend exists.
- [x] **Step 2:** Implement `errors.py` (`StateConflictError(Exception)`,
  `StateBackendError`) and `base.py` (`StateToken = str | None`, the four
  `Protocol` classes, and a `BackendBundle` dataclass exposing
  `.objectives()`, `.handoffs()`, `.approvals()`, `.events()`).
- [x] **Step 3:** Run `uv run ruff check src/metagit/core/state` and
  `uv run pytest tests/core/state -q`; confirm the suite collects and the skeleton
  runs (skipped/xfail is acceptable at this task boundary).

---

### Task 2: Implement `LocalFileBackend` with locking and content tokens

**Files:**
- Create: `src/metagit/core/state/local.py`
- Modify: `tests/core/state/test_backend_contract.py`
- Create: `tests/core/state/test_local_backend.py`

**Interfaces:**
- Consumes: `Objective`, `HandoffItem`, `ApprovalRequest` from
  `core/context/models.py`; `SessionStore` for sessions-dir resolution.
- Produces: `LocalFileBackend` implementing all four backends, plus a `local_bundle`
  factory used by the contract suite.

- [x] **Step 1:** Write `test_local_backend.py` asserting: files land at the same
  paths as today (`.metagit/sessions/objectives.json`,
  `.metagit/sessions/handoffs.json`, `.metagit/approvals/pending.json`); JSON
  envelope keys unchanged (`objectives`/`handoffs`/`requests`); token changes after
  a write; stale-token `save` raises `StateConflictError`.
- [x] **Step 2:** Implement `LocalFileBackend`. Centralize the `_read_json` /
  `_write_json` logic (currently duplicated in `objective_store.py`,
  `handoff_store.py`, `approval_store.py`) here. Token = SHA-256 of file bytes
  (empty/missing file → `None`). Wrap read-modify-write in `fcntl.flock` on POSIX
  (best-effort no-op where unavailable). Preserve `chmod 0o600`/`0o700`.
- [x] **Step 3:** Register `local_bundle` in the contract suite fixture and remove
  the skip; the shared contract tests must pass against `LocalFileBackend`.
- [x] **Step 4:** `uv run pytest tests/core/state -q` green; `uv run ruff check`
  clean.

---

### Task 3: Route the existing stores through the backend (default = local)

**Files:**
- Modify: `src/metagit/core/context/objective_store.py`
- Modify: `src/metagit/core/context/handoff_store.py`
- Modify: `src/metagit/core/context/approval_store.py`
- Create: `src/metagit/core/state/resolver.py`
- Modify: `tests/` (existing context store/service tests, if any assert file IO
  directly)

**Interfaces:**
- Consumes: `resolve_backend(workspace_root)` → `BackendBundle`.
- Produces: stores that delegate to a backend while keeping their public method
  names (`load_objectives`/`save_objectives`, `load_handoffs`/`save_handoffs`,
  `load_requests`/`save_requests`) and constructor signature
  (`(workspace_root, backend=None)`).

- [x] **Step 1:** Implement `resolver.py`: read `METAGIT_STATE_URL` /
  `METAGIT_STATE_BACKEND` env, else app-config `state` block (Task 6 adds the
  model; until then default to local), returning a `LocalBackendBundle` when no URL
  is set. For this task it may return local unconditionally.
- [x] **Step 2:** Refactor the three stores to hold a backend and delegate. Keep the
  `path` property (some callers/tests read it) sourced from the local backend for
  compatibility. Track the last-loaded token on the store instance so a subsequent
  `save_*` can pass it as `expected`.
- [x] **Step 3:** Run the FULL existing suite: `uv run pytest -q`. The default local
  path must be a no-op change behaviorally. Fix any test that reached into private
  `_read_json`/`_write_json` by pointing it at the backend or the store's public
  API.
- [x] **Step 4:** `uv run ruff check` clean.

---

### Task 4: Add concurrency-safe retry in mutating services

**Files:**
- Modify: `src/metagit/core/context/objective_service.py`
- Modify: `src/metagit/core/context/approval_service.py`
- Modify: `src/metagit/core/context/handoff_service.py`
- Create: `tests/core/state/test_service_concurrency.py`

**Interfaces:**
- Consumes: `StateConflictError`.
- Produces: mutating methods that retry once (configurable) on conflict by
  reloading and reapplying the single mutation.

- [x] **Step 1:** Write `test_service_concurrency.py`: simulate a stale write (two
  services sharing one backend; A loads, B writes, A writes) and assert both
  mutations survive after A's retry; assert bounded retry surfaces
  `StateConflictError` when exhausted.
- [x] **Step 2:** Wrap the read-modify-write bodies of `ObjectiveService.upsert`,
  `upsert_partial`, `edit`, `_set_status`; `ApprovalService.resolve`/mutations; and
  `HandoffService._transition` in a small `_with_retry` helper that catches
  `StateConflictError`, reloads, replays the intent, and re-saves. `HandoffService.create`
  should use the backend `append` fast path (no CAS).
- [x] **Step 3:** `uv run pytest tests/core/state -q` and the full context suite
  green; `uv run ruff check` clean.

---

### Task 5: Implement `RemoteHttpBackend` (stdlib client)

**Files:**
- Create: `src/metagit/core/state/remote.py`
- Create: `tests/core/state/test_remote_backend.py`

**Interfaces:**
- Consumes: `/v3/ops/*` contract (see Task 7 for server routes added).
- Produces: `RemoteHttpBackend` implementing all four backends over
  `urllib.request`, with `Authorization: Bearer` and `If-Match`/`ETag` handling;
  `remote_bundle` factory for the contract suite.

- [x] **Step 1:** Write `test_remote_backend.py` using an in-process
  `http.server`-based stub (or the real ops handler from Task 7) to assert:
  GET returns list + token from `ETag`; PUT with matching `If-Match` succeeds and
  returns a new token; PUT with stale `If-Match` → `412` → `StateConflictError`;
  handoff `append` POSTs one item; `events(since=...)` returns filtered rows.
- [x] **Step 2:** Implement `RemoteHttpBackend`: map each backend method to the
  route table in the design doc; parse `ETag` into `StateToken`; send `If-Match` on
  writes; translate `412` → `StateConflictError`, other non-2xx → `StateBackendError`;
  bearer token from bundle config; stdlib only.
- [x] **Step 3:** Register `remote_bundle` in the contract suite; the SAME shared
  contract tests from Task 1 must pass against the remote backend (this is the
  local/remote parity guarantee).
- [x] **Step 4:** `uv run pytest tests/core/state -q` green; `uv run ruff check`
  clean.

---

### Task 6: Add the `state` app-config block and finish the resolver

**Files:**
- Modify: `src/metagit/core/appconfig/models.py`
- Modify: `src/metagit/core/state/resolver.py`
- Modify: `src/metagit/data/metagit.config.yaml` (defaults, if defaults are shipped there)
- Modify: `schemas/metagit_config.schema.json` (regenerate)
- Create/Modify: `tests/core/appconfig/test_state_config.py`

**Interfaces:**
- Produces: `StateConfig` model (`backend: local|http`, `url`, `token`,
  `conflict_retries: int = 1`) nested on `AppConfig` as optional `state`.
- Produces: resolver precedence env > app-config > default-local.

- [x] **Step 1:** Write config tests: default config has `state.backend == "local"`
  and constructs a local bundle; setting `state.url` (or `METAGIT_STATE_URL`)
  selects the remote bundle; env overrides config; `appconfig preview` redacts
  `state.token`.
- [x] **Step 2:** Add `StateConfig` to `models.py` and an optional
  `state: StateConfig = Field(default_factory=StateConfig)` on `AppConfig`. Ensure
  additive validation (existing configs without `state` still load).
- [x] **Step 3:** Finish `resolver.py` precedence and wire redaction into the
  existing `appconfig preview` secret-redaction path.
- [x] **Step 4:** Regenerate the JSON schema
  (`uv run metagit appconfig schema …` per the repo's schema task) and commit the
  updated `schemas/metagit_config.schema.json`.
- [x] **Step 5:** `uv run pytest tests/core/appconfig -q` and full suite green;
  ruff clean.

---

### Task 7: Extend the ops server to serve the full contract

**Files:**
- Modify: `src/metagit/core/web/ops_handler.py`
- Modify: `tests/` for web ops (add handoffs/events/PUT coverage)

**Interfaces:**
- Produces: `PUT /v3/ops/objectives` and `PUT /v3/ops/approvals` (whole-document,
  `If-Match` enforced), `GET/POST/PUT /v3/ops/handoffs`, and `GET /v3/ops/events`.
- Consumes: the same services, now backed by the orchestrator's `LocalFileBackend`.

- [x] **Step 1:** Write handler tests: PUT with correct `If-Match` writes and
  returns new `ETag`; stale `If-Match` → `412`; `GET /v3/ops/handoffs` and
  `POST` (append) work; `GET /v3/ops/events?since=` returns
  `WorkspaceEventsResult`. Preserve existing GET/POST/PATCH objective routes for the
  web UI.
- [x] **Step 2:** Add the routes in `handle(...)` and implement handlers that
  compute/enforce the token via the local backend before writing; emit `ETag` on
  responses. Reuse `WorkspaceEventService` for the events route.
- [x] **Step 3:** End-to-end integration test: run the handler in-process, drive it
  with `RemoteHttpBackend`, assert a full objective + handoff + approval round trip
  and that the orchestrator's on-disk JSON reflects the writes.
- [x] **Step 4:** Full suite `uv run pytest -q` green; ruff clean.

---

### Task 8: Docs, changelog, and verification sweep

**Files:**
- Modify: `docs/` (a short "Sharing state across a team" page under the existing
  docs tree; link from the context/coordination docs)
- Modify: `CHANGELOG.md`
- Modify: `llms.txt` if it enumerates config/env surfaces

- [x] **Step 1:** Document the `state` config block, the three env vars, the two
  deployment shapes (orchestrator-serves vs. any-HTTP-endpoint), and the security
  note (token required beyond loopback, prefer TLS in front).
- [x] **Step 2:** Add a CHANGELOG entry under the next version.
- [x] **Step 3:** Final verification:
  - `uv run pytest -q` (full suite) green.
  - `uv run ruff check` clean.
  - Manual smoke: with no config, `uv run metagit context objective list` behaves as
    before; with `METAGIT_STATE_URL` pointed at a locally-served ops server, two
    separate working dirs see the same objectives/handoffs.
- [x] **Step 4:** Confirm no regression in existing `context`, `appconfig`, and web
  ops test modules.

---

## Sequencing Notes

- Tasks 1→4 deliver concurrency-safe **local** state (already valuable on a shared
  filesystem) without any remote surface.
- Tasks 5→7 add the remote path; Task 5 can be tested against a stub before Task 7
  lands the real routes, but Task 7's integration test is the acceptance gate.
- The parametrized contract suite (Task 1) is the north star: local (Task 2) and
  remote (Task 5) must both pass it — that is the local/remote parity guarantee.
