#!/usr/bin/env python
"""
Tests for declarative workspace project sources.
"""

import pytest
from pydantic import ValidationError

from metagit.core.config.models import MetagitConfig, Workspace
from metagit.core.project.source_models import (
    ProjectSource,
    SourceProvider,
    SourceSyncMode,
)
from metagit.core.workspace.models import WorkspaceProject


def test_project_source_to_source_spec() -> None:
    source = ProjectSource(
        id="acme-github",
        provider=SourceProvider.GITHUB,
        org="acme",
        mode=SourceSyncMode.ADDITIVE,
        ignore_patterns=["**/deprecated/**"],
    )
    spec = source.to_source_spec()
    assert spec.source_id == "acme-github"
    assert spec.org == "acme"
    assert spec.ignore_patterns == ["**/deprecated/**"]


def test_project_source_rejects_discover_mode() -> None:
    with pytest.raises(ValidationError):
        ProjectSource(
            id="bad",
            provider=SourceProvider.GITHUB,
            org="acme",
            mode=SourceSyncMode.DISCOVER,
        )


def test_workspace_project_rejects_duplicate_source_ids() -> None:
    with pytest.raises(ValidationError):
        WorkspaceProject(
            name="platform",
            sources=[
                ProjectSource(
                    id="dup",
                    provider=SourceProvider.GITHUB,
                    org="acme",
                ),
                ProjectSource(
                    id="dup",
                    provider=SourceProvider.GITLAB,
                    group="acme",
                ),
            ],
            repos=[],
        )


def test_yaml_ignore_alias_maps_to_ignore_patterns() -> None:
    config = MetagitConfig.model_validate(
        {
            "name": "demo",
            "workspace": {
                "projects": [
                    {
                        "name": "platform",
                        "sources": [
                            {
                                "id": "acme-github",
                                "provider": "github",
                                "org": "acme",
                                "ignore": ["**/deprecated/**"],
                            }
                        ],
                        "repos": [],
                    }
                ]
            },
        }
    )
    assert config.workspace is not None
    source = config.workspace.projects[0].sources[0]
    assert source.ignore_patterns == ["**/deprecated/**"]
