#!/usr/bin/env python
"""Tests for install method detection."""

from __future__ import annotations

from unittest.mock import patch

from metagit.core.release.install_detect import (
    build_upgrade_command,
    detect_install_method,
)


@patch("metagit.core.release.install_detect._is_editable_install", return_value=False)
@patch("metagit.core.release.install_detect._is_uv_tool_install", return_value=True)
def test_detect_install_method_prefers_uv_tool(
    _mock_uv: object,
    _mock_editable: object,
) -> None:
    assert detect_install_method() == "uv_tool"
    assert build_upgrade_command("uv_tool") == "uv tool upgrade metagit-cli"


@patch("metagit.core.release.install_detect._is_editable_install", return_value=True)
def test_detect_install_method_reports_editable(_mock_editable: object) -> None:
    assert detect_install_method() == "editable"


@patch("metagit.core.release.install_detect._is_editable_install", return_value=False)
@patch("metagit.core.release.install_detect._is_uv_tool_install", return_value=False)
@patch("metagit.core.release.install_detect._package_is_installed", return_value=True)
@patch("metagit.core.release.install_detect.sys.executable", "/usr/bin/python3")
def test_detect_install_method_falls_back_to_pip(
    _mock_pkg: object,
    _mock_uv: object,
    _mock_editable: object,
) -> None:
    assert detect_install_method() == "pip"
    assert (
        build_upgrade_command("pip") == "/usr/bin/python3 -m pip install -U metagit-cli"
    )
