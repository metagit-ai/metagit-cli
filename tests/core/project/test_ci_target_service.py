#!/usr/bin/env python
"""Tests for CiTargetService show/detect/set persistence."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.project.ci_models import CiProvider, CiTargetStatus
from metagit.core.project.ci_target_service import CiTargetService
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _write_manifest(tmp_path: Path) -> tuple[Path, MetagitConfig]:
    config = MetagitConfig(
        name="demo",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="umbrella",
                    repos=[
                        ProjectPath(
                            name="payments-api",
                            url="https://dev.azure.com/contoso/PaySystem/_git/payments-api",
                        )
                    ],
                )
            ]
        ),
    )
    path = tmp_path / ".metagit.yml"
    path.write_text(
        "name: demo\n"
        "workspace:\n"
        "  projects:\n"
        "    - name: umbrella\n"
        "      repos:\n"
        "        - name: payments-api\n"
        "          url: https://dev.azure.com/contoso/PaySystem/_git/payments-api\n",
        encoding="utf-8",
    )
    return path, config


def test_ci_target_service_detect_and_apply(tmp_path: Path) -> None:
    path, config = _write_manifest(tmp_path)
    service = CiTargetService()
    detected = service.detect(
        config=config,
        project_name="umbrella",
        repo_name="payments-api",
        config_path=str(path),
        apply=True,
        force=True,
    )
    assert detected["ok"] is True
    assert detected["applied"] is True
    assert detected["ci"]["provider"] == "azure_devops"
    assert detected["ci"]["organization"] == "contoso"

    shown = service.show(
        config=config,
        project_name="umbrella",
        repo_name="payments-api",
        config_path=str(path),
    )
    assert shown["ok"] is True
    assert shown["ci"]["project"] == "PaySystem"


def test_ci_target_service_set_declared(tmp_path: Path) -> None:
    path, config = _write_manifest(tmp_path)
    result = CiTargetService().set_target(
        config=config,
        project_name="umbrella",
        repo_name="payments-api",
        config_path=str(path),
        provider=CiProvider.AZURE_DEVOPS.value,
        organization="contoso",
        project="OtherProject",
        repository="payments-api",
        definition_ids=["42"],
        status=CiTargetStatus.OVERRIDDEN.value,
    )
    assert result["ok"] is True
    assert result["ci"]["project"] == "OtherProject"
    assert result["ci"]["definition_ids"] == ["42"]
    assert result["ci"]["status"] == "overridden"
