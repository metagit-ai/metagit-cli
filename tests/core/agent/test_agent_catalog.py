#!/usr/bin/env python
"""Tests for agent catalog service."""

from pathlib import Path

from metagit.core.agent.catalog import AgentCatalogService
from metagit.core.agent.models import AgentTemplateManifest
from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.agent.schema_generator import agent_template_json_schema


def test_all_bundled_templates_validate() -> None:
    registry = AgentTemplateRegistry()
    issues = AgentCatalogService(registry=registry).validate_all_templates()
    assert issues == []
    assert len(registry.list_template_ids()) == 10


def test_catalog_envelope_sorted_and_delegation_index() -> None:
    service = AgentCatalogService()
    envelope = service.list_catalog()
    assert envelope.schema_version == "1.0"
    assert len(envelope.templates) == 10
    ids = [entry.id for entry in envelope.templates]
    assert ids.index("orchestration-overseer") < ids.index("repo-implementer")
    implementer = next(item for item in envelope.templates if item.id == "repo-implementer")
    assert "orchestration-overseer" in implementer.delegated_by
    assert "agent-access-optimizer" in implementer.delegates_to


def test_minimal_manifest_rejects_unknown_extra() -> None:
    try:
        AgentTemplateManifest.model_validate(
            {
                "id": "demo",
                "label": "Demo",
                "description": "demo",
                "unexpected": True,
            }
        )
    except Exception:
        return
    raise AssertionError("expected validation error for unknown field")


def test_schema_contains_catalog_fields() -> None:
    schema = agent_template_json_schema()
    properties = schema.get("properties", {})
    assert "schema_version" in properties
    assert "ui" in properties
    assert "delegates_to" in properties


def test_overlay_merge(tmp_path: Path) -> None:
    overlay_root = tmp_path / ".metagit-agents" / "repo-implementer"
    overlay_root.mkdir(parents=True)
    (overlay_root / "template.yaml").write_text(
        "schema_version: '1.0'\n"
        "id: repo-implementer\n"
        "label: Overlay implementer\n"
        "description: overlay\n"
        "version: 9.9.9\n",
        encoding="utf-8",
    )
    registry = AgentTemplateRegistry(manifest_root=tmp_path)
    manifest = registry.load_manifest("repo-implementer")
    assert manifest is not None
    assert manifest.label == "Overlay implementer"
    assert manifest.version == "9.9.9"
    assert registry.resolve_source("repo-implementer").value == "merged"
