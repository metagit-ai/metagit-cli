#!/usr/bin/env python
"""Unit tests for capability resolve/compile service."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.routing.capability_service import CapabilityService


def _write_manifest(root: Path) -> None:
    (root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "routing:",
                "  catalog: knowledge/requests/entries",
                "  runs: knowledge/requests/runs",
                "workspace:",
                "  projects:",
                "    - name: infra",
                "      tags:",
                "        project_type: iac",
                "        domain: platform",
                "      repos:",
                "        - name: terraform-vpc",
                "          path: repos/terraform-vpc",
                "          language: hcl",
                "          tags:",
                "            iac: terraform",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    repo = root / "repos" / "terraform-vpc"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "main.tf").write_text("resource \"null_resource\" \"demo\" {}\n", encoding="utf-8")
    entries = root / "knowledge" / "requests" / "entries"
    entries.mkdir(parents=True, exist_ok=True)
    (entries / "REQ-TF.yml").write_text(
        "\n".join(
            [
                "id: REQ-TF",
                "title: Terraform module change",
                "triggers:",
                "  - terraform module change",
                "gates: [fmt, validate]",
                "capability:",
                "  selector:",
                "    project_types: [iac]",
                "    tags: {iac: terraform}",
                "    path_globs: ['**/*.tf']",
                "    languages: [hcl]",
                "  workflow:",
                "    - {name: inspect}",
                "    - {name: fmt, gate: true}",
                "  expected_output: merge_request",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _service(root: Path) -> CapabilityService:
    loaded = MetagitConfigManager(str(root / ".metagit.yml")).load_config()
    assert not isinstance(loaded, Exception)
    return CapabilityService(loaded, workspace_root=str(root))


def test_resolve_returns_capability_matches(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    matches = _service(tmp_path).resolve("terraform module change", project="infra")
    assert len(matches) == 1
    assert matches[0].capability_id == "REQ-TF"
    assert "selector:pass" in matches[0].why


def test_compile_returns_envelope_with_scope_and_workflow(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    envelope = _service(tmp_path).compile("REQ-TF", project="infra", repo="terraform-vpc", with_context=False)
    assert envelope.capability_id == "REQ-TF"
    assert envelope.repository.repo == "terraform-vpc"
    assert envelope.workflow[1].name == "fmt"
    assert "fmt" in envelope.gates

