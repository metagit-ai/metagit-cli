#!/usr/bin/env python
"""Tests for agent template partial rendering."""

from pathlib import Path

import pytest

from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.agent.renderer import AgentTemplateRenderer
from metagit.core.init.models import InitTemplateFileSpec


def test_include_resolves_shared_partial() -> None:
    registry = AgentTemplateRegistry()
    renderer = AgentTemplateRenderer(
        resolve_source=lambda name: registry.resolve_source_file(
            "repo-implementer",
            name,
        ),
    )
    content = renderer.render_file(
        registry.template_dir("repo-implementer"),
        InitTemplateFileSpec(template="repo-implementer.md.tpl", output="out.md"),
        {
            "workspace_name": "demo",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "demo",
            "id": "repo-implementer",
            "label": "Repo implementer",
        },
    )
    assert "Guarded sync" in content
    assert "demo" in content


def test_missing_partial_raises(tmp_path: Path) -> None:
    broken = tmp_path / "broken.md.tpl"
    broken.write_text('{{ include "does-not-exist" }}\n', encoding="utf-8")
    renderer = AgentTemplateRenderer(
        resolve_source=lambda name: tmp_path / f"{name}.md.tpl"
        if (tmp_path / f"{name}.md.tpl").is_file()
        else None,
    )
    with pytest.raises(FileNotFoundError):
        renderer.render_file(
            tmp_path,
            InitTemplateFileSpec(template="broken.md.tpl", output="out.md"),
            {"workspace_name": "demo", "manifest_path": ".metagit.yml"},
        )
