#!/usr/bin/env python
"""Release acceptance for 0.38.2. Each test locks one changelog claim."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli
from metagit.core.config.manifest_diff import diff_manifests

ROOT = """\
name: umbrella
kind: umbrella
includes:
  - .metagit.d/projects/platform.yml
  - .metagit.d/projects/zz-probe.yml
  - .metagit.d/graph/nodes.yml
  - .metagit.d/graph/relationships.yml
"""

PLATFORM = """\
workspace:
  projects:
    - name: platform
      repos:
        - name: admin-api
          url: git@git.ssh.example:acme/admin-api.git
        - name: other
          url: https://github.com/acme/other.git
        - name: worker
          url: https://github.com/acme/worker.git
"""

PROBE = """\
workspace:
  projects:
    - name: zz-probe
      repos: []
"""

NODES = """\
graph:
  nodes:
    - identity: platform/admin-api
      name: admin-api
    - identity: github://acme/admin-api
      name: admin-api
"""

RELATIONSHIPS = """\
graph:
  relationships:
    - id: edge-a
      from:
        project: platform
        repo: admin-api
      to:
        project: platform
        repo: other
      type: depends_on
    - id: edge-b
      from:
        project: platform
        repo: admin-api
      to:
        identity: platform/admin-api
      type: related
