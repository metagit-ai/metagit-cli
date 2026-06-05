#!/usr/bin/env python

"""Tests for GitNexus group sync service."""

from pathlib import Path
from unittest.mock import MagicMock

from metagit.core.config.models import MetagitConfig
from metagit.core.gitnexus.group_sync import (
    GitNexusGroupRunner,
    GitNexusGroupSyncService,
    load_group_repo_paths,
    normalize_group_name,
)
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


class _FakeRunner(GitNexusGroupRunner):
    def __init__(self, groups_root: Path) -> None:
        super().__init__(groups_root=groups_root, runner=self._fake_run)
        self.calls: list[list[str]] = []
        self._groups_root = groups_root
        self._groups_root.mkdir(parents=True, exist_ok=True)

    def _fake_run(self, cmd, **kwargs):
        self.calls.append(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stdout = '{"contracts": [], "crossLinks": []}'
        result.stderr = ""
        if "group" in cmd and "create" in cmd:
            group_name = cmd[-1]
            group_dir = self._groups_root / group_name
            group_dir.mkdir(parents=True, exist_ok=True)
            (group_dir / "group.yaml").write_text(
                "version: 1\nname: {}\nrepos: {{}}\n".format(group_name),
                encoding="utf-8",
            )
        if "group" in cmd and "add" in cmd:
            group_name = cmd[cmd.index("add") + 1]
            group_path = cmd[cmd.index("add") + 2]
            registry_name = cmd[cmd.index("add") + 3]
            yaml_path = self._groups_root / group_name / "group.yaml"
            text = yaml_path.read_text(encoding="utf-8")
            if "repos:" not in text:
                text += "repos: {}\n"
            repos = load_group_repo_paths(yaml_path)
            repos[group_path] = registry_name
            lines = [
                "version: 1",
                f"name: {group_name}",
                "repos:",
            ]
            for key, value in repos.items():
                lines.append(f"  {key}: {value}")
            yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return result


def _workspace_config(tmp_path: Path) -> tuple[MetagitConfig, str]:
    root = tmp_path / "workspace"
    alpha = root / "alpha" / "api"
    alpha.mkdir(parents=True)
    (alpha / ".git").mkdir()
    return (
        MetagitConfig(
            name="My Workspace",
            workspace=Workspace(
                projects=[
                    WorkspaceProject(
                        name="alpha",
                        repos=[
                            ProjectPath(
                                name="api",
                                path="alpha/api",
                                url="https://example.com/a.git",
                            )
                        ],
                    )
                ]
            ),
        ),
        str(root),
    )


def test_normalize_group_name_slugifies_manifest_name() -> None:
    assert normalize_group_name("My Workspace") == "my-workspace"


def test_sync_workspace_creates_group_and_adds_indexed_repo(tmp_path: Path) -> None:
    config, workspace_root = _workspace_config(tmp_path)
    alpha_path = str(tmp_path / "workspace" / "alpha" / "api")
    registry = MagicMock()
    registry.registry_name_for_path.return_value = "alpha-api"
    runner = _FakeRunner(tmp_path / "groups")

    result = GitNexusGroupSyncService(
        registry=registry,
        runner=runner,
    ).sync_workspace(
        config,
        workspace_root,
        group_name="test-group",
        run_contract_sync=True,
    )

    assert result.ok is True
    assert result.created_group is True
    assert len(result.added) == 1
    assert result.added[0].group_path == "alpha/api"
    assert result.added[0].registry_name == "alpha-api"
    assert result.contract_sync_ran is True
    registry.registry_name_for_path.assert_called_once_with(repo_path=alpha_path)
    assert any("group" in call and "sync" in call for call in runner.calls)


def test_sync_workspace_skips_missing_registry(tmp_path: Path) -> None:
    config, workspace_root = _workspace_config(tmp_path)
    registry = MagicMock()
    registry.registry_name_for_path.return_value = None
    runner = _FakeRunner(tmp_path / "groups")
    (tmp_path / "groups" / "ws").mkdir(parents=True)
    (tmp_path / "groups" / "ws" / "group.yaml").write_text(
        "version: 1\nname: ws\nrepos: {}\n",
        encoding="utf-8",
    )
    runner._groups_root = tmp_path / "groups"

    result = GitNexusGroupSyncService(
        registry=registry,
        runner=runner,
    ).sync_workspace(
        config,
        workspace_root,
        group_name="ws",
        create_group=False,
        run_contract_sync=False,
    )

    assert result.ok is True
    assert not result.added
    assert result.skipped
    assert result.skipped[0]["reason"] == "not_in_gitnexus_registry"
