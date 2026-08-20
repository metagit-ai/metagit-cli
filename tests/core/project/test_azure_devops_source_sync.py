#!/usr/bin/env python
"""Unit tests for Azure DevOps source discovery helpers."""

from __future__ import annotations

from typing import Any

import pytest

from metagit.core.appconfig.models import AppConfig, AzureDevOpsProvider, Providers
from metagit.core.project.source_models import SourceProvider, SourceSpec
from metagit.core.project.source_sync import SourceSyncService
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeSession:
    def __init__(self) -> None:
        self.auth: Any = None
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: float = 30) -> _FakeResponse:
        self.calls.append((url, dict(params or {})))
        if url.endswith("/_apis/projects"):
            return _FakeResponse({"value": [{"name": "PaySystem"}, {"name": "Shared"}]})
        if "/_apis/git/repositories" in url:
            project = "PaySystem" if "PaySystem" in url else "Shared"
            return _FakeResponse(
                {
                    "value": [
                        {
                            "id": f"{project}-1",
                            "name": f"{project.lower()}-api",
                            "remoteUrl": f"https://dev.azure.com/contoso/{project}/_git/{project.lower()}-api",
                            "defaultBranch": "refs/heads/main",
                            "isDisabled": False,
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected url {url}")


def test_source_spec_azure_requires_organization() -> None:
    with pytest.raises(ValueError, match="organization"):
        SourceSpec(provider=SourceProvider.AZURE_DEVOPS)


def test_discover_azure_devops_across_projects(monkeypatch: pytest.MonkeyPatch) -> None:
    app_config = AppConfig(
        providers=Providers(
            azure_devops=AzureDevOpsProvider(
                enabled=True,
                api_token="pat",
                base_url="https://dev.azure.com",
            )
        )
    )
    logger = UnifiedLogger(LoggerConfig(log_level="ERROR", minimal_console=True))
    service = SourceSyncService(app_config, logger)
    fake = _FakeSession()

    monkeypatch.setattr("metagit.core.project.source_sync.requests.Session", lambda: fake)

    spec = SourceSpec(
        provider=SourceProvider.AZURE_DEVOPS,
        organization="contoso",
        recursive=True,
    )
    result = service._discover_azure_devops(spec)
    assert not isinstance(result, Exception)
    assert len(result) == 2
    assert result[0].provider == SourceProvider.AZURE_DEVOPS
    assert result[0].namespace.startswith("contoso/")
    assert any(item.full_name.endswith("paysystem-api") for item in result)
