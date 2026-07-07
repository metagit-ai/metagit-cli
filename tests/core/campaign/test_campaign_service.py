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


def test_campaign_create_with_explicit_repos_freezes_selection(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(config=config, definition_root=tmp_path)
    campaign = service.create(
        slug="frozen",
        title="Frozen set",
        repos=["demo/alpha", "demo/beta", "demo/alpha"],  # dupe ignored
        goal="Ship the thing",
        reference_impl="demo/alpha",
    )
    # Explicit set is frozen verbatim (no query drift), deduped, order preserved.
    assert [f"{r.project}/{r.repo}" for r in campaign.repos] == ["demo/alpha", "demo/beta"]
    assert campaign.selection.query is None
    assert campaign.selection.resolved_at is not None
    assert campaign.goal == "Ship the thing"
    assert campaign.reference_impl == "demo/alpha"
    assert campaign.created is not None and campaign.updated is not None


def test_campaign_create_requires_query_or_repos(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(config=config, definition_root=tmp_path)
    try:
        service.create(slug="empty", title="Empty")
    except ValueError as exc:
        assert "--query or at least one --repo" in str(exc)
    else:  # pragma: no cover - guard must raise
        raise AssertionError("expected ValueError when no selection provided")


def test_campaign_explicit_repo_bad_selector(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(config=config, definition_root=tmp_path)
    try:
        service.create(slug="bad", title="Bad", repos=["no-slash"])
    except ValueError as exc:
        assert "project/repo" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for malformed --repo selector")


def test_campaign_set_repo_status_stamps_updated(tmp_path: Path) -> None:
    config = _sample_config()
    service = CampaignService(config=config, definition_root=tmp_path)
    created = service.create(slug="stamp", title="Stamp", repos=["demo/alpha"])
    original_updated = created.updated
    assert original_updated is not None
    changed = service.set_repo_status(slug="stamp", project="demo", repo="alpha", status="mr-open")
    assert changed.updated is not None
    assert changed.updated >= original_updated


def test_campaign_loads_legacy_document(tmp_path: Path) -> None:
    """A pre-native overlay (int schema_version, `complete` status, list tags)
    loads without a rewrite via the compatibility normalizers."""
    config = _sample_config()
    service = CampaignService(
        config=config,
        definition_root=tmp_path,
        campaigns_path="knowledge/campaigns",
    )
    service.campaigns_dir().mkdir(parents=True, exist_ok=True)
    legacy = (
        "schema_version: 1\n"
        "slug: legacy\n"
        "title: Legacy overlay\n"
        "status: complete\n"
        "goal: pre-existing goal\n"
        "reference_impl: demo/alpha\n"
        "selection:\n"
        "  query:\n"
        "  tags: []\n"
        "repos:\n"
        "  - project: demo\n"
        "    repo: alpha\n"
        "    role: app\n"
        "    status: merged\n"
        "lessons: []\n"
    )
    (service.campaigns_dir() / "legacy.yml").write_text(legacy, encoding="utf-8")

    loaded = service.load("legacy")
    assert loaded is not None
    assert loaded.schema_version == "1"  # coerced int -> str
    assert loaded.status == "completed"  # complete -> completed
    assert loaded.selection.tags == {}  # [] -> {}
    assert loaded.goal == "pre-existing goal"
    assert loaded.reference_impl == "demo/alpha"
    assert loaded.repos[0].role == "app"

    # And it participates in list/status rollups cleanly.
    summary = service.list_campaigns()
    assert any(item.slug == "legacy" and item.status == "completed" for item in summary.campaigns)
