#!/usr/bin/env python
"""CLI tests for metagit project repo promote."""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner
from git import Repo

from metagit.cli.main import cli


def _init_local_git_repo(path: Path, *, remote_url: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    readme = path / "README.md"
    readme.write_text("hello", encoding="utf-8")
    repo.index.add([str(readme.relative_to(path))])
    repo.index.commit("init")
    repo.create_remote("origin", remote_url)


def test_project_repo_promote_dry_run_json(tmp_path: Path) -> None:
    source = tmp_path / "user-repo"
    remote_url = "https://github.com/example-org/example.git"
    _init_local_git_repo(source, remote_url=remote_url)

    workspace = tmp_path / ".metagit"
    metagit_yml = tmp_path / ".metagit.yml"
    metagit_yml.write_text(
        "\n".join(
            [
                "name: test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: example",
                f"          path: {str(source).replace(os.sep, '/')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    app_cfg = tmp_path / "metagit.config.yaml"
    app_cfg.write_text(
        "\n".join(
            [
                "config:",
                "  description: test",
                "  workspace:",
                f"    path: {str(workspace).replace(os.sep, '/')}",
                "    default_project: platform",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "project",
            "-c",
            str(metagit_yml),
            "--project",
            "platform",
            "repo",
            "promote",
            "--name",
            "example",
            "--dry-run",
            "--json",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert '"ok": true' in result.output
    assert remote_url in result.output
