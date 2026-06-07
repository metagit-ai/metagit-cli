#!/usr/bin/env python
"""Tests for VersionUpgradeService."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from metagit.core.release.models import LatestReleaseInfo, VersionCheckResult
from metagit.core.release.upgrade_service import VersionUpgradeService


def _check_result(*, update_available: bool = True) -> VersionCheckResult:
    latest = LatestReleaseInfo(
        version="2.0.0",
        tag_name="v2.0.0",
        published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        html_url="https://github.com/metagit-ai/metagit-cli/releases/tag/v2.0.0",
        source="github",
    )
    return VersionCheckResult(
        installed_version="1.0.0",
        latest_release=latest,
        pypi_version="2.0.0",
        update_available=update_available,
        is_latest=not update_available,
        install_command="uv tool upgrade metagit-cli",
    )


def test_upgrade_dry_run_when_update_available() -> None:
    check_service = MagicMock()
    check_service.check.return_value = _check_result(update_available=True)
    service = VersionUpgradeService(check_service=check_service)

    with patch(
        "metagit.core.release.upgrade_service.detect_install_method",
        return_value="uv_tool",
    ):
        result = service.upgrade(apply=False)

    assert result.ok is True
    assert result.dry_run is True
    assert result.applied is False
    assert result.command == "uv tool upgrade metagit-cli"
    assert "Update available" in (result.message or "")


def test_upgrade_skips_when_already_latest() -> None:
    check_service = MagicMock()
    check_service.check.return_value = _check_result(update_available=False)
    service = VersionUpgradeService(check_service=check_service)

    with patch(
        "metagit.core.release.upgrade_service.detect_install_method",
        return_value="uv_tool",
    ):
        result = service.upgrade(apply=True)

    assert result.ok is True
    assert result.skipped is True
    assert result.applied is False


def test_upgrade_refuses_editable_install() -> None:
    check_service = MagicMock()
    check_service.check.return_value = _check_result(update_available=True)
    service = VersionUpgradeService(check_service=check_service)

    with patch(
        "metagit.core.release.upgrade_service.detect_install_method",
        return_value="editable",
    ):
        result = service.upgrade(apply=True)

    assert result.ok is False
    assert result.error == "editable_install"


def test_upgrade_applies_command() -> None:
    check_service = MagicMock()
    check_service.check.return_value = _check_result(update_available=True)

    def _runner(
        command: list[str], *, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["uv", "tool", "upgrade", "metagit-cli"]
        return subprocess.CompletedProcess(command, 0, "upgraded", "")

    service = VersionUpgradeService(check_service=check_service, runner=_runner)

    with patch(
        "metagit.core.release.upgrade_service.detect_install_method",
        return_value="uv_tool",
    ):
        result = service.upgrade(apply=True)

    assert result.ok is True
    assert result.applied is True
    assert result.dry_run is False
    assert result.exit_code == 0
    assert result.stdout == "upgraded"
