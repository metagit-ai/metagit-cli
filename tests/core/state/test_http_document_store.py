#!/usr/bin/env python
"""Tests for the coordination HTTP DocumentStore."""

from __future__ import annotations

import io
import json
import subprocess
import urllib.error
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from metagit.core.state.document import DocumentRef
from metagit.core.state.errors import StateBackendError, StateConflictError
from metagit.core.state.http_document import HttpDocumentStore
from metagit.core.state.plane import (
    KEY_DOCUMENT,
    NS_COORD_APPROVALS,
    NS_COORD_EVENTS,
    NS_COORD_HANDOFFS,
    NS_COORD_OBJECTIVES,
)


class _FakeResponse:
    def __init__(
        self,
        body: dict[str, Any],
        *,
        status: int = 200,
        etag: str | None = None,
    ) -> None:
        self.status = status
        self.headers = Message()
        if etag is not None:
            self.headers["ETag"] = etag
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _ref(namespace: str, *, key: str = KEY_DOCUMENT) -> DocumentRef:
    return DocumentRef(
        org_id="org-test",
        workspace_id="ws-test",
        namespace=namespace,
        key=key,
    )


def test_get_and_put_objectives_use_ops_route_and_cas(monkeypatch) -> None:
    requests: list[Any] = []
    responses = iter(
        [
            _FakeResponse({"objectives": [{"id": "o1"}]}, etag='"token-1"'),
            _FakeResponse({"objectives": [{"id": "o2"}]}, etag='"token-2"'),
        ]
    )

    def fake_urlopen(request, timeout):
        requests.append(request)
        assert timeout == 30
        return next(responses)

    monkeypatch.setattr("metagit.core.state.http_document.urllib.request.urlopen", fake_urlopen)
    store = HttpDocumentStore("https://state.example/", bearer_token="secret")
    ref = _ref(NS_COORD_OBJECTIVES)

    record = store.get(ref)
    token = store.put(ref, {"objectives": [{"id": "o2"}]}, expected="token-1")

    assert record is not None
    assert record.body == {"objectives": [{"id": "o1"}]}
    assert record.token == "token-1"
    assert token == "token-2"
    assert requests[0].full_url == "https://state.example/v3/ops/objectives"
    assert requests[0].method == "GET"
    assert requests[0].get_header("Authorization") == "Bearer secret"
    assert requests[1].method == "PUT"
    assert requests[1].get_header("If-match") == '"token-1"'
    assert json.loads(requests[1].data) == {"objectives": [{"id": "o2"}]}


@pytest.mark.parametrize(
    ("namespace", "path"),
    [
        (NS_COORD_OBJECTIVES, "/v3/ops/objectives"),
        (NS_COORD_HANDOFFS, "/v3/ops/handoffs"),
        (NS_COORD_APPROVALS, "/v3/ops/approvals?status=all"),
        (NS_COORD_EVENTS, "/v3/ops/events"),
    ],
)
def test_get_maps_coord_documents_to_existing_ops_routes(
    monkeypatch,
    namespace: str,
    path: str,
) -> None:
    requests: list[Any] = []

    def fake_urlopen(request, timeout):
        _ = timeout
        requests.append(request)
        return _FakeResponse({})

    monkeypatch.setattr("metagit.core.state.http_document.urllib.request.urlopen", fake_urlopen)

    HttpDocumentStore("https://state.example").get(_ref(namespace))

    assert requests[0].full_url == f"https://state.example{path}"


def test_append_handoff_posts_item_body(monkeypatch) -> None:
    requests: list[Any] = []
    saved = {"id": "h1", "title": "Saved handoff"}

    def fake_urlopen(request, timeout):
        _ = timeout
        requests.append(request)
        return _FakeResponse(saved)

    monkeypatch.setattr("metagit.core.state.http_document.urllib.request.urlopen", fake_urlopen)

    result = HttpDocumentStore("https://state.example").append(
        _ref(NS_COORD_HANDOFFS),
        {"id": "h1", "title": "New handoff"},
    )

    assert result == saved
    assert requests[0].method == "POST"
    assert requests[0].full_url == "https://state.example/v3/ops/handoffs"
    assert json.loads(requests[0].data) == {"id": "h1", "title": "New handoff"}


