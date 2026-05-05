#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.gate
"""

from pathlib import Path

from metagit.core.mcp.gate import WorkspaceGate
from metagit.core.mcp.models import McpActivationState


def test_missing_root_is_inactive_missing() -> None:
    gate = WorkspaceGate()

    result = gate.evaluate(root_path=None)

    assert result.state == McpActivationState.INACTIVE_MISSING_CONFIG


def test_missing_config_file_is_inactive_missing(tmp_path: Path) -> None:
    gate = WorkspaceGate()

    result = gate.evaluate(root_path=str(tmp_path))

    assert result.state == McpActivationState.INACTIVE_MISSING_CONFIG


def test_invalid_config_file_is_inactive_invalid(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text("name:\n  - invalid\n", encoding="utf-8")
    gate = WorkspaceGate()

    result = gate.evaluate(root_path=str(tmp_path))

    assert result.state == McpActivationState.INACTIVE_INVALID_CONFIG


def test_valid_config_file_is_active(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(
        "\n".join(
            [
                "name: metagit-test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    gate = WorkspaceGate()

    result = gate.evaluate(root_path=str(tmp_path))

    assert result.state == McpActivationState.ACTIVE
