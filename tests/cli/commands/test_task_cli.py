#!/usr/bin/env python
"""CLI tests for metagit task (RFC-0008)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _env(root: Path) -> dict[str, str]:
    return {**os.environ, "METAGIT_WORKSPACE_PATH": str(root.resolve())}


def _write_manifest(root: Path) -> None:
    (root / ".metagit.yml").write_text(
        "name: workspace\nkind: application\ndescription: taskgraph fixture\n",
        encoding="utf-8",
    )


def test_task_create_expand_ready_complete_json() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_manifest(root)
        create = runner.invoke(
            cli,
            [
                "task",
                "create",
                "--title",
                "Demo",
                "--goal",
                "Ship",
                "--graph-id",
                "demo-graph",
                "--json",
            ],
            env=_env(root),
            catch_exceptions=False,
        )
        assert create.exit_code == 0, create.output
        payload = json.loads(create.output)
        assert payload["graph_id"] == "demo-graph"

        outline = json.dumps(
            [
                {"node_id": "root", "title": "Root"},
                {"node_id": "child", "title": "Child", "depends_on": ["root"]},
            ]
        )
        expand = runner.invoke(
            cli,
            ["task", "expand", "--graph-id", "demo-graph", "--json"],
            input=outline,
            env=_env(root),
            catch_exceptions=False,
        )
        assert expand.exit_code == 0, expand.output

        ready = runner.invoke(
            cli,
            ["task", "ready", "--graph-id", "demo-graph", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert ready.exit_code == 0, ready.output
        ready_payload = json.loads(ready.output)
        assert [n["node_id"] for n in ready_payload["nodes"]] == ["root"]

        complete = runner.invoke(
            cli,
            ["task", "complete", "--node-id", "root", "--graph-id", "demo-graph", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert complete.exit_code == 0, complete.output

        ready2 = runner.invoke(
            cli,
            ["task", "ready", "--graph-id", "demo-graph", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert ready2.exit_code == 0
        assert [n["node_id"] for n in json.loads(ready2.output)["nodes"]] == ["child"]

        listed = runner.invoke(
            cli,
            ["task", "list", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert listed.exit_code == 0
        assert "demo-graph" in listed.output
