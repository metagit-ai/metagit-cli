#!/usr/bin/env python
"""Tests for ComponentResolver list/get/resolve."""

from __future__ import annotations

from pathlib import Path

from metagit.core.component.models import Component
from metagit.core.component.resolve import ComponentResolver, resolved_component_payload
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _native() -> MetagitConfig:
    return MetagitConfig(
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
                                Component(name="web", path="apps/web", kind="application"),
                                Component(name="api", path="apps/api", kind="service"),
                                Component(name="auth", path="apps/web/packages/auth"),
                            ],
                        )
                    ],
                )
            ]
        ),
    )


def test_direct_path_match() -> None:
    row = ComponentResolver().resolve(_native(), "apps/web", project="platform", repo="core")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "web"


def test_nested_file_match() -> None:
    row = ComponentResolver().resolve(
        _native(), "apps/web/src/login.tsx", project="platform", repo="core"
    )
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "web"


def test_overlapping_paths_select_longest() -> None:
    row = ComponentResolver().resolve(
        _native(),
        "apps/web/packages/auth/src/index.ts",
        project="platform",
        repo="core",
    )
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "auth"


def test_unmatched_path_returns_none() -> None:
    row = ComponentResolver().resolve(
        _native(), "docs/readme.md", project="platform", repo="core"
    )
    assert row is None


def test_repo_without_components_returns_none() -> None:
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
    assert ComponentResolver().resolve(config, "apps/web", project="platform", repo="core") is None
    assert ComponentResolver().list(config) == []


def test_invalid_path_returns_value_error() -> None:
    result = ComponentResolver().resolve(_native(), "../escape", project="platform", repo="core")
    assert isinstance(result, ValueError)


def test_get_by_full_id() -> None:
    row = ComponentResolver().get(_native(), "platform/core/web")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.id == "platform/core/web"


def test_get_unique_bare_name() -> None:
    row = ComponentResolver().get(_native(), "api")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "api"


def test_get_ambiguous_bare_name() -> None:
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
                            path="./a",
                            components=[Component(name="web", path="apps/web")],
                        ),
                        ProjectPath(
                            name="edge",
                            path="./b",
                            components=[Component(name="web", path="web")],
                        ),
                    ],
                )
            ]
        ),
    )
    result = ComponentResolver().get(config, "web")
    assert isinstance(result, ValueError)
    assert "ambiguous" in str(result).lower()


def test_unscoped_relative_path_two_repos_is_ambiguous() -> None:
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
                            path="./a",
                            components=[Component(name="web", path="apps/web")],
                        ),
                        ProjectPath(
                            name="edge",
                            path="./b",
                            components=[Component(name="site", path="apps/web")],
                        ),
                    ],
                )
            ]
        ),
    )
    result = ComponentResolver().resolve(config, "apps/web/src/x.ts")
    assert isinstance(result, ValueError)


def test_project_only_relative_path_two_repos_is_ambiguous() -> None:
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
                            path="./a",
                            components=[Component(name="web", path="apps/web")],
                        ),
                        ProjectPath(
                            name="edge",
                            path="./b",
                            components=[Component(name="site", path="apps/web")],
                        ),
                    ],
                )
            ]
        ),
    )
    result = ComponentResolver().resolve(config, "apps/web/src/x.ts", project="platform")
    assert isinstance(result, ValueError)


def test_application_paths_resolve() -> None:
    config = MetagitConfig(
        name="metagit-cli",
        kind="cli",
        paths=[ProjectPath(name="metagit-cli", path="src/metagit")],
    )
    row = ComponentResolver().resolve(config, "src/metagit/cli/main.py")
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.id == "metagit-cli/metagit-cli/metagit-cli"


def test_whole_repo_dot_loses_to_nested() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="p",
                    repos=[
                        ProjectPath(
                            name="r",
                            path=".",
                            components=[
                                Component(name="root", path="."),
                                Component(name="web", path="apps/web"),
                            ],
                        )
                    ],
                )
            ]
        ),
    )
    nested = ComponentResolver().resolve(config, "apps/web/x.ts", project="p", repo="r")
    root = ComponentResolver().resolve(config, "README.md", project="p", repo="r")
    assert not isinstance(nested, Exception) and nested is not None
    assert nested.name == "web"
    assert not isinstance(root, Exception) and root is not None
    assert root.name == "root"


def test_filesystem_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "platform"
    target = repo / "apps" / "web" / "src"
    target.mkdir(parents=True)
    (target / "login.tsx").write_text("x\n", encoding="utf-8")
    config = _native()
    row = ComponentResolver().resolve(
        config,
        str(target / "login.tsx"),
        definition_root=tmp_path,
    )
    assert not isinstance(row, Exception)
    assert row is not None
    assert row.name == "web"


def test_payload_shape() -> None:
    row = ComponentResolver().get(_native(), "platform/core/web")
    assert row is not None and not isinstance(row, Exception)
    payload = resolved_component_payload(row)
    assert payload["id"] == "platform/core/web"
    assert payload["path"] == "apps/web"
    assert payload["source"] == "native"
    assert "spec" in payload
