#!/usr/bin/env python
"""Tests for Azure DevOps WIT client."""

from __future__ import annotations

from typing import Any

from metagit.core.workitem.azure_devops import AzureDevOpsBoardClient
from metagit.core.workitem.models import ExternalWorkRef


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []

    def post(self, endpoint: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": "POST", "endpoint": endpoint, **kwargs})
        return _FakeResponse(
            {
                "id": 42,
                "_links": {"html": {"href": "https://dev.azure.com/org/proj/_workitems/edit/42"}},
            }
        )

    def get(self, endpoint: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": "GET", "endpoint": endpoint, **kwargs})
        return _FakeResponse({"id": 42, "fields": {"System.WorkItemType": "Feature"}})


def test_create_item_posts_json_patch() -> None:
    session = _FakeSession()
    client = AzureDevOpsBoardClient(
        api_token="pat",
        organization="org",
        project="proj",
        session=session,  # type: ignore[arg-type]
    )
    result = client.create_item(title="Campaign", description="goal", kind="Feature")
    assert not isinstance(result, Exception)
    assert result.id == "42"
    assert result.kind == "Feature"
    assert session.calls[0]["headers"]["Content-Type"] == "application/json-patch+json"


def test_create_child_adds_parent_relation() -> None:
    session = _FakeSession()
    client = AzureDevOpsBoardClient(
        api_token="pat",
        organization="org",
        project="proj",
        session=session,  # type: ignore[arg-type]
    )
    parent = ExternalWorkRef(provider="azure_devops", id="9", url="https://example/9")
    result = client.create_item(
        title="Child",
        description="repo",
        kind="User Story",
        parent=parent,
    )
    assert not isinstance(result, Exception)
    payload = session.calls[0]["json"]
    assert any(item.get("path") == "/relations/-" for item in payload)
