#!/usr/bin/env python
"""Parametrized DocumentStore contract tests."""

from __future__ import annotations

from typing import Any, Callable, Iterator

import pytest

from metagit.core.state.document import DocumentRef, DocumentStore
from metagit.core.state.errors import StateConflictError
from metagit.core.state.local_document import LocalDocumentStore
from metagit.core.state.memory import InMemoryDocumentStore
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_OBJECTIVES, default_org_id

DOCUMENT_STORE_FACTORIES: dict[str, Callable[..., DocumentStore]] = {
    "memory": lambda **_: InMemoryDocumentStore(),
    "local": lambda tmp_path=None, **_: LocalDocumentStore(str(tmp_path)),
}


@pytest.fixture(params=list(DOCUMENT_STORE_FACTORIES.keys()) + ["dynamodb", "mongodb"])
def document_store(request, tmp_path) -> Iterator[DocumentStore]:
    if request.param == "dynamodb":
        boto3 = pytest.importorskip("boto3")
        pytest.importorskip("moto")
        from moto import mock_aws

        from metagit.core.state.dynamodb import DynamoDocumentStore

        with mock_aws():
            ddb = boto3.client("dynamodb", region_name="us-east-1")
            ddb.create_table(
                TableName="metagit-state-contract",
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
            yield DynamoDocumentStore(table="metagit-state-contract", region="us-east-1")
        return

    if request.param == "mongodb":
        mongomock = pytest.importorskip("mongomock")
        from metagit.core.state.mongodb import MongoDocumentStore

        yield MongoDocumentStore(
            uri="mongodb://localhost",
            database="metagit",
            collection="state_contract",
            client=mongomock.MongoClient(),
        )
        return

    factory = DOCUMENT_STORE_FACTORIES[request.param]
    yield factory(tmp_path=tmp_path)


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
