#!/usr/bin/env python
"""MongoDocumentStore contract smoke (mongomock)."""

from __future__ import annotations

import pytest

mongomock = pytest.importorskip("mongomock")

from metagit.core.state.document import DocumentRef
from metagit.core.state.errors import StateBackendError, StateConflictError
from metagit.core.state.mongodb import MongoDocumentStore
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_OBJECTIVES, default_org_id


def _store() -> MongoDocumentStore:
    client = mongomock.MongoClient()
    return MongoDocumentStore(
        uri="mongodb://user:secret@localhost:27017",
        database="metagit",
        collection="state",
        client=client,
    )


def test_mongo_put_get_cas() -> None:
    store = _store()
    ref = DocumentRef(default_org_id(), "ws", NS_COORD_OBJECTIVES, KEY_DOCUMENT)
    token = store.put(ref, {"objectives": []}, expected=None)
    assert store.get(ref) is not None
    with pytest.raises(StateConflictError):
        store.put(ref, {"objectives": [{"id": "x"}]}, expected="bad")
    store.put(ref, {"objectives": [{"id": "x"}]}, expected=token)


def test_mongo_append_list_prefix_delete_and_describe() -> None:
    store = _store()
    ref = DocumentRef(default_org_id(), "ws", NS_COORD_OBJECTIVES, "items")
    store.append(ref, {"id": "h1"})
    store.append(ref, {"id": "h2"})
    record = store.get(ref)
    assert record is not None
    assert len(record.body.get("items", [])) == 2
    refs = store.list_prefix(default_org_id(), "ws", NS_COORD_OBJECTIVES, prefix="it", limit=10)
    assert any(item.key == "items" for item in refs)

    token = record.token
    assert token is not None
    store.delete(ref, expected=token)
    assert store.get(ref) is None

    info = store.describe()
    assert info["backend"] == "mongodb"
    assert info["database"] == "metagit"
    assert info["collection"] == "state"
    assert "uri" not in info
    assert "secret" not in str(info).lower()
    assert "user:secret" not in str(info)


def test_mongo_missing_pymongo_hint(monkeypatch) -> None:
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def _blocked(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "pymongo" or name.startswith("pymongo."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    for key in list(sys.modules):
        if key == "pymongo" or key.startswith("pymongo."):
            monkeypatch.delitem(sys.modules, key, raising=False)
    import metagit.core.state.mongodb as mongodb_mod

    importlib.reload(mongodb_mod)
    with pytest.raises(StateBackendError, match=r"metagit-cli\[state-mongodb\]"):
        mongodb_mod.MongoDocumentStore(uri="mongodb://localhost", database="metagit")
