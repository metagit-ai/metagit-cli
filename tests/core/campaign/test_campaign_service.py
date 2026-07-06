#!/usr/bin/env python
"""Unit tests for native campaign service."""

from __future__ import annotations

from pathlib import Path

from metagit.core.campaign.models import CampaignDocument, CampaignRepoEntry
from metagit.core.campaign.service import CampaignService
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _sample_config() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[
                        ProjectPath(name="alpha", path="./"),
                        ProjectPath(name="beta", path="./examples"),
                    ],
                ),
            ],
        ),
    )


def test_campaign_create_uses_default_campaigns_dir(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(config=config, definition_root=tmp_path)
    service.create(slug="rollout", title="Rollout", query="alpha")
    assert service.campaigns_dir() == (tmp_path / "_campaigns").resolve()


def test_campaign_create_and_status(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(config=config, definition_root=tmp_path)
    campaign = service.create(slug="rollout", title="Rollout", query="alpha")
    assert campaign.slug == "rollout"
    assert len(campaign.repos) == 1
    assert campaign.repos[0].project == "demo"

    status = service.status("rollout")
    assert status is not None
    assert status.pending_count == 1

    updated = service.set_repo_status(
        slug="rollout",
        project="demo",
        repo="alpha",
        status="merged",
        mr="https://example.com/mr/1",
    )
    assert updated.repos[0].status == "merged"
    assert updated.repos[0].mr == "https://example.com/mr/1"


def test_campaign_validate_unknown_repo(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(
        config=config,
        definition_root=tmp_path,
        campaigns_path="_campaigns",
    )
    service.campaigns_dir().mkdir(parents=True, exist_ok=True)
    invalid = CampaignDocument(
        slug="bad",
        title="Bad",
        repos=[CampaignRepoEntry(project="demo", repo="missing")],
    )
    service._save(invalid)
    issues = service.validate_all()
    assert any("unknown repo" in issue.message for issue in issues)


def test_campaign_expand_dry_run(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(config=config, definition_root=tmp_path)
    service.create(slug="expand-me", title="Expand", query="alpha")
    result = service.expand(slug="expand-me", session_root=tmp_path, dry_run=True)
    assert len(result.objective_ids) == 1
    assert result.objective_ids[0].startswith("campaign-expand-me-")
