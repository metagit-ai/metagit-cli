#!/usr/bin/env python
"""Tests for state backend app-config wiring."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from metagit.core.appconfig.models import AppConfig, StateConfig, StateMongoConfig
from metagit.core.context.models import Objective
from metagit.core.state.http_document import HttpDocumentStore
from metagit.core.state.identity import resolve_org_id, resolve_workspace_id
from metagit.core.state.local_document import LocalDocumentStore
from metagit.core.state.memory import InMemoryDocumentStore
from metagit.core.state.resolver import (
    describe_state_backend,
    resolve_backend,
    resolve_document_store,
)
from metagit.core.web.config_preview import redact_secrets
from metagit.core.workspace.context_models import utc_now_iso


def test_default_state_config_is_local() -> None:
    config = AppConfig()
    assert config.state.backend == "local"
    assert config.state.url == ""
    bundle = resolve_backend("/tmp/unused")
    objectives: list[Objective] = bundle.objectives().load()[0]
    assert objectives == []


def test_state_url_env_selects_http_document_store() -> None:
    with patch.dict(os.environ, {"METAGIT_STATE_URL": "http://127.0.0.1:8787"}, clear=False):
        bundle = resolve_backend("/tmp/unused")
        backend = bundle.objectives()
        assert isinstance(getattr(backend, "_store", None), HttpDocumentStore)


def test_state_env_overrides_config_fields() -> None:
    config = AppConfig()
    with patch.dict(
        os.environ,
        {
            "METAGIT_STATE_URL": "http://example.test",
            "METAGIT_STATE_BACKEND": "http",
            "METAGIT_STATE_TOKEN": "secret-token",
        },
        clear=False,
    ):
        updated = AppConfig._override_from_environment(config)
    assert updated.state.url == "http://example.test"
    assert updated.state.backend == "http"
    assert updated.state.token == "secret-token"


def test_appconfig_preview_redacts_state_token() -> None:
    config = AppConfig(state=StateConfig(token="super-secret-token"))
    redacted = redact_secrets(config.model_dump(mode="json"))
    assert redacted["state"]["token"] == "***oken"


def test_state_config_accepts_plane_backends() -> None:
    config = StateConfig(backend="dynamodb", org_id="acme", workspace_id="ws1")
    assert config.backend == "dynamodb"
    assert config.dynamodb.table == ""
    assert config.mongodb.collection == "metagit_state"


def test_state_plane_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_ORG_ID", "acme")
    monkeypatch.setenv("METAGIT_STATE_WORKSPACE_ID", "platform")
    monkeypatch.setenv("METAGIT_STATE_DDB_TABLE", "state-table")
    monkeypatch.setenv("METAGIT_STATE_DDB_REGION", "us-east-1")
    monkeypatch.setenv("METAGIT_STATE_DDB_ENDPOINT", "http://localhost:8000")
    monkeypatch.setenv("METAGIT_STATE_MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("METAGIT_STATE_MONGO_DB", "metagit")

    updated = AppConfig._override_from_environment(AppConfig())

    assert updated.state.org_id == "acme"
    assert updated.state.workspace_id == "platform"
    assert updated.state.dynamodb.table == "state-table"
    assert updated.state.dynamodb.region == "us-east-1"
    assert updated.state.dynamodb.endpoint_url == "http://localhost:8000"
    assert updated.state.mongodb.uri == "mongodb://localhost:27017"
    assert updated.state.mongodb.database == "metagit"


def test_state_identity_resolution_uses_configured_values(tmp_path) -> None:
    state = StateConfig(org_id="acme", workspace_id="platform")
    assert resolve_org_id(state) == "acme"
    assert resolve_workspace_id(state, str(tmp_path)) == "platform"


def test_state_identity_resolution_derives_defaults(tmp_path) -> None:
    state = StateConfig()
    resolved_root = str(Path(tmp_path).resolve())
    expected_workspace_id = hashlib.sha256(resolved_root.encode("utf-8")).hexdigest()[:16]
    assert resolve_org_id(state) == "_"
    assert resolve_workspace_id(state, str(tmp_path)) == expected_workspace_id


def test_preview_redacts_mongo_uri() -> None:
    config = AppConfig(state=StateConfig(mongodb=StateMongoConfig(uri="mongodb://user:pass@host/db")))
    redacted = redact_secrets(config.model_dump(mode="json"))
    assert "pass" not in redacted["state"]["mongodb"]["uri"]


def test_describe_state_backend_defaults_local() -> None:
    from metagit.core.state.resolver import describe_state_backend

    info = describe_state_backend("/tmp/ws")
    assert info["backend"] == "local"
    assert info["url"] == ""
    assert info["token_configured"] is False


def test_describe_state_backend_reports_remote_env(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_URL", "http://127.0.0.1:8787")
    monkeypatch.setenv("METAGIT_STATE_TOKEN", "secret")
    info = describe_state_backend("/tmp/ws")
    assert info["backend"] == "http"
    assert info["url"] == "http://127.0.0.1:8787"
    assert info["env_overrides"]["METAGIT_STATE_URL"] is True
    assert info["token_configured"] is True


def test_describe_state_backend_sanitizes_remote_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "METAGIT_STATE_URL",
        "https://user:password@example.test/state?token=secret&key=value",
    )

    info = describe_state_backend("/tmp/ws")

    assert info["url"] == "https://example.test/state?token=***&key=***"
    assert "user" not in info["url"]
    assert "password" not in info["url"]
    assert "secret" not in info["url"]


@pytest.mark.parametrize(
    "statement",
    [
        "from metagit.core.state import resolve_backend",
        "from metagit.core.state.resolver import resolve_backend",
    ],
)
def test_resolver_is_cold_importable_in_subprocess(statement: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", statement],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_resolve_memory_backend(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_BACKEND", "memory")
    bundle = resolve_backend("/tmp/ws")
    token = bundle.objectives().save([], expected=None)
    rows, loaded_token = bundle.objectives().load()
    assert rows == []
    assert loaded_token == token


def test_resolve_memory_backend_reuses_store(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_BACKEND", "memory")
    first = resolve_backend("/tmp/shared-memory-ws")
    now = utc_now_iso()
    objective = Objective(
        id="shared",
        title="Shared objective",
        created_at=now,
        updated_at=now,
    )
    first.objectives().save([objective], expected=None)

    second = resolve_backend("/tmp/shared-memory-ws")
    rows, _ = second.objectives().load()

    assert [row.id for row in rows] == ["shared"]


def test_resolve_document_store_for_supported_backends(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("METAGIT_STATE_BACKEND", "local")
    assert isinstance(resolve_document_store(str(tmp_path)), LocalDocumentStore)

    monkeypatch.setenv("METAGIT_STATE_BACKEND", "memory")
    assert isinstance(resolve_document_store(str(tmp_path)), InMemoryDocumentStore)

    monkeypatch.setenv("METAGIT_STATE_BACKEND", "http")
    monkeypatch.setenv("METAGIT_STATE_URL", "http://example.test")
    assert isinstance(resolve_document_store(str(tmp_path)), HttpDocumentStore)


def test_mongodb_backend_requires_uri_and_database(monkeypatch, tmp_path) -> None:
    # CI runners often have no ~/.config/metagit/config.yml; isolate Path.home
    # so AppConfig.load() cannot mask missing env via a developer config file.
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: empty_home)
    monkeypatch.setenv("METAGIT_STATE_BACKEND", "mongodb")
    monkeypatch.delenv("METAGIT_STATE_MONGO_URI", raising=False)
    monkeypatch.delenv("METAGIT_STATE_MONGO_DB", raising=False)
    with pytest.raises(ValueError, match="requires uri"):
        resolve_document_store(str(tmp_path))
    with pytest.raises(ValueError, match="requires uri"):
        resolve_backend(str(tmp_path))

    monkeypatch.setenv("METAGIT_STATE_MONGO_URI", "mongodb://localhost:27017")
    with pytest.raises(ValueError, match="requires database"):
        resolve_document_store(str(tmp_path))
    with pytest.raises(ValueError, match="requires database"):
        resolve_backend(str(tmp_path))


def test_appconfig_load_applies_state_env_without_config_file(monkeypatch, tmp_path) -> None:
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: empty_home)
    monkeypatch.setenv("METAGIT_STATE_BACKEND", "mongodb")
    monkeypatch.setenv("METAGIT_STATE_MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("METAGIT_STATE_MONGO_DB", "metagit")

    loaded = AppConfig.load()
    assert not isinstance(loaded, Exception)
    assert loaded.state.backend == "mongodb"
    assert loaded.state.mongodb.uri == "mongodb://localhost:27017"
    assert loaded.state.mongodb.database == "metagit"


def test_dynamodb_backend_requires_table(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("METAGIT_STATE_BACKEND", "dynamodb")
    monkeypatch.delenv("METAGIT_STATE_DDB_TABLE", raising=False)
    with pytest.raises(ValueError, match="requires table"):
        resolve_document_store(str(tmp_path))
    with pytest.raises(ValueError, match="requires table"):
        resolve_backend(str(tmp_path))


def test_resolve_dynamodb_document_store(monkeypatch, tmp_path) -> None:
    pytest.importorskip("boto3")
    from metagit.core.state.dynamodb import DynamoDocumentStore

    monkeypatch.setenv("METAGIT_STATE_BACKEND", "dynamodb")
    monkeypatch.setenv("METAGIT_STATE_DDB_TABLE", "metagit-state")
    monkeypatch.setenv("METAGIT_STATE_DDB_REGION", "us-east-1")
    store = resolve_document_store(str(tmp_path))
    assert isinstance(store, DynamoDocumentStore)
    assert store.describe()["table"] == "metagit-state"
    assert "secret" not in store.describe()


def test_resolve_mongodb_document_store(monkeypatch, tmp_path) -> None:
    pytest.importorskip("pymongo")
    from metagit.core.state.mongodb import MongoDocumentStore

    monkeypatch.setenv("METAGIT_STATE_BACKEND", "mongodb")
    monkeypatch.setenv("METAGIT_STATE_MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("METAGIT_STATE_MONGO_DB", "metagit")
    store = resolve_document_store(str(tmp_path))
    assert isinstance(store, MongoDocumentStore)
    info = store.describe()
    assert info["database"] == "metagit"
    assert info["collection"] == "metagit_state"
    assert "uri" not in info
    assert "secret" not in info


def test_describe_includes_org_workspace_and_extras(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_ORG_ID", "acme")
    monkeypatch.setenv("METAGIT_STATE_WORKSPACE_ID", "ws1")
    info = describe_state_backend("/tmp/ws")
    assert info["org_id"] == "acme"
    assert info["workspace_id"] == "ws1"
    assert isinstance(info["extras"]["dynamodb"], bool)
    assert isinstance(info["extras"]["mongodb"], bool)
