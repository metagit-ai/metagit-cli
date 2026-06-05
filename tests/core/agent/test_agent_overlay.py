#!/usr/bin/env python
"""Tests for workspace agent template overlay scaffolding."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.agent.models import AgentOverlayInitMode, AgentOverlayScope
from metagit.core.agent.overlay import (
    init_overlay_from_bundled,
    overlay_has_files,
    overlay_path_for_template,
)
from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.agent.service import AgentService


def _write_manifest_root(path: Path) -> None:
    (path / ".metagit.yml").write_text(
        "name: test-workspace\nworkspace:\n  path: .\n",
        encoding="utf-8",
    )


def test_init_overlay_committed_default_path(tmp_path: Path) -> None:
    _write_manifest_root(tmp_path)
    registry = AgentTemplateRegistry()
    bundled_dir = registry.template_dir("repo-implementer")
    result = init_overlay_from_bundled(
        template_id="repo-implementer",
        manifest_root=tmp_path,
        bundled_dir=bundled_dir,
        scope=AgentOverlayScope.COMMITTED,
    )
    overlay_dir = overlay_path_for_template(
        tmp_path,
        "repo-implementer",
        scope=AgentOverlayScope.COMMITTED,
    )
    assert overlay_dir.is_dir()
    assert ".metagit-agents" in str(overlay_dir)
    assert (overlay_dir / "template.yaml").is_file()
    assert result.scope == AgentOverlayScope.COMMITTED


def test_init_overlay_local_path(tmp_path: Path) -> None:
    _write_manifest_root(tmp_path)
    registry = AgentTemplateRegistry()
    result = init_overlay_from_bundled(
        template_id="repo-implementer",
        manifest_root=tmp_path,
        bundled_dir=registry.template_dir("repo-implementer"),
        scope=AgentOverlayScope.LOCAL,
        mode=AgentOverlayInitMode.MINIMAL,
    )
    overlay_dir = overlay_path_for_template(
        tmp_path,
        "repo-implementer",
        scope=AgentOverlayScope.LOCAL,
    )
    assert ".metagit/.agent-templates" in str(overlay_dir)
    assert result.scope == AgentOverlayScope.LOCAL


def test_local_overlay_overrides_committed_manifest(tmp_path: Path) -> None:
    _write_manifest_root(tmp_path)
    registry = AgentTemplateRegistry()
    bundled_dir = registry.template_dir("repo-implementer")
    init_overlay_from_bundled(
        template_id="repo-implementer",
        manifest_root=tmp_path,
        bundled_dir=bundled_dir,
        scope=AgentOverlayScope.COMMITTED,
        mode=AgentOverlayInitMode.MINIMAL,
    )
    committed_manifest = overlay_path_for_template(
        tmp_path,
        "repo-implementer",
        scope=AgentOverlayScope.COMMITTED,
    ) / "template.yaml"
    committed_manifest.write_text(
        committed_manifest.read_text(encoding="utf-8").replace(
            "# label: Custom label",
            "label: Committed label",
        ),
        encoding="utf-8",
    )
    local_dir = overlay_path_for_template(
        tmp_path,
        "repo-implementer",
        scope=AgentOverlayScope.LOCAL,
    )
    local_dir.mkdir(parents=True)
    (local_dir / "template.yaml").write_text(
        "schema_version: '1.0'\nid: repo-implementer\nlabel: Local label\n",
        encoding="utf-8",
    )
    merged_registry = AgentTemplateRegistry(manifest_root=tmp_path)
    manifest = merged_registry.load_manifest("repo-implementer")
    assert manifest is not None
    assert manifest.label == "Local label"


def test_init_overlay_refuses_without_force(tmp_path: Path) -> None:
    _write_manifest_root(tmp_path)
    registry = AgentTemplateRegistry()
    bundled_dir = registry.template_dir("repo-implementer")
    init_overlay_from_bundled(
        template_id="repo-implementer",
        manifest_root=tmp_path,
        bundled_dir=bundled_dir,
    )
    with pytest.raises(FileExistsError):
        init_overlay_from_bundled(
            template_id="repo-implementer",
            manifest_root=tmp_path,
            bundled_dir=bundled_dir,
        )


def test_cli_overlay_init_committed(tmp_path: Path) -> None:
    _write_manifest_root(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "agent",
            "overlay",
            "init",
            "repo-implementer",
            "--root",
            str(tmp_path),
            "--mode",
            "minimal",
        ],
    )
    assert result.exit_code == 0, result.output
    assert ".metagit-agents/repo-implementer" in result.output


def test_service_init_overlay_merged_source(tmp_path: Path) -> None:
    _write_manifest_root(tmp_path)
    service = AgentService(manifest_root=tmp_path)
    service.init_overlay("repo-implementer", mode=AgentOverlayInitMode.MINIMAL)
    registry = AgentTemplateRegistry(manifest_root=tmp_path)
    assert registry.resolve_source("repo-implementer").value == "merged"
    assert overlay_has_files(
        tmp_path,
        "repo-implementer",
        scope=AgentOverlayScope.COMMITTED,
    )
