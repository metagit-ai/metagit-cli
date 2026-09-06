#!/usr/bin/env python
"""Tests for ComponentCatalog attachment points."""

from __future__ import annotations

from metagit.core.component.catalog import ComponentCatalog
from metagit.core.component.models import Component
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_native_nested_components() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="core",
                            path="./platform",
                            components=[
                                Component(name="web", path="apps/web"),
                                Component(name="api", path="apps/api"),
                            ],
                        )
                    ],
                )
            ]
        ),
    )
    rows = ComponentCatalog().list(config)
    assert [row.id for row in rows] == ["platform/core/web", "platform/core/api"]
    assert rows[0].source == "native"
    assert rows[0].spec.path == "apps/web"


def test_empty_repo_components_are_omitted() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[ProjectPath(name="core", path="./platform")],
                )
            ]
        ),
    )
    assert ComponentCatalog().list(config) == []


def test_application_paths_adapter_uses_config_name() -> None:
    config = MetagitConfig(
        name="metagit-cli",
        kind="cli",
        paths=[
            ProjectPath(
                name="metagit-cli",
                path="src/metagit",
                language="python",
                tags={"type": "cli"},
            )
        ],
    )
    rows = ComponentCatalog().list(config)
    assert len(rows) == 1
    assert rows[0].id == "metagit-cli/metagit-cli/metagit-cli"
    assert rows[0].source == "path"
    assert rows[0].spec.language == "python"
    assert rows[0].spec.tags == {"type": "cli"}


def test_legacy_ref_only_components_are_skipped() -> None:
    config = MetagitConfig(
        name="app",
        components=[ProjectPath(name="other", ref="other-project")],
        paths=[ProjectPath(name="lib", path="packages/lib")],
    )
    rows = ComponentCatalog().list(config)
    assert [row.id for row in rows] == ["app/app/lib"]
    assert rows[0].source == "path"


def test_legacy_path_bearing_components_are_cataloged() -> None:
    config = MetagitConfig(
        name="app",
        components=[ProjectPath(name="shared", path="packages/shared", language="go")],
    )
    rows = ComponentCatalog().list(config)
    assert len(rows) == 1
    assert rows[0].id == "app/app/shared"
    assert rows[0].source == "legacy_component"
    assert rows[0].spec.language == "go"
