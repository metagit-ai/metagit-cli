#!/usr/bin/env python

"""CLI tests for config patch/preview/tree commands."""

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from metagit.cli.main import cli


def _minimal_metagit(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "name": "cli-patch-test",
                "kind": "application",
                "workspace": {"projects": []},
            }
        ),
        encoding="utf-8",
    )


def test_config_patch_json_omits_tree_unless_requested() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _minimal_metagit(Path(".metagit.yml"))
        bare = runner.invoke(
            cli,
            [
                "config",
                "-c",
                ".metagit.yml",
                "patch",
                "--op",
                "set",
                "--path",
                "name",
                "--value",
                "renamed",
                "--json",
            ],
        )
        assert bare.exit_code == 0, bare.output
        payload = json.loads(bare.output)
        assert "tree" not in payload
        with_tree = runner.invoke(
            cli,
            [
                "config",
                "-c",
                ".metagit.yml",
                "patch",
                "--op",
                "set",
                "--path",
                "name",
                "--value",
                "renamed",
                "--json",
                "--tree",
            ],
        )
        assert with_tree.exit_code == 0, with_tree.output
        assert "tree" in json.loads(with_tree.output)


def test_config_patch_single_op_save() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _minimal_metagit(Path(".metagit.yml"))
        result = runner.invoke(
            cli,
            [
                "config",
                "-c",
                ".metagit.yml",
                "patch",
                "--op",
                "set",
                "--path",
                "name",
                "--value",
                "renamed",
                "--save",
            ],
        )
        assert result.exit_code == 0, result.output
        on_disk = yaml.safe_load(Path(".metagit.yml").read_text(encoding="utf-8"))
        assert on_disk["name"] == "renamed"


def test_config_patch_operations_file() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _minimal_metagit(Path(".metagit.yml"))
        ops_path = Path("ops.json")
        ops_path.write_text(
            json.dumps(
                {
                    "operations": [
                        {"op": "append", "path": "workspace.projects"},
                        {
                            "op": "set",
                            "path": "workspace.projects[0].name",
                            "value": "from-file",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        result = runner.invoke(
            cli,
            [
                "config",
                "-c",
                ".metagit.yml",
                "patch",
                "--file",
                str(ops_path),
                "--save",
            ],
        )
        assert result.exit_code == 0, result.output
        on_disk = yaml.safe_load(Path(".metagit.yml").read_text(encoding="utf-8"))
        assert on_disk["workspace"]["projects"][0]["name"] == "from-file"


def test_config_preview_json() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _minimal_metagit(Path(".metagit.yml"))
        result = runner.invoke(
            cli,
            [
                "config",
                "-c",
                ".metagit.yml",
                "preview",
                "--op",
                "set",
                "--path",
                "name",
                "--value",
                "draft-name",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["draft"] is True
        assert "draft-name" in payload["yaml"]
