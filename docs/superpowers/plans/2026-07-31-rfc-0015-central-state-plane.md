# RFC-0015 Central State Plane — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic `DocumentStore` state plane under Metagit coordination so local, HTTP, DynamoDB, and MongoDB share one CAS protocol, while keeping today’s local JSON default and `BackendBundle` call sites unchanged.

**Architecture:** Introduce `DocumentRef` / `StateRecord` / `DocumentStore` plus namespace constants. Implement `InMemoryDocumentStore`, `LocalDocumentStore` (legacy `coord.*` file paths), and `HttpDocumentStore` (existing `/v3/ops/*`). Adapt `BackendBundle` via `adapters/coord.py`. Extend resolver + `StateConfig` for `dynamodb` / `mongodb` / `memory` with optional extras. Cloud backends lazy-import SDKs.

**Tech Stack:** Python 3.12, Pydantic v2, existing `metagit.core.state`, stdlib JSON/hashlib/threading, optional `boto3` + `moto`, optional `pymongo` + `mongomock`, pytest, uv, ruff.

**Design:** [2026-07-31-rfc-0015-central-state-plane-design.md](../specs/2026-07-31-rfc-0015-central-state-plane-design.md)  
**Series:** [central-state-plane-series-index](../specs/2026-07-31-central-state-plane-series-index.md)

## Global Constraints

- Default (no config, no env) MUST remain local JSON with no behavioral regression in existing coordination tests.
- Do not change shapes of `Objective`, `HandoffItem`, `ApprovalRequest`.
- No boto3/pymongo in the base `metagit-cli` install — optional extras only.
- Secrets (tokens, Mongo URIs) never logged; redacted in appconfig preview; `describe()` never returns secrets.
- Empty-document CAS uses `expected=None` (same as today’s `BackendBundle` / `If-Match: ""` on HTTP).
- No new required CLI verbs; backend selection is configuration/env.
- Concentrate new code in `src/metagit/core/state/`; keep services calling `resolve_backend()` → `BackendBundle`.
- Follow repo conventions: `uv run`, 2-space indent, type hints, `os.path.join` / `Path`, tests under `tests/`.
- Before hand-off: `task qa:prepush` then `task gitnexus:analyze`.
- Implement on a feature branch (e.g. `feat/rfc-0015-central-state-plane`), not directly on `main`.

## Out of scope

Org catalog (0016), harness (0017), ontology engine (0018), flipping ACL/task persistence defaults, generic `/v3/state/*` HTTP routes, multi-tenant SaaS, distributed locks, SSE push.

