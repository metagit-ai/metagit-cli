#!/usr/bin/env python
"""Unit tests for CI target models and remote locator parsing."""

from __future__ import annotations

from pathlib import Path

from metagit.core.project.ci_models import CiProvider, CiTargetStatus, RepoCiTarget
from metagit.core.project.ci_target_resolver import (
    CiTargetResolver,
    parse_remote_locator,
    scan_ci_config_paths,
)


def test_parse_ado_https_remote() -> None:
    locator = parse_remote_locator("https://dev.azure.com/contoso/PaySystem/_git/payments-api")
    assert locator["provider"] == CiProvider.AZURE_DEVOPS
    assert locator["organization"] == "contoso"
    assert locator["project"] == "PaySystem"
    assert locator["repository"] == "payments-api"
    assert locator["host"] == "dev.azure.com"


def test_parse_ado_ssh_v3_remote() -> None:
    locator = parse_remote_locator("git@ssh.dev.azure.com:v3/contoso/PaySystem/payments-api")
    assert locator["provider"] == CiProvider.AZURE_DEVOPS
    assert locator["organization"] == "contoso"
    assert locator["project"] == "PaySystem"
    assert locator["repository"] == "payments-api"


def test_parse_github_remote() -> None:
    locator = parse_remote_locator("git@github.com:acme/widget.git")
    assert locator["provider"] == CiProvider.GITHUB
    assert locator["owner"] == "acme"
    assert locator["name"] == "widget"


def test_scan_azure_pipelines_file(tmp_path: Path) -> None:
    (tmp_path / "azure-pipelines.yml").write_text("trigger: none\n", encoding="utf-8")
    paths, provider = scan_ci_config_paths(
        str(tmp_path),
        ci_file_map={"azure-pipelines.yml": "Azure DevOps"},
    )
    assert paths == ["azure-pipelines.yml"]
    assert provider == CiProvider.AZURE_DEVOPS


def test_resolver_preserves_declared(tmp_path: Path) -> None:
    existing = RepoCiTarget(
        provider=CiProvider.AZURE_DEVOPS,
        organization="other-org",
        project="other-project",
        repository="payments-api",
        status=CiTargetStatus.DECLARED,
    )
    resolved = CiTargetResolver().resolve(
        repo_path=str(tmp_path),
        url="https://dev.azure.com/contoso/PaySystem/_git/payments-api",
        existing_ci=existing,
        force=False,
    )
    assert resolved is not None
    assert resolved.organization == "other-org"
    assert resolved.status == CiTargetStatus.DECLARED.value or resolved.status == CiTargetStatus.DECLARED


def test_resolver_force_redetect(tmp_path: Path) -> None:
    (tmp_path / "azure-pipelines.yml").write_text("trigger: none\n", encoding="utf-8")
    existing = RepoCiTarget(
        provider=CiProvider.AZURE_DEVOPS,
        organization="other-org",
        project="other-project",
        repository="payments-api",
        status=CiTargetStatus.DECLARED,
    )
    resolved = CiTargetResolver(
        ci_file_map={"azure-pipelines.yml": "Azure DevOps"},
    ).resolve(
        repo_path=str(tmp_path),
        url="https://dev.azure.com/contoso/PaySystem/_git/payments-api",
        existing_ci=existing,
        force=True,
    )
    assert resolved is not None
    assert resolved.organization == "contoso"
    assert resolved.project == "PaySystem"
    assert "azure-pipelines.yml" in resolved.config_paths
    assert resolved.status == CiTargetStatus.DETECTED.value or resolved.status == CiTargetStatus.DETECTED


def test_detect_for_url_only() -> None:
    target = CiTargetResolver().detect_for_url(
        "https://dev.azure.com/contoso/PaySystem/_git/payments-api"
    )
    assert target is not None
    assert target.provider in {CiProvider.AZURE_DEVOPS, CiProvider.AZURE_DEVOPS.value}
    assert target.organization == "contoso"
