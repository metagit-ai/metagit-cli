#!/usr/bin/env python
"""Tests for paged campaign board sync."""

from __future__ import annotations

from pathlib import Path

from metagit.core.campaign.service import CampaignService
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workitem.board_service import CampaignBoardService
from metagit.core.workitem.models import ExternalWorkRef
from metagit.core.workspace.models import Workspace, WorkspaceProject


class _FakeBoard:
    def __init__(self) -> None:
        self.created: list[str] = []
        self._next = 1

    def create_item(self, *, title: str, description: str, kind: str, parent=None):
        _ = (description, parent)
        identifier = str(self._next)
        self._next += 1
        self.created.append(title)
        return ExternalWorkRef(
            provider="azure_devops",
            id=identifier,
            url=f"https://dev.azure.com/org/proj/_workitems/edit/{identifier}",
            kind=kind,
        )

    def get_item(self, ref: ExternalWorkRef):
        return ref


def _config() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[
                        ProjectPath(name="alpha", path="./a"),
                        ProjectPath(name="beta", path="./b"),
                    ],
                ),
            ],
        ),
    )


def test_board_sync_pages_children(tmp_path: Path) -> None:
    service = CampaignService(config=_config(), definition_root=tmp_path)
    service.create(slug="rollout", title="Rollout", repos=["demo/alpha", "demo/beta"])
    client = _FakeBoard()
    result = CampaignBoardService(campaign_service=service, client=client).sync(
        slug="rollout",
        limit=1,
        offset=0,
    )
    assert result.ok is True
    assert result.truncated is True
    assert result.parent is not None
    assert len(result.created) == 2  # parent + one child
    reloaded = service.load("rollout")
    assert reloaded is not None
    assert reloaded.work_item is not None
    assert reloaded.repos[0].work_item is not None
    assert reloaded.repos[1].work_item is None