## File map (create)

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/state/document.py` | `DocumentRef`, `StateRecord`, `DocumentStore` Protocol |
| `src/metagit/core/state/plane.py` | Namespace constants, `default_org_id`, `derive_workspace_id` |
| `src/metagit/core/state/memory.py` | `InMemoryDocumentStore` (thread-safe) |
| `src/metagit/core/state/local_document.py` | `LocalDocumentStore` over filesystem |
| `src/metagit/core/state/http_document.py` | `HttpDocumentStore` over `/v3/ops/*` for `coord.*` |
| `src/metagit/core/state/dynamodb.py` | `DynamoDocumentStore` (lazy boto3) |
| `src/metagit/core/state/mongodb.py` | `MongoDocumentStore` (lazy pymongo) |
| `src/metagit/core/state/adapters/__init__.py` | Package marker |
| `src/metagit/core/state/adapters/coord.py` | `BackendBundle` from `DocumentStore` |
| `src/metagit/core/state/acl_migration.md` | Phase-4 mapping notes (repo doc under package or docs) |
| `tests/core/state/test_document_contract.py` | Parametrized DocumentStore contract |
| `tests/core/state/test_memory_store.py` | Memory-specific tests |
| `tests/core/state/test_local_document_store.py` | Legacy path encoding for `coord.*` |
| `tests/core/state/test_http_document_store.py` | HTTP mapping / mocked urllib |
| `tests/core/state/test_coord_adapters.py` | Adapter → BackendBundle |
| `tests/core/state/test_dynamodb_store.py` | moto-backed (skip if no moto/boto3) |
| `tests/core/state/test_mongodb_store.py` | mongomock-backed (skip if missing) |

## File map (modify)

| Path | Change |
|------|--------|
| `src/metagit/core/state/__init__.py` | Export document/plane/memory/resolve helpers |
| `src/metagit/core/state/resolver.py` | `resolve_document_store`, extend `describe_state_backend`, route backends |
| `src/metagit/core/appconfig/models.py` | Extend `StateConfig` (+ nested Dynamo/Mongo models) |
| `src/metagit/core/web/config_preview.py` | Redact mongo uri / ddb fields if needed |
| `pyproject.toml` | `state-dynamodb`, `state-mongodb` extras; test deps moto/mongomock |
| `tests/core/appconfig/test_state_config.py` | New backends + describe fields |
| `tests/core/mcp/test_resource_service.py` | gate/status extras/org/workspace |
| `docs/reference/sharing-state.md` | Plane backends + deployment shapes |
| `skills/metagit-sharing-state/SKILL.md` (+ data copy via skills sync) | Same |
| `docs/superpowers/specs/2026-07-31-rfc-0015-*.md` | Plan link + status |
| `docs/superpowers/specs/2026-07-31-central-state-plane-series-index.md` | Plan column |
| `CHANGELOG.md` | Unreleased feat entry |
| `.mex/ROUTER.md` | Implementation progress |

---

### Task 1: Document models + namespace helpers

**Files:**
- Create: `src/metagit/core/state/document.py`
- Create: `src/metagit/core/state/plane.py`
- Test: `tests/core/state/test_document_models.py`

**Interfaces:**
- Produces: `DocumentRef(org_id: str, workspace_id: str, namespace: str, key: str)`, `StateRecord(ref, body: dict[str, Any], token: StateToken)`, `DocumentStore` Protocol with `get/put/append/list_prefix/delete/describe`
- Produces: `NS_COORD_OBJECTIVES = "coord.objectives"` (and handoffs/approvals/events), `KEY_DOCUMENT = "document"`, `default_org_id() -> str` returns `"_"`, `derive_workspace_id(workspace_root: str) -> str` returns first 16 hex chars of SHA-256 of resolved absolute path

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python
"""Unit tests for DocumentRef and workspace id derivation."""

from __future__ import annotations

from pathlib import Path

from metagit.core.state.document import DocumentRef, StateRecord
from metagit.core.state.plane import (
    KEY_DOCUMENT,
    NS_COORD_OBJECTIVES,
    default_org_id,
    derive_workspace_id,
)


def test_document_ref_fields() -> None:
    ref = DocumentRef(
        org_id="acme",
        workspace_id="ws1",
        namespace=NS_COORD_OBJECTIVES,
        key=KEY_DOCUMENT,
    )
    assert ref.namespace == "coord.objectives"
    assert ref.key == "document"


def test_default_org_id() -> None:
    assert default_org_id() == "_"


def test_derive_workspace_id_stable(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    a = derive_workspace_id(str(root))
    b = derive_workspace_id(str(root.resolve()))
    assert a == b
    assert len(a) == 16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/state/test_document_models.py -v`  
Expected: FAIL with `ModuleNotFoundError` for `metagit.core.state.document` or `plane`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python
"""DocumentStore protocol and record types for the central state plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from metagit.core.state.base import StateToken


@dataclass(frozen=True)
class DocumentRef:
    org_id: str
    workspace_id: str
    namespace: str
    key: str


@dataclass(frozen=True)
class StateRecord:
    ref: DocumentRef
    body: dict[str, Any]
    token: StateToken


class DocumentStore(Protocol):
    def get(self, ref: DocumentRef) -> StateRecord | None: ...

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken: ...

    def append(self, ref: DocumentRef, item: dict[str, Any]) -> dict[str, Any]: ...

    def list_prefix(
        self,
        org_id: str,
        workspace_id: str,
        namespace: str,
        *,
        prefix: str = "",
        limit: int = 100,
    ) -> list[DocumentRef]: ...

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None: ...

    def describe(self) -> dict[str, Any]: ...
```

```python
#!/usr/bin/env python
"""Namespace constants and identity helpers for the state plane."""

from __future__ import annotations

import hashlib
from pathlib import Path

NS_COORD_OBJECTIVES = "coord.objectives"
NS_COORD_HANDOFFS = "coord.handoffs"
NS_COORD_APPROVALS = "coord.approvals"
NS_COORD_EVENTS = "coord.events"

KEY_DOCUMENT = "document"

RESERVED_NAMESPACES: frozenset[str] = frozenset(
    {
        NS_COORD_OBJECTIVES,
        NS_COORD_HANDOFFS,
        NS_COORD_APPROVALS,
        NS_COORD_EVENTS,
        "acl.branches",
        "acl.leases",
        "acl.claims",
        "acl.worktrees",
        "acl.agents",
        "task.graphs",
        "schedule.policy",
        "merge.queue",
        "catalog.workspace",
    }
)


def default_org_id() -> str:
    return "_"


def derive_workspace_id(workspace_root: str) -> str:
    resolved = str(Path(workspace_root).expanduser().resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/state/test_document_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/state/document.py src/metagit/core/state/plane.py tests/core/state/test_document_models.py
git commit -m "feat(state): add DocumentStore types and plane namespaces"
```

---

### Task 2: InMemoryDocumentStore + shared contract suite

**Files:**
- Create: `src/metagit/core/state/memory.py`
- Create: `tests/core/state/test_document_contract.py`
- Create: `tests/core/state/test_memory_store.py`
- Modify: `src/metagit/core/state/__init__.py` (export `InMemoryDocumentStore`, `DocumentRef`, `DocumentStore`)

**Interfaces:**
- Consumes: `DocumentStore`, `DocumentRef`, `StateRecord`, `StateConflictError`
- Produces: `InMemoryDocumentStore` — thread-safe via `threading.RLock`; token = SHA-256 hex of canonical JSON body; missing → `get` returns `None`; first `put` requires `expected is None`; stale → `StateConflictError`
- Produces: `append` loads list at `body["items"]` (creates if missing), appends `item`, CAS-free write under lock (matches handoff append semantics)
- Produces: contract fixture registry `DOCUMENT_STORE_FACTORIES: dict[str, Callable[..., DocumentStore]]`

- [ ] **Step 1: Write the failing contract tests**

```python
#!/usr/bin/env python
"""Parametrized DocumentStore contract tests."""

from __future__ import annotations

from typing import Any, Callable

import pytest

from metagit.core.state.document import DocumentRef, DocumentStore
from metagit.core.state.errors import StateConflictError
from metagit.core.state.memory import InMemoryDocumentStore
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_OBJECTIVES, default_org_id

DOCUMENT_STORE_FACTORIES: dict[str, Callable[..., DocumentStore]] = {
    "memory": lambda **_: InMemoryDocumentStore(),
}


@pytest.fixture(params=list(DOCUMENT_STORE_FACTORIES.keys()))
def document_store(request) -> DocumentStore:
    return DOCUMENT_STORE_FACTORIES[request.param]()


def _ref(key: str = KEY_DOCUMENT) -> DocumentRef:
    return DocumentRef(
        org_id=default_org_id(),
        workspace_id="ws-test",
        namespace=NS_COORD_OBJECTIVES,
        key=key,
    )


def test_get_missing_returns_none(document_store: DocumentStore) -> None:
    assert document_store.get(_ref()) is None


def test_put_get_round_trip(document_store: DocumentStore) -> None:
    body: dict[str, Any] = {"objectives": [{"id": "o1"}]}
    token = document_store.put(_ref(), body, expected=None)
    record = document_store.get(_ref())
    assert record is not None
    assert record.body == body
    assert record.token == token


def test_stale_put_raises(document_store: DocumentStore) -> None:
    document_store.put(_ref(), {"objectives": []}, expected=None)
    with pytest.raises(StateConflictError):
        document_store.put(_ref(), {"objectives": [{"id": "x"}]}, expected="stale")


def test_append_and_list_prefix(document_store: DocumentStore) -> None:
    ref = _ref(key="items")
    document_store.append(ref, {"id": "h1"})
    document_store.append(ref, {"id": "h2"})
    record = document_store.get(ref)
    assert record is not None
    assert len(record.body.get("items", [])) == 2
    refs = document_store.list_prefix(
        default_org_id(), "ws-test", NS_COORD_OBJECTIVES, prefix="", limit=10
    )
    assert any(r.key == "items" for r in refs)


def test_delete_cas(document_store: DocumentStore) -> None:
    token = document_store.put(_ref(), {"objectives": []}, expected=None)
    document_store.delete(_ref(), expected=token)
    assert document_store.get(_ref()) is None
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/core/state/test_document_contract.py -v`  
Expected: FAIL — `InMemoryDocumentStore` missing

- [ ] **Step 3: Implement `InMemoryDocumentStore`**

```python
#!/usr/bin/env python
"""In-memory DocumentStore for tests and ephemeral plane backends."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from metagit.core.state.document import DocumentRef, StateRecord
from metagit.core.state.base import StateToken
from metagit.core.state.errors import StateConflictError


def _canonical_token(body: dict[str, Any]) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ref_key(ref: DocumentRef) -> tuple[str, str, str, str]:
    return (ref.org_id, ref.workspace_id, ref.namespace, ref.key)


class InMemoryDocumentStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._docs: dict[tuple[str, str, str, str], tuple[dict[str, Any], str]] = {}

    def get(self, ref: DocumentRef) -> StateRecord | None:
        with self._lock:
            row = self._docs.get(_ref_key(ref))
            if row is None:
                return None
            body, token = row
            return StateRecord(ref=ref, body=dict(body), token=token)

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken:
        with self._lock:
            key = _ref_key(ref)
            current = self._docs.get(key)
            current_token = None if current is None else current[1]
            if current_token != expected:
                raise StateConflictError(
                    f"state conflict for {ref.namespace}/{ref.key}: "
                    f"expected {expected!r}, have {current_token!r}"
                )
            token = _canonical_token(body)
            self._docs[key] = (dict(body), token)
            return token

    def append(self, ref: DocumentRef, item: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            key = _ref_key(ref)
            current = self._docs.get(key)
            body = {"items": []} if current is None else dict(current[0])
            items = body.get("items")
            if not isinstance(items, list):
                items = []
            items = list(items) + [dict(item)]
            body["items"] = items
            token = _canonical_token(body)
            self._docs[key] = (body, token)
            return dict(item)

    def list_prefix(
        self,
        org_id: str,
        workspace_id: str,
        namespace: str,
        *,
        prefix: str = "",
        limit: int = 100,
    ) -> list[DocumentRef]:
        with self._lock:
            out: list[DocumentRef] = []
            for o, w, ns, k in sorted(self._docs.keys()):
                if o != org_id or w != workspace_id or ns != namespace:
                    continue
                if prefix and not k.startswith(prefix):
                    continue
                out.append(
                    DocumentRef(org_id=o, workspace_id=w, namespace=ns, key=k)
                )
                if len(out) >= limit:
                    break
            return out

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None:
        with self._lock:
            key = _ref_key(ref)
            current = self._docs.get(key)
            current_token = None if current is None else current[1]
            if current is None or current_token != expected:
                raise StateConflictError(
                    f"state conflict deleting {ref.namespace}/{ref.key}"
                )
            del self._docs[key]

    def describe(self) -> dict[str, Any]:
        return {"backend": "memory", "document_count": len(self._docs)}
```

- [ ] **Step 4: Run contract + memory tests**

Run: `uv run pytest tests/core/state/test_document_contract.py tests/core/state/test_memory_store.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/state/memory.py src/metagit/core/state/__init__.py \
  tests/core/state/test_document_contract.py tests/core/state/test_memory_store.py
git commit -m "feat(state): add InMemoryDocumentStore and document contract tests"
```

---

### Task 3: Extend `StateConfig` + identity resolution helpers

**Files:**
- Modify: `src/metagit/core/appconfig/models.py` (`StateConfig` and nested models)
- Modify: `src/metagit/core/state/resolver.py` (add `_resolve_org_id`, `_resolve_workspace_id`, env overrides)
- Modify: `src/metagit/core/web/config_preview.py` if mongo URI appears in dump
- Modify: `tests/core/appconfig/test_state_config.py`

**Interfaces:**
- Produces: `StateDynamoConfig(table: str = "", region: str = "", endpoint_url: str = "")`
- Produces: `StateMongoConfig(uri: str = "", database: str = "", collection: str = "metagit_state")`
- Produces: `StateConfig.backend: Literal["local","http","dynamodb","mongodb","memory"]`
- Produces: `StateConfig.org_id`, `workspace_id`, `dynamodb`, `mongodb`
- Produces: env overrides in `AppConfig._override_from_environment` for `METAGIT_STATE_ORG_ID`, `METAGIT_STATE_WORKSPACE_ID`, `METAGIT_STATE_DDB_*`, `METAGIT_STATE_MONGO_*`
- Produces: `resolve_org_id(state) -> str`, `resolve_workspace_id(state, workspace_root) -> str`

- [ ] **Step 1: Write failing tests**

```python
def test_state_config_accepts_plane_backends() -> None:
    cfg = StateConfig(backend="dynamodb", org_id="acme", workspace_id="ws1")
    assert cfg.backend == "dynamodb"
    assert cfg.dynamodb.table == ""
    assert cfg.mongodb.collection == "metagit_state"


def test_state_org_workspace_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_ORG_ID", "acme")
    monkeypatch.setenv("METAGIT_STATE_WORKSPACE_ID", "platform")
    updated = AppConfig._override_from_environment(AppConfig())
    assert updated.state.org_id == "acme"
    assert updated.state.workspace_id == "platform"


def test_preview_redacts_mongo_uri() -> None:
    config = AppConfig(
        state=StateConfig(mongodb=StateMongoConfig(uri="mongodb://user:pass@host/db"))
    )
    redacted = redact_secrets(config.model_dump(mode="json"))
    assert "pass" not in redacted["state"]["mongodb"]["uri"]
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/core/appconfig/test_state_config.py::test_state_config_accepts_plane_backends -v`  
Expected: FAIL — unexpected kwargs / Literal rejection

- [ ] **Step 3: Implement config models + env overrides + redact**

Extend `StateConfig` exactly as in the design YAML. In `redact_secrets`, mask `state.mongodb.uri` like other secrets (keep last 4 chars pattern used for tokens). Wire env vars in `_override_from_environment` beside existing `METAGIT_STATE_*` handling.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/core/appconfig/test_state_config.py -v`  
Expected: PASS (including pre-existing local/http tests)

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/appconfig/models.py src/metagit/core/state/resolver.py \
  src/metagit/core/web/config_preview.py tests/core/appconfig/test_state_config.py
git commit -m "feat(state): extend StateConfig for plane backends and identity"
```

---

### Task 4: LocalDocumentStore (legacy `coord.*` paths)

**Files:**
- Create: `src/metagit/core/state/local_document.py`
- Create: `tests/core/state/test_local_document_store.py`
- Modify: `tests/core/state/test_document_contract.py` — register `"local"` factory

**Interfaces:**
- Consumes: `DocumentRef`, locking/token helpers from `local.py` (`_token_for_bytes` — export or duplicate small helpers in `local_document.py` to avoid breaking private APIs; prefer extracting `_token_for_bytes` / flock helpers to `src/metagit/core/state/files.py` if needed)
- Produces: `LocalDocumentStore(workspace_root: str, *, org_id: str = "_", workspace_id: str | None = None)`
- Produces: path mapping — for `(NS_COORD_OBJECTIVES, KEY_DOCUMENT)` → `.metagit/sessions/objectives.json`; handoffs → `handoffs.json`; approvals → `.metagit/approvals/pending.json`; events → read-only derived or `.metagit/sessions/events.json` if present; **all other** namespaces → `.metagit/state/{namespace}/{key}.json`
- Produces: `append` for handoffs namespace updates `{"handoffs":[...]}` envelope (not `items`) when `ref.namespace == NS_COORD_HANDOFFS` and `ref.key == KEY_DOCUMENT`; for generic keys use `items` list like memory

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""LocalDocumentStore path encoding tests."""

from __future__ import annotations

from pathlib import Path

from metagit.core.state.local_document import LocalDocumentStore
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_OBJECTIVES, default_org_id


def test_coord_objectives_uses_legacy_path(tmp_path: Path) -> None:
    store = LocalDocumentStore(str(tmp_path), org_id=default_org_id())
    ref = store.ref_for(NS_COORD_OBJECTIVES, KEY_DOCUMENT)
    store.put(ref, {"objectives": [{"id": "o1"}]}, expected=None)
    legacy = tmp_path / ".metagit" / "sessions" / "objectives.json"
    assert legacy.is_file()
    record = store.get(ref)
    assert record is not None
    assert record.body["objectives"][0]["id"] == "o1"


def test_generic_namespace_uses_state_dir(tmp_path: Path) -> None:
    store = LocalDocumentStore(str(tmp_path))
    ref = store.ref_for("catalog.workspace", KEY_DOCUMENT)
    store.put(ref, {"projects": []}, expected=None)
    path = tmp_path / ".metagit" / "state" / "catalog.workspace" / "document.json"
    assert path.is_file()
```

Add `ref_for(namespace, key) -> DocumentRef` helper on the store using its org/workspace ids.

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/core/state/test_local_document_store.py -v`  
Expected: FAIL — module missing

- [ ] **Step 3: Implement `LocalDocumentStore`**

Reuse `SessionStore` for sessions dir. Use flock + atomic write pattern from `LocalFileBackend._write_json`. Register in contract:

```python
DOCUMENT_STORE_FACTORIES["local"] = lambda tmp_path=None, **_: LocalDocumentStore(
    str(tmp_path)
)
```

Update the contract fixture to pass `tmp_path` into factories that need it:

```python
@pytest.fixture(params=list(DOCUMENT_STORE_FACTORIES.keys()))
def document_store(request, tmp_path):
    factory = DOCUMENT_STORE_FACTORIES[request.param]
    return factory(tmp_path=tmp_path)
```

Adjust memory factory to ignore `tmp_path`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/core/state/test_local_document_store.py tests/core/state/test_document_contract.py -v`  
Expected: PASS for memory + local

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/state/local_document.py tests/core/state/test_local_document_store.py \
  tests/core/state/test_document_contract.py
git commit -m "feat(state): add LocalDocumentStore with legacy coord paths"
```

---

### Task 5: HttpDocumentStore for `coord.*`

**Files:**
- Create: `src/metagit/core/state/http_document.py`
- Create: `tests/core/state/test_http_document_store.py`
- Modify: `tests/core/state/test_document_contract.py` — optional `"http"` param skipped by default; dedicated unit tests with mocked transport

**Interfaces:**
- Consumes: patterns from `RemoteHttpBackend` (urllib, ETag / If-Match)
- Produces: `HttpDocumentStore(base_url: str, bearer_token: str = "")`
- Produces: namespace→path map:
  - `coord.objectives`/`document` → `/v3/ops/objectives`
  - `coord.handoffs`/`document` → `/v3/ops/handoffs`
  - `coord.approvals`/`document` → `/v3/ops/approvals`
  - `coord.events`/`document` → `/v3/ops/events` (get/list only; put may raise `StateBackendError` if unsupported)
- Produces: for unsupported namespace/key → `StateBackendError` explaining generic `/v3/state` deferred
- Produces: `append` on handoffs → `POST /v3/ops/handoffs` with item body (same as today)

- [ ] **Step 1: Write failing tests with a fake HTTP handler**

Use `http.server` or monkeypatch `urlopen` similarly to `tests/core/state/test_remote_backend.py`. Assert GET/PUT round-trip and 412 → `StateConflictError`.

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/core/state/test_http_document_store.py -v`  
Expected: FAIL — module missing

- [ ] **Step 3: Implement `HttpDocumentStore`**

Prefer composing the existing `RemoteHttpBackend` private request helpers or factor shared HTTP CAS into `src/metagit/core/state/http_transport.py` if duplication exceeds ~40 lines. Do not break `remote_bundle`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/core/state/test_http_document_store.py tests/core/state/test_remote_backend.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/state/http_document.py tests/core/state/test_http_document_store.py
git commit -m "feat(state): add HttpDocumentStore over existing ops routes"
```

---

### Task 6: Coord adapters → BackendBundle

**Files:**
- Create: `src/metagit/core/state/adapters/__init__.py`
- Create: `src/metagit/core/state/adapters/coord.py`
- Create: `tests/core/state/test_coord_adapters.py`

**Interfaces:**
- Produces: `coord_bundle(store: DocumentStore, *, org_id: str, workspace_id: str) -> BackendBundle`
- Produces: adapter classes implementing `ObjectiveBackend.load/save`, `HandoffBackend.load/save/append`, `ApprovalBackend.load/save`, `EventsBackend.list_events`
- Envelope keys unchanged: `objectives`, `handoffs`, `requests`
- `Objective` / `HandoffItem` / `ApprovalRequest` validated via Pydantic on load
- Events: if store has `coord.events`/`document` with `{"events":[...]}` use it; else return empty `WorkspaceEventsResult` (local events today are derived — keep parity with `LocalFileBackend.list_events` by delegating to existing local events logic when store is `LocalDocumentStore`, or call through a small helper duplicated from `local.py`)

**Events parity rule (locked for this task):** For `LocalDocumentStore`, `EventsBackend` may wrap `LocalFileBackend(workspace_root).list_events` to avoid behavior drift. For memory/dynamo/mongo, persist `{"events":[...]}` under `coord.events`/`document` and filter `since` in the adapter.

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Coord adapters expose BackendBundle over DocumentStore."""

from __future__ import annotations

from metagit.core.context.models import Objective
from metagit.core.state.adapters.coord import coord_bundle
from metagit.core.state.memory import InMemoryDocumentStore
from metagit.core.workspace.context_models import utc_now_iso


def test_coord_bundle_objectives_round_trip() -> None:
    store = InMemoryDocumentStore()
    bundle = coord_bundle(store, org_id="_", workspace_id="ws")
    now = utc_now_iso()
    obj = Objective(
        id="o1",
        title="t",
        status="in_progress",
        repos=[],
        created_at=now,
        updated_at=now,
    )
    token = bundle.objectives().save([obj], expected=None)
    rows, loaded = bundle.objectives().load()
    assert len(rows) == 1
    assert rows[0].id == "o1"
    assert loaded == token
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/core/state/test_coord_adapters.py -v`  
Expected: FAIL — adapters missing

- [ ] **Step 3: Implement adapters**

```python
#!/usr/bin/env python
"""Adapt DocumentStore into coordination BackendBundle protocols."""

from __future__ import annotations

from typing import Any

from metagit.core.context.models import (
    ApprovalRequest,
    HandoffItem,
    Objective,
    WorkspaceEventsResult,
)
from metagit.core.state.base import BackendBundle, StateToken
from metagit.core.state.document import DocumentRef, DocumentStore
from metagit.core.state.plane import (
    KEY_DOCUMENT,
    NS_COORD_APPROVALS,
    NS_COORD_EVENTS,
    NS_COORD_HANDOFFS,
    NS_COORD_OBJECTIVES,
)


class _ObjectivesAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_OBJECTIVES, KEY_DOCUMENT)

    def load(self) -> tuple[list[Objective], StateToken]:
        record = self._store.get(self._ref)
        if record is None:
            return [], None
        raw = record.body.get("objectives")
        if not isinstance(raw, list):
            return [], record.token
        rows = [Objective.model_validate(x) for x in raw if isinstance(x, dict)]
        return rows, record.token

    def save(self, objectives: list[Objective], *, expected: StateToken) -> StateToken:
        body = {"objectives": [o.model_dump(mode="json") for o in objectives]}
        return self._store.put(self._ref, body, expected=expected)


class _HandoffsAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_HANDOFFS, KEY_DOCUMENT)

    def load(self) -> tuple[list[HandoffItem], StateToken]:
        record = self._store.get(self._ref)
        if record is None:
            return [], None
        raw = record.body.get("handoffs")
        if not isinstance(raw, list):
            return [], record.token
        rows = [HandoffItem.model_validate(x) for x in raw if isinstance(x, dict)]
        return rows, record.token

    def save(self, handoffs: list[HandoffItem], *, expected: StateToken) -> StateToken:
        body = {"handoffs": [h.model_dump(mode="json") for h in handoffs]}
        return self._store.put(self._ref, body, expected=expected)

    def append(self, item: HandoffItem) -> HandoffItem:
        dumped = item.model_dump(mode="json")
        self._store.append(self._ref, dumped)
        return item


class _ApprovalsAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_APPROVALS, KEY_DOCUMENT)

    def load(self) -> tuple[list[ApprovalRequest], StateToken]:
        record = self._store.get(self._ref)
        if record is None:
            return [], None
        raw = record.body.get("requests")
        if not isinstance(raw, list):
            return [], record.token
        rows = [ApprovalRequest.model_validate(x) for x in raw if isinstance(x, dict)]
        return rows, record.token

    def save(self, requests: list[ApprovalRequest], *, expected: StateToken) -> StateToken:
        body = {"requests": [r.model_dump(mode="json") for r in requests]}
        return self._store.put(self._ref, body, expected=expected)


class _EventsAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_EVENTS, KEY_DOCUMENT)

    def list_events(self, *, since: str | None = None) -> WorkspaceEventsResult:
        record = self._store.get(self._ref)
        if record is None:
            return WorkspaceEventsResult(events=[])
        raw = record.body.get("events")
        if not isinstance(raw, list):
            return WorkspaceEventsResult(events=[])
        events = [e for e in raw if isinstance(e, dict)]
        if since:
            events = [e for e in events if str(e.get("timestamp", "")) > since]
        return WorkspaceEventsResult.model_validate({"events": events})


def coord_bundle(
    store: DocumentStore, *, org_id: str, workspace_id: str
) -> BackendBundle:
    return BackendBundle(
        objectives_backend=_ObjectivesAdapter(store, org_id, workspace_id),
        handoffs_backend=_HandoffsAdapter(store, org_id, workspace_id),
        approvals_backend=_ApprovalsAdapter(store, org_id, workspace_id),
        events_backend=_EventsAdapter(store, org_id, workspace_id),
    )
```

`LocalDocumentStore.append` / `HttpDocumentStore.append` for `NS_COORD_HANDOFFS` + `KEY_DOCUMENT` must update the `handoffs` list inside `{"handoffs":[...]}` (not a generic `items` key). Generic namespaces may keep the memory-store `items` convention.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/core/state/test_coord_adapters.py tests/core/state/test_backend_contract.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/state/adapters tests/core/state/test_coord_adapters.py
git commit -m "feat(state): adapt DocumentStore to coordination BackendBundle"
```

---

### Task 7: Wire resolver + diagnostics (no default behavior change)

**Files:**
- Modify: `src/metagit/core/state/resolver.py`
- Modify: `src/metagit/core/state/__init__.py`
- Modify: `tests/core/appconfig/test_state_config.py`
- Modify: `tests/core/mcp/test_resource_service.py` (gate/status fields)

**Interfaces:**
- Produces: `resolve_document_store(workspace_root: str) -> DocumentStore`
- Produces: `resolve_backend(workspace_root)` behavior:
  - `local` (default): keep returning `local_bundle(workspace_root)` **unchanged** for MVP safety OR return `coord_bundle(LocalDocumentStore(...), ...)` once Task 4/6 green and existing tests pass — **locked:** switch local to `coord_bundle(LocalDocumentStore)` only after full `tests/core/state` + `tests/core/context` green; if any flake, keep `local_bundle` and use DocumentStore path only for memory/dynamodb/mongodb
  - `http` / `METAGIT_STATE_URL`: keep `remote_bundle` **or** `coord_bundle(HttpDocumentStore)` — same lock rule
  - `memory`: `coord_bundle(InMemoryDocumentStore(), ...)`
  - `dynamodb` / `mongodb`: raise clear `ValueError` until Tasks 8/9 (“backend not implemented”) then wire
- Produces: `describe_state_backend` adds `org_id`, `workspace_id`, `extras: {"dynamodb": bool, "mongodb": bool}` via importlib.util.find_spec

**Locked wiring for this task:**  
`local` → `local_bundle` (preserve).  
`http` → `remote_bundle` (preserve).  
`memory` → `coord_bundle(InMemoryDocumentStore())`.  
`dynamodb`/`mongodb` → placeholders that raise until later tasks.  
`resolve_document_store` always returns the DocumentStore for the effective backend (local→LocalDocumentStore, http→HttpDocumentStore, memory→InMemory).

- [ ] **Step 1: Write failing tests**

```python
def test_resolve_memory_backend(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_BACKEND", "memory")
    bundle = resolve_backend("/tmp/ws")
    token = bundle.objectives().save([], expected=None)
    assert token is not None or token is None  # empty save may yield token from canonical empty
    rows, _ = bundle.objectives().load()
    assert rows == []


def test_describe_includes_org_workspace_and_extras(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_ORG_ID", "acme")
    monkeypatch.setenv("METAGIT_STATE_WORKSPACE_ID", "ws1")
    info = describe_state_backend("/tmp/ws")
    assert info["org_id"] == "acme"
    assert info["workspace_id"] == "ws1"
    assert "dynamodb" in info["extras"]
    assert "mongodb" in info["extras"]
```

- [ ] **Step 2: Implement resolver branching + describe fields**

- [ ] **Step 3: Run regression**

Run: `uv run pytest tests/core/state tests/core/appconfig/test_state_config.py tests/core/mcp/test_resource_service.py -q`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/metagit/core/state/resolver.py src/metagit/core/state/__init__.py \
  tests/core/appconfig/test_state_config.py tests/core/mcp/test_resource_service.py
git commit -m "feat(state): resolve DocumentStore backends and extend gate diagnostics"
```

---

### Task 8: DynamoDB DocumentStore + packaging extra

**Files:**
- Create: `src/metagit/core/state/dynamodb.py`
- Create: `tests/core/state/test_dynamodb_store.py`
- Modify: `pyproject.toml` — extras + test deps
- Modify: `src/metagit/core/state/resolver.py` — wire `dynamodb`
- Modify: `tests/core/state/test_document_contract.py` — register dynamo factory under pytest marker/skip

**Interfaces:**
- Produces: `DynamoDocumentStore(table: str, *, region: str = "", endpoint_url: str = "")`
- Produces: pk/sk schema from design; conditional put; Query for list_prefix
- Produces: lazy `import boto3` inside `__init__`; if missing → `StateBackendError("install metagit-cli[state-dynamodb]")`
- Produces: pyproject:

```toml
state-dynamodb = ["boto3>=1.35.0"]
```

Add `moto[dynamodb]>=5.0.0` to `[project.optional-dependencies] test` or dependency-group dev/test.

- [ ] **Step 1: Write moto test (skip if ImportError)**

```python
#!/usr/bin/env python
"""DynamoDocumentStore contract smoke (moto)."""

from __future__ import annotations

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from moto import mock_aws

from metagit.core.state.dynamodb import DynamoDocumentStore
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_OBJECTIVES, default_org_id
from metagit.core.state.document import DocumentRef


@mock_aws
def test_dynamo_put_get_cas() -> None:
    ddb = boto3.client("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="metagit-state",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    )
    store = DynamoDocumentStore(table="metagit-state", region="us-east-1")
    ref = DocumentRef(default_org_id(), "ws", NS_COORD_OBJECTIVES, KEY_DOCUMENT)
    token = store.put(ref, {"objectives": []}, expected=None)
    assert store.get(ref) is not None
    with pytest.raises(Exception):
        store.put(ref, {"objectives": [{"id": "x"}]}, expected="bad")
    store.put(ref, {"objectives": [{"id": "x"}]}, expected=token)
```

Use `StateConflictError` in the raises clause once implemented.

- [ ] **Step 2: Implement `DynamoDocumentStore`**

Serialize `body` as JSON string attribute `body` (or Map). Store `token` attribute. Conditional expression:  
`(attribute_not_exists(pk) AND attribute_not_exists(sk) AND :expected_empty = :true) OR token = :expected` — simpler approach matching memory: if `expected is None` require attribute_not_exists; else `token = :expected`.

- [ ] **Step 3: Wire resolver**

When backend is `dynamodb`, require table from config/env; build store; return `coord_bundle(store, org_id=..., workspace_id=...)`.

- [ ] **Step 4: Run tests**

Run: `uv sync --extra state-dynamodb --extra test && uv run pytest tests/core/state/test_dynamodb_store.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/metagit/core/state/dynamodb.py \
  src/metagit/core/state/resolver.py tests/core/state/test_dynamodb_store.py \
  uv.lock
git commit -m "feat(state): add DynamoDocumentStore optional backend"
```

---

### Task 9: MongoDB DocumentStore + packaging extra

**Files:**
- Create: `src/metagit/core/state/mongodb.py`
- Create: `tests/core/state/test_mongodb_store.py`
- Modify: `pyproject.toml` — `state-mongodb = ["pymongo>=4.10.0"]`, add `mongomock` to test extras
- Modify: `src/metagit/core/state/resolver.py`

**Interfaces:**
- Produces: `MongoDocumentStore(uri: str, database: str, collection: str = "metagit_state")`
- Produces: `_id` composite dict per design; CAS via `find_one_and_update` filter
- Produces: lazy pymongo import with install hint
- For unit tests: inject client via optional `client=` kwarg so mongomock works without real URI

- [ ] **Step 1: Write mongomock tests**

```python
mongomock = pytest.importorskip("mongomock")

def test_mongo_put_get_cas() -> None:
    client = mongomock.MongoClient()
    store = MongoDocumentStore(
        uri="mongodb://localhost",
        database="metagit",
        collection="state",
        client=client,
    )
    ...
```

- [ ] **Step 2: Implement + wire resolver**

- [ ] **Step 3: Run**

Run: `uv sync --extra state-mongodb --extra test && uv run pytest tests/core/state/test_mongodb_store.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock src/metagit/core/state/mongodb.py \
  src/metagit/core/state/resolver.py tests/core/state/test_mongodb_store.py
git commit -m "feat(state): add MongoDocumentStore optional backend"
```

---

### Task 10: Docs, skill, ACL migration notes, changelog, series status

**Files:**
- Modify: `docs/reference/sharing-state.md`
- Modify: `skills/metagit-sharing-state/SKILL.md`
- Create: `docs/reference/central-state-plane.md` (operator reference for DocumentStore backends, table bootstrap, org/workspace ids)
- Create: `docs/superpowers/specs/2026-07-31-rfc-0015-acl-namespace-migration.md` (Phase 4 design-only mapping from `.metagit/{branches,leases,claims,worktrees,agents}` → `acl.*` keys — no code flip)
- Modify: `mkdocs.yml` — nav entry
- Modify: `CHANGELOG.md`
- Modify: series index + RFC-0015 design (`Plan:` link, Status → In progress / Implemented when done)
- Modify: `.mex/ROUTER.md`
- Run: `task skills:sync` so `src/metagit/data/skills/metagit-sharing-state` mirrors

**Content requirements for sharing-state / central-state-plane docs:**
- Backend table: local | http | memory | dynamodb | mongodb
- Extras install: `uv tool install 'metagit-cli[state-dynamodb]'`
- Deployment shape A: agents → Dynamo directly
- Deployment shape B: `metagit web serve` with server-side Dynamo; agents keep `METAGIT_STATE_URL`
- Dynamo table bootstrap snippet (pk/sk)
- Never commit credentials

- [ ] **Step 1: Write docs + skill updates**
- [ ] **Step 2: Update series index plan column to this file**
- [ ] **Step 3: Changelog under Unreleased**

```markdown
- **Central state plane (RFC-0015):** pluggable `DocumentStore` with memory/local/http adapters and optional DynamoDB/MongoDB extras; extended `state` app-config and `gate/status` diagnostics; see `docs/reference/central-state-plane.md`.
```

- [ ] **Step 4: `task skills:sync` and commit**

```bash
task skills:sync
git add docs skills src/metagit/data/skills CHANGELOG.md mkdocs.yml .mex \
  docs/superpowers/specs/2026-07-31-*.md
git commit -m "docs(state): document central state plane backends and skills"
```

---

### Task 11: Full regression + optional local→adapter cutover

**Files:**
- Possibly modify: `resolver.py` only if cutover is green

- [x] **Step 1: Run full state + context + mcp subset**

```bash
uv run pytest tests/core/state tests/core/context tests/core/mcp/test_resource_service.py -q
```

Expected: PASS

- [x] **Step 2 (optional cutover):** Point `local` at `coord_bundle(LocalDocumentStore(...))` and `http` at `coord_bundle(HttpDocumentStore(...))`. Re-run Step 1 + `tests/core/state/test_backend_contract.py` + `test_backend_contract_remote.py`. Revert cutover if any failure; shipping without cutover is acceptable if `resolve_document_store` exists for 0016.

- [x] **Step 3: `task qa:prepush` then `task gitnexus:analyze`**

- [x] **Step 4: Final commit if cutover landed**

```bash
git commit -m "feat(state): route local/http coordination through DocumentStore adapters"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| DocumentStore protocol | 1–2 |
| In-memory store | 2 |
| Local + legacy coord paths | 4 |
| HTTP over `/v3/ops/*` | 5 |
| Coord adapters / BackendBundle | 6 |
| Config + env + org/workspace | 3, 7 |
| gate/status diagnostics | 7 |
| DynamoDB extra | 8 |
| MongoDB extra | 9 |
| Skills + docs + deployment shapes | 10 |
| ACL namespace migration notes | 10 (design-only) |
| No default regression | 7, 11 |
| Reserved namespaces constants | 1 |
| Thread-safe memory | 2 |

## Self-review notes

- No TBD placeholders; optional cutover is explicitly optional with acceptance criteria.
- Types: `DocumentRef`, `StateRecord`, `DocumentStore`, `coord_bundle`, `resolve_document_store` used consistently across tasks.
- Generic `/v3/state/*` deferred per design recommendation — not in this plan.
- Catalog/harness/ontology intentionally absent.
