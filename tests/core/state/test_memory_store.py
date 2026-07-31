#!/usr/bin/env python
"""InMemoryDocumentStore-specific tests."""

from __future__ import annotations

from metagit.core.state.document import DocumentRef
from metagit.core.state.memory import InMemoryDocumentStore
from metagit.core.state.plane import NS_COORD_OBJECTIVES, default_org_id


def _ref(key: str = "doc") -> DocumentRef:
    return DocumentRef(
        org_id=default_org_id(),
        workspace_id="ws-mem",
        namespace=NS_COORD_OBJECTIVES,
        key=key,
    )


def test_describe_reports_backend_and_count() -> None:
    store = InMemoryDocumentStore()
    assert store.describe() == {"backend": "memory", "document_count": 0}
    store.put(_ref(), {"objectives": []}, expected=None)
    assert store.describe() == {"backend": "memory", "document_count": 1}


def test_get_returns_shallow_copy_of_body() -> None:
    store = InMemoryDocumentStore()
    body = {"objectives": [{"id": "o1"}], "version": 1}
    store.put(_ref(), body, expected=None)
    record = store.get(_ref())
    assert record is not None
    record.body["version"] = 2
    record.body["extra"] = "x"
    again = store.get(_ref())
    assert again is not None
    assert again.body["version"] == 1
    assert "extra" not in again.body
