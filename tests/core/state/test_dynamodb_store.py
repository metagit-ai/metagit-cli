#!/usr/bin/env python
"""DynamoDocumentStore contract smoke (moto)."""

from __future__ import annotations

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from moto import mock_aws

from metagit.core.state.document import DocumentRef
from metagit.core.state.dynamodb import DynamoDocumentStore
from metagit.core.state.errors import StateBackendError, StateConflictError
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_OBJECTIVES, default_org_id


def _create_table(table_name: str = "metagit-state") -> None:
    ddb = boto3.client("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName=table_name,
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


@mock_aws
def test_dynamo_put_get_cas() -> None:
    _create_table()
    store = DynamoDocumentStore(table="metagit-state", region="us-east-1")
    ref = DocumentRef(default_org_id(), "ws", NS_COORD_OBJECTIVES, KEY_DOCUMENT)
    token = store.put(ref, {"objectives": []}, expected=None)
    assert store.get(ref) is not None
    with pytest.raises(StateConflictError):
        store.put(ref, {"objectives": [{"id": "x"}]}, expected="bad")
    store.put(ref, {"objectives": [{"id": "x"}]}, expected=token)


@mock_aws
def test_dynamo_append_list_prefix_delete_and_describe() -> None:
    _create_table()
    store = DynamoDocumentStore(table="metagit-state", region="us-east-1")
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
    assert info["backend"] == "dynamodb"
    assert info["table"] == "metagit-state"
    assert "secret" not in info
    assert "token" not in info
    assert "credentials" not in info
    assert "aws_access" not in str(info).lower()


def test_dynamo_missing_boto3_hint(monkeypatch) -> None:
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def _blocked(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "boto3" or name.startswith("boto3."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    for key in list(sys.modules):
        if key == "boto3" or key.startswith("boto3."):
            monkeypatch.delitem(sys.modules, key, raising=False)
    import metagit.core.state.dynamodb as dynamodb_mod

    importlib.reload(dynamodb_mod)
    with pytest.raises(StateBackendError, match=r"metagit-cli\[state-dynamodb\]"):
        dynamodb_mod.DynamoDocumentStore(table="metagit-state", region="us-east-1")