"""


def _write(tmp_path: Path) -> Path:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(ROOT, encoding="utf-8")
    projects = tmp_path / ".metagit.d" / "projects"
    graph = tmp_path / ".metagit.d" / "graph"
    projects.mkdir(parents=True)
    graph.mkdir()
    (projects / "platform.yml").write_text(PLATFORM, encoding="utf-8")
    (projects / "zz-probe.yml").write_text(PROBE, encoding="utf-8")
    (graph / "nodes.yml").write_text(NODES, encoding="utf-8")
    (graph / "relationships.yml").write_text(RELATIONSHIPS, encoding="utf-8")
    return manifest


def _invoke(runner: CliRunner, args: list[str]) -> object:
    return runner.invoke(cli, ["--config", DEFAULT_CONFIG, *args])


def test_move_rewrites_graph_endpoints_in_the_owning_fragment(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    runner = CliRunner()
    dry = _invoke(
        runner,
        [
            "project",
            "-c",
            str(manifest),
            "-p",
            "platform",
            "repo",
            "move",
            "-n",
            "admin-api",
            "--to-project",
            "zz-probe",
            "--manifest-only",
            "--dry-run",
        ],
    )
    assert dry.exit_code == 0, dry.output
    assert "graph.relationships[id=edge-a].from_endpoint.project: platform -> zz-probe" in dry.output
    root_before = manifest.read_text(encoding="utf-8")

    moved = _invoke(
        runner,
        [
            "project",
            "-c",
            str(manifest),
            "-p",
            "platform",
            "repo",
            "move",
            "-n",
            "admin-api",
            "--to-project",
            "zz-probe",
            "--manifest-only",
            "--json",
        ],
    )
    assert moved.exit_code == 0, moved.output
    payload = json.loads(moved.output)
    changes = payload["data"]["manifest_changes"]
    assert "graph.relationships[id=edge-a].from_endpoint.project: platform -> zz-probe" in changes
    relationships = (tmp_path / ".metagit.d" / "graph" / "relationships.yml").read_text(encoding="utf-8")
    assert "project: zz-probe" in relationships
    assert relationships.count("repo: admin-api") == 2
    assert "identity: zz-probe/admin-api" in relationships
    assert "project: platform\n        repo: admin-api" not in relationships
    nodes = (tmp_path / ".metagit.d" / "graph" / "nodes.yml").read_text(encoding="utf-8")
    assert "identity: zz-probe/admin-api" in nodes
    assert "identity: github://acme/admin-api" in nodes
    assert "git@git.ssh.example:acme/admin-api.git" in (tmp_path / ".metagit.d" / "projects" / "zz-probe.yml").read_text(
        encoding="utf-8"
    )
    assert manifest.read_text(encoding="utf-8") == root_before

    checked = _invoke(runner, ["config", "-c", str(manifest), "validate"])
    assert checked.exit_code == 0, checked.output
    strict = _invoke(runner, ["config", "-c", str(manifest), "validate", "--strict"])
    assert strict.exit_code == 0, strict.output


def test_validate_reports_a_stale_project_repo_endpoint(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    runner = CliRunner()
    moved = _invoke(
        runner,
        [
            "project",
            "-c",
            str(manifest),
            "repo",
            "move",
            "-n",
            "admin-api",
            "--to-project",
            "zz-probe",
            "--manifest-only",
        ],
    )
    assert moved.exit_code == 0, moved.output
    fragment = tmp_path / ".metagit.d" / "graph" / "relationships.yml"
    text = fragment.read_text(encoding="utf-8")
    fragment.write_text(text.replace("project: zz-probe", "project: platform", 1), encoding="utf-8")

    normal = _invoke(runner, ["config", "-c", str(manifest), "validate", "--json"])
    strict = _invoke(runner, ["config", "-c", str(manifest), "validate", "--strict", "--json"])
    expected = (
        "graph.relationships[id=edge-a].from: repo 'admin-api' is not in project 'platform' "
        "(it is declared in 'zz-probe')"
    )
    assert normal.exit_code == 1, normal.output
    assert strict.exit_code == 1, strict.output
    normal_errors = json.loads(normal.output)["errors"]
    strict_errors = json.loads(strict.output)["errors"]
    assert any(expected in str(item.get("message", item)) for item in normal_errors)
    assert any(expected in str(item.get("message", item)) for item in strict_errors)
    assert "Traceback" not in normal.output


def test_config_set_parses_maps_and_keeps_selectors(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    runner = CliRunner()
    path = "workspace.projects[name=platform].repos[name=other].tags"
    bad = _invoke(runner, ["config", "-c", str(manifest), "set", path, "not-json"])
    assert bad.exit_code != 0
    assert path in bad.output
    assert "not-json" not in (tmp_path / ".metagit.d" / "projects" / "platform.yml").read_text(encoding="utf-8")

    good = _invoke(runner, ["config", "-c", str(manifest), "set", path, '{"type":"application"}'])
    assert good.exit_code == 0, good.output
    assert path in good.output
    stored = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "platform.yml").read_text(encoding="utf-8"))
    repo = stored["workspace"]["projects"][0]["repos"][1]
    assert repo["tags"] == {"type": "application"}

    again = _invoke(runner, ["config", "-c", str(manifest), "set", path, "{team: core}"])
    assert again.exit_code == 0, again.output
    stored = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "platform.yml").read_text(encoding="utf-8"))
    assert stored["workspace"]["projects"][0]["repos"][1]["tags"] == {"team": "core"}


def test_patch_appends_the_value_and_honours_save_in_the_file(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    runner = CliRunner()
    missing = _invoke(
        runner,
        [
            "config",
            "-c",
            str(manifest),
            "patch",
            "--op",
            "append",
            "--path",
            "workspace.projects[name=zz-probe].repos",
            "--save",
        ],
    )
    assert missing.exit_code != 0
    assert "example-name" not in (tmp_path / ".metagit.d" / "projects" / "zz-probe.yml").read_text(encoding="utf-8")

    appended = _invoke(
        runner,
        [
            "config",
            "-c",
            str(manifest),
            "patch",
            "--op",
            "append",
            "--path",
            "workspace.projects[name=zz-probe].repos",
            "--value",
            '{"name":"extra","url":"https://github.com/acme/extra.git"}',
            "--save",
        ],
    )
    assert appended.exit_code == 0, appended.output
    probe = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "zz-probe.yml").read_text(encoding="utf-8"))
    assert probe["workspace"]["projects"][0]["repos"][0]["name"] == "extra"

    ops = tmp_path / "ops.json"
    ops.write_text(
        json.dumps(
            {
                "save": True,
                "operations": [{"op": "set", "path": "name", "value": "renamed-umbrella"}],
            }
        ),
        encoding="utf-8",
    )
    saved = _invoke(runner, ["config", "-c", str(manifest), "patch", "--file", str(ops)])
    assert saved.exit_code == 0, saved.output
    assert "renamed-umbrella" in manifest.read_text(encoding="utf-8")

    ops.write_text(json.dumps({"save": True, "operations": [], "nope": 1}), encoding="utf-8")
    rejected = _invoke(runner, ["config", "-c", str(manifest), "patch", "--file", str(ops)])
    assert rejected.exit_code != 0
    assert "nope" in rejected.output


def test_printed_paths_resolve_and_bad_selectors_exit_2(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    runner = CliRunner()
    fetched = _invoke(
        runner,
        [
            "config",
            "-c",
            str(manifest),
            "get",
            "graph.relationships[id=edge-b].from.project",
        ],
    )
    assert fetched.exit_code == 0, fetched.output
    assert fetched.output.strip() == "platform"
    node = _invoke(
        runner,
        ["config", "-c", str(manifest), "get", "graph.nodes[id=github://acme/admin-api].identity"],
    )
    assert node.exit_code == 0, node.output
    assert node.output.strip() == "github://acme/admin-api"

    bad = _invoke(
        runner,
        ["config", "-c", str(manifest), "get", "workspace.projects[name=missing].name", "--json"],
    )
    assert bad.exit_code == 2, bad.output
    assert "Traceback" not in bad.output
    payload = json.loads(bad.output)
    assert payload["ok"] is False
    assert "Candidates" in payload["error"]


def test_glob_split_diff_reports_one_order_entry(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: umbrella\nkind: umbrella\nworkspace:\n  projects:\n"
        "    - name: zebra\n      repos:\n        - name: api\n          url: https://github.com/acme/api.git\n"
        "    - name: alpha\n      repos:\n        - name: web\n          url: https://github.com/acme/web.git\n",
        encoding="utf-8",
    )
    original = tmp_path / "original.yml"
    original.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")
    runner = CliRunner()
    split = _invoke(
        runner,
        ["config", "-c", str(manifest), "split", "--by", "all", "--glob"],
    )
    assert split.exit_code == 0, split.output
    diffs = diff_manifests(str(original), str(manifest), mode="raw", cwd=tmp_path)
    assert [item.kind for item in diffs if item.kind != "order"] == []
    assert [item.kind for item in diffs] == ["order"]
    indexed = diff_manifests(str(original), str(manifest), mode="raw", cwd=tmp_path, by_index=True)
    assert any(item.kind == "value" for item in indexed)


def test_repo_add_tag_and_multi_move_is_atomic(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    runner = CliRunner()
    added = _invoke(
        runner,
        [
            "project",
            "-c",
            str(manifest),
            "-p",
            "platform",
            "repo",
            "add",
            "-n",
            "tagged",
            "--url",
            "https://github.com/acme/tagged.git",
            "--tag",
            "type=application",
            "--tag",
            "team=core",
        ],
    )
    assert added.exit_code == 0, added.output
    platform = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "platform.yml").read_text(encoding="utf-8"))
    tagged = next(repo for repo in platform["workspace"]["projects"][0]["repos"] if repo["name"] == "tagged")
    assert tagged["tags"] == {"type": "application", "team": "core"}

    refused = _invoke(
        runner,
        [
            "project",
            "-c",
            str(manifest),
            "-p",
            "platform",
            "repo",
            "move",
            "-n",
            "other",
            "-n",
            "missing",
            "--to-project",
            "zz-probe",
            "--manifest-only",
        ],
    )
    assert refused.exit_code != 0
    still = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "platform.yml").read_text(encoding="utf-8"))
    names = [repo["name"] for repo in still["workspace"]["projects"][0]["repos"]]
    assert "other" in names

    moved = _invoke(
        runner,
        [
            "project",
            "-c",
            str(manifest),
            "-p",
            "platform",
            "repo",
            "move",
            "-n",
            "other",
            "-n",
            "worker",
            "--to-project",
            "zz-probe",
            "--manifest-only",
        ],
    )
    assert moved.exit_code == 0, moved.output
    platform = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "platform.yml").read_text(encoding="utf-8"))
    probe = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "zz-probe.yml").read_text(encoding="utf-8"))
    left = {repo["name"] for repo in platform["workspace"]["projects"][0]["repos"]}
    right = {repo["name"] for repo in probe["workspace"]["projects"][0]["repos"]}
    assert "other" not in left and "worker" not in left
    assert {"other", "worker"} <= right


def test_merge_help_states_the_checked_out_target_rule() -> None:
    runner = CliRunner()
    result = _invoke(runner, ["merge", "--help"])
    assert result.exit_code == 0, result.output
    text = re.sub(r"\s+", " ", result.output)
    assert "No flag overrides this" in text
    assert "git -C <path> switch --detach" in text
