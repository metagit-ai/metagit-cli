#!/usr/bin/env python
"""Tests for ReleaseCheckService."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import requests

from metagit.core.release.release_check_service import ReleaseCheckService


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


def _github_payload() -> dict[str, Any]:
    return {
        "tag_name": "v9.8.7",
        "name": "Metagit 9.8.7",
        "published_at": "2026-05-01T12:00:00Z",
        "html_url": "https://github.com/metagit-ai/metagit-cli/releases/tag/v9.8.7",
        "body": "## Highlights\n- New feature",
    }


def _pypi_payload(version: str = "9.8.7") -> dict[str, Any]:
    return {"info": {"version": version}}


def test_check_reports_update_available() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _FakeResponse(payload=_github_payload()),
        _FakeResponse(payload=_pypi_payload()),
    ]
    service = ReleaseCheckService(session=session)
    result = service.check(installed_version="1.0.0")

    assert result.update_available is True
    assert result.is_latest is False
    assert result.latest_release is not None
    assert result.latest_release.version == "9.8.7"
    assert result.latest_release.body == "## Highlights\n- New feature"
    assert result.pypi_version == "9.8.7"
    assert not result.fetch_errors


def test_check_marks_installed_as_latest() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _FakeResponse(payload=_github_payload()),
        _FakeResponse(payload=_pypi_payload()),
    ]
    service = ReleaseCheckService(session=session)
    result = service.check(installed_version="9.8.7")

    assert result.update_available is False
    assert result.is_latest is True


def test_check_omits_notes_when_requested() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _FakeResponse(payload=_github_payload()),
        _FakeResponse(payload=_pypi_payload()),
    ]
    service = ReleaseCheckService(session=session)
    result = service.check(installed_version="1.0.0", include_notes=False)

    assert result.latest_release is not None
    assert result.latest_release.body is None


def test_check_falls_back_to_pypi_when_github_missing() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _FakeResponse(status_code=404),
        _FakeResponse(payload=_pypi_payload("3.2.1")),
    ]
    service = ReleaseCheckService(session=session)
    result = service.check(installed_version="3.0.0")

    assert result.latest_release is not None
    assert result.latest_release.version == "3.2.1"
    assert result.latest_release.source == "pypi"
    assert result.update_available is True
    assert any("GitHub" in error for error in result.fetch_errors)


def test_check_records_network_errors() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("offline")
    service = ReleaseCheckService(session=session)
    result = service.check(installed_version="1.0.0")

    assert result.latest_release is None
    assert result.pypi_version is None
    assert result.is_latest is True
    assert len(result.fetch_errors) == 2


def test_check_retries_github_without_token_after_401() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _FakeResponse(status_code=401),
        _FakeResponse(payload=_github_payload()),
        _FakeResponse(payload=_pypi_payload()),
    ]
    service = ReleaseCheckService(session=session, github_token="stale-token")
    result = service.check(installed_version="1.0.0")

    assert result.latest_release is not None
    assert result.latest_release.source == "github"
    assert result.latest_release.version == "9.8.7"
    assert session.get.call_count == 3


def test_github_published_at_parses_utc() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _FakeResponse(payload=_github_payload()),
        _FakeResponse(payload=_pypi_payload()),
    ]
    service = ReleaseCheckService(session=session)
    result = service.check(installed_version="1.0.0")

    assert result.latest_release is not None
    assert result.latest_release.published_at == datetime(
        2026, 5, 1, 12, 0, tzinfo=timezone.utc
    )