def test_coord_http_append_returns_server_normalized_handoff(monkeypatch) -> None:
    """Coord adapter must return HttpDocumentStore POST body when server normalizes fields."""
    from metagit.core.context.models import HandoffItem
    from metagit.core.state.adapters.coord import coord_bundle
    from metagit.core.workspace.context_models import utc_now_iso

    now = utc_now_iso()
    server_body = {
        "id": "h1",
        "title": "server-normalized",
        "status": "open",
        "created_by": "ops-server",
        "created_at": now,
        "updated_at": now,
    }

    def fake_urlopen(request, timeout):
        _ = timeout
        assert request.method == "POST"
        return _FakeResponse(server_body)

    monkeypatch.setattr("metagit.core.state.http_document.urllib.request.urlopen", fake_urlopen)
    store = HttpDocumentStore("https://state.example")
    bundle = coord_bundle(store, org_id="_", workspace_id="ws")
    item = HandoffItem(
        id="h1",
        title="client title",
        created_by="agent",
        created_at=now,
        updated_at=now,
    )

    saved = bundle.handoffs().append(item)

    assert saved.title == "server-normalized"
    assert saved.created_by == "ops-server"


def test_http_412_raises_state_conflict(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        _ = timeout
        raise urllib.error.HTTPError(
            request.full_url,
            412,
            "Precondition Failed",
            Message(),
            io.BytesIO(b'{"error":{"kind":"state_conflict"}}'),
        )

    monkeypatch.setattr("metagit.core.state.http_document.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(StateConflictError):
        HttpDocumentStore("https://state.example").put(
            _ref(NS_COORD_OBJECTIVES),
            {"objectives": []},
            expected="stale",
        )


def test_events_are_read_only_and_other_append_routes_are_unsupported(monkeypatch) -> None:
    def unexpected_urlopen(request, timeout):
        _ = (request, timeout)
        raise AssertionError("unsupported operations must not issue HTTP requests")

    monkeypatch.setattr(
        "metagit.core.state.http_document.urllib.request.urlopen",
        unexpected_urlopen,
    )
    store = HttpDocumentStore("https://state.example")

    with pytest.raises(StateBackendError, match="read-only"):
        store.put(_ref(NS_COORD_EVENTS), {"events": []}, expected=None)
    with pytest.raises(StateBackendError, match="handoffs"):
        store.append(_ref(NS_COORD_OBJECTIVES), {"id": "o1"})


@pytest.mark.parametrize(
    "ref",
    [
        _ref("task.graphs"),
        _ref(NS_COORD_OBJECTIVES, key="other"),
    ],
)
def test_unsupported_documents_explain_generic_state_api_is_deferred(ref: DocumentRef) -> None:
    store = HttpDocumentStore("https://state.example")

    with pytest.raises(StateBackendError, match=r"generic /v3/state.*deferred"):
        store.get(ref)


def test_list_prefix_returns_only_known_document_and_delete_is_deferred() -> None:
    store = HttpDocumentStore("https://state.example")

    refs = store.list_prefix(
        "org-test",
        "ws-test",
        NS_COORD_HANDOFFS,
        prefix="doc",
        limit=10,
    )

    assert refs == [_ref(NS_COORD_HANDOFFS)]
    with pytest.raises(StateBackendError, match=r"generic /v3/state.*deferred"):
        store.delete(_ref(NS_COORD_HANDOFFS), expected="token")


def test_describe_omits_bearer_token() -> None:
    assert HttpDocumentStore(
        "https://state.example/",
        bearer_token="secret",
    ).describe() == {
        "backend": "http",
        "base_url": "https://state.example",
        "namespaces": [
            NS_COORD_APPROVALS,
            NS_COORD_EVENTS,
            NS_COORD_HANDOFFS,
            NS_COORD_OBJECTIVES,
        ],
    }


def test_describe_sanitizes_base_url_userinfo_and_query() -> None:
    described = HttpDocumentStore(
        "https://user:secret@example.com:8787/path?token=abc",
    ).describe()

    base_url = described["base_url"]
    assert "secret" not in base_url
    assert "token=abc" not in base_url
    assert base_url == "https://example.com:8787/path?token=***"


def test_http_document_store_is_cold_importable(cold_import_environment) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    environment = cold_import_environment
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            ("from metagit.core.state.http_document import HttpDocumentStore; print(HttpDocumentStore.__name__)"),
        ],
        cwd=repository_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "HttpDocumentStore"
