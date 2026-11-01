#!/usr/bin/env python
"""Save-path tests: an existing manifest is spliced, never re-dumped."""

from __future__ import annotations

import copy
import difflib
import os
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

import metagit.core.context  # noqa: F401  (loads before catalog to avoid a partial-init cycle)
from metagit.core.config.format_service import ConfigFormatService
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.layout_service import WorkspaceLayoutService

STYLE_MANIFEST = """\
# top comment
name: demo
kind: umbrella
description: old description  # target comment
workspace:
    description: >-
        folded text
        continues here
    projects:
        # comment above the project
        - name: alpha  # keep-me
          description: |
              line one
              line two
          repos:
              # comment above repo one
              - name: r1
                description: |-
                    strip one
                    strip two
              - name: r2
                description: first plain line
                    second plain line
              - name: r3
                description: 'single quoted
                    continues here'
              - name: r4
                description: "double quoted
                    continues here"
              - name: r5
                description: >
                    clip folded
                    second line
"""

STYLE_SNIPPETS = [
    "# top comment\n",
    "workspace:\n    description: >-\n        folded text\n        continues here\n",
    "        # comment above the project\n        - name: alpha  # keep-me\n",
    "          description: |\n              line one\n              line two\n",
    "              # comment above repo one\n",
    "                description: |-\n                    strip one\n                    strip two\n",
    "                description: first plain line\n                    second plain line\n",
    "                description: 'single quoted\n                    continues here'\n",
    '                description: "double quoted\n                    continues here"\n',
    "                description: >\n                    clip folded\n                    second line\n",
]

SMALL_MANIFEST = """\
name: demo
kind: umbrella
description: base description
workspace:
    projects:
        - name: alpha
          repos:
              - name: one
                description: first repo
              - name: two
                description: second repo
"""

LONG_DESCRIPTION = (
    "This description is deliberately longer than eighty-eight columns so a restyle "
    "would wrap it into a block scalar and insert newlines."
)

ALPHA_FRAGMENT = """\
# yaml-language-server: $schema=https://example.com/fragment.schema.json
workspace:
    projects:
        - name: alpha
          repos:
              - name: a1
                description: |
                    moved line one
                    moved line two
              - name: a2
                description: stays behind
"""

BETA_FRAGMENT = """\
# yaml-language-server: $schema=https://example.com/fragment.schema.json
workspace:
    projects:
        - name: beta
          repos:
              - name: b1
                description: {long}
"""

ROOT_MANIFEST = """\
name: umbrella
kind: umbrella
includes:
    - projects/alpha.yml
    - projects/beta.yml
workspace:
    description: split fixture
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _load(path: Path) -> tuple[MetagitConfigManager, MetagitConfig]:
    manager = MetagitConfigManager(path)
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception), loaded
    return manager, loaded


def _changed_lines(before: str, after: str) -> list[str]:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
    return [line for line in diff if line[:1] in "+-" and line[:3] not in ("+++", "---")]


def _split_tree(tmp_path: Path) -> Path:
    root = _write(tmp_path / ".metagit.yml", ROOT_MANIFEST)
    _write(tmp_path / "projects" / "alpha.yml", ALPHA_FRAGMENT)
    _write(tmp_path / "projects" / "beta.yml", BETA_FRAGMENT.format(long=LONG_DESCRIPTION))
    return root


def test_style_fixture_touches_only_the_edited_key(tmp_path: Path) -> None:
    manifest = _write(tmp_path / ".metagit.yml", STYLE_MANIFEST)
    manager, loaded = _load(manifest)
    loaded.description = "new description"
    assert manager.save_config(loaded) is None
    after = manifest.read_text(encoding="utf-8")
    assert _changed_lines(STYLE_MANIFEST, after) == [
        "-description: old description  # target comment",
        "+description: new description  # target comment",
    ]
    for snippet in STYLE_SNIPPETS:
        assert snippet in after
    before_data = yaml.safe_load(STYLE_MANIFEST)
    after_data = yaml.safe_load(after)
    assert after_data["description"] == "new description"
    before_data["description"] = "new description"
    assert after_data == before_data


def _set_description(config: MetagitConfig) -> None:
    config.description = "changed"


def _set_multiline(config: MetagitConfig) -> None:
    config.description = "line one\nline two"


def _add_key(config: MetagitConfig) -> None:
    config.workspace.projects[0].description = "added"


def _delete_key(config: MetagitConfig) -> None:
    config.workspace.projects[0].repos[0].description = None


def _append_repo(config: MetagitConfig) -> None:
    config.workspace.projects[0].repos.append(ProjectPath(name="three", description="third repo"))


def _delete_repo(config: MetagitConfig) -> None:
    config.workspace.projects[0].repos.pop(0)


def _expect_set(data: dict[str, Any]) -> None:
    data["description"] = "changed"


def _expect_multiline(data: dict[str, Any]) -> None:
    data["description"] = "line one\nline two"


def _expect_add(data: dict[str, Any]) -> None:
    data["workspace"]["projects"][0]["description"] = "added"


def _expect_delete(data: dict[str, Any]) -> None:
    del data["workspace"]["projects"][0]["repos"][0]["description"]


def _expect_append(data: dict[str, Any]) -> None:
    data["workspace"]["projects"][0]["repos"].append({"name": "three", "description": "third repo"})


def _expect_delete_repo(data: dict[str, Any]) -> None:
    data["workspace"]["projects"][0]["repos"].pop(0)


@pytest.mark.parametrize(
    ("mutate", "expect"),
    [
        (_set_description, _expect_set),
        (_set_multiline, _expect_multiline),
        (_add_key, _expect_add),
        (_delete_key, _expect_delete),
        (_append_repo, _expect_append),
        (_delete_repo, _expect_delete_repo),
    ],
    ids=["set", "set_multiline", "add_key", "delete_key", "append_repo", "delete_repo"],
)
def test_single_edit_changes_only_the_edited_path(
    tmp_path: Path,
    mutate: Callable[[MetagitConfig], None],
    expect: Callable[[dict[str, Any]], None],
) -> None:
    manifest = _write(tmp_path / ".metagit.yml", SMALL_MANIFEST)
    manager, loaded = _load(manifest)
    mutate(loaded)
    assert manager.save_config(loaded) is None
    expected = copy.deepcopy(yaml.safe_load(SMALL_MANIFEST))
    expect(expected)
    assert yaml.safe_load(manifest.read_text(encoding="utf-8")) == expected


def _freeze(path: Path) -> int:
    stale = path.stat().st_mtime_ns - 10_000_000_000
    os.utime(path, ns=(stale, stale))
    return stale


def test_noop_save_leaves_single_file_untouched(tmp_path: Path) -> None:
    manifest = _write(tmp_path / ".metagit.yml", STYLE_MANIFEST)
    manager, _loaded = _load(manifest)
    stale = _freeze(manifest)
    assert manager.save_config() is None
    assert manifest.read_text(encoding="utf-8") == STYLE_MANIFEST
    assert manifest.stat().st_mtime_ns == stale


def test_noop_save_leaves_split_fragments_untouched(tmp_path: Path) -> None:
    root = _split_tree(tmp_path)
    files = [root, tmp_path / "projects" / "alpha.yml", tmp_path / "projects" / "beta.yml"]
    before = {path: path.read_bytes() for path in files}
    manager, _loaded = _load(root)
    stale = {path: _freeze(path) for path in files}
    assert manager.save_config() is None
    for path in files:
        assert path.read_bytes() == before[path]
        assert path.stat().st_mtime_ns == stale[path]


def test_no_format_save_does_not_rewrite_untouched_strings(tmp_path: Path) -> None:
    text = SMALL_MANIFEST.replace("first repo", LONG_DESCRIPTION)
    manifest = _write(tmp_path / ".metagit.yml", text)
    manager, loaded = _load(manifest)
    loaded.description = "changed"
    assert manager.save_config(loaded, auto_format=False) is None
    after = manifest.read_text(encoding="utf-8")
    assert f"description: {LONG_DESCRIPTION}\n" in after
    assert _changed_lines(text, after) == [
        "-description: base description",
        "+description: changed",
    ]


def test_save_to_a_missing_path_uses_the_existing_renderer(tmp_path: Path) -> None:
    _manager, loaded = _load(_write(tmp_path / "source.yml", SMALL_MANIFEST))
    destination = tmp_path / "new.yml"
    assert MetagitConfigManager(config_path=destination).save_config(loaded, destination) is None
    assert destination.read_text(encoding="utf-8") == ConfigFormatService().render_metagit(loaded, original_text="")


def test_save_to_a_missing_path_without_format_dumps_yaml(tmp_path: Path) -> None:
    _manager, loaded = _load(_write(tmp_path / "source.yml", SMALL_MANIFEST))
    destination = tmp_path / "new.yml"
    assert MetagitConfigManager(config_path=destination).save_config(loaded, destination, auto_format=False) is None
    assert yaml.safe_load(destination.read_text(encoding="utf-8"))["name"] == "demo"


def test_flow_style_mapping_aborts_and_leaves_the_file(tmp_path: Path) -> None:
    text = "name: demo\nkind: umbrella\nworkspace: {description: shared, projects: []}\n"
    manifest = _write(tmp_path / ".metagit.yml", text)
    manager, loaded = _load(manifest)
    loaded.workspace.description = "edited"
    outcome = manager.save_config(loaded)
    assert isinstance(outcome, Exception)
    assert manifest.read_text(encoding="utf-8") == text


def test_failed_splice_in_one_fragment_writes_no_file(tmp_path: Path) -> None:
    root = _split_tree(tmp_path)
    beta = tmp_path / "projects" / "beta.yml"
    flow = "workspace:\n    projects:\n        - {name: beta, description: flow, repos: []}\n"
    beta.write_text(flow, encoding="utf-8")
    alpha = tmp_path / "projects" / "alpha.yml"
    manager, loaded = _load(root)
    for project in loaded.workspace.projects:
        project.description = f"edited {project.name}"
    outcome = manager.save_config(loaded)
    assert isinstance(outcome, Exception)
    assert alpha.read_text(encoding="utf-8") == ALPHA_FRAGMENT
    assert beta.read_text(encoding="utf-8") == flow
    assert root.read_text(encoding="utf-8") == ROOT_MANIFEST


def test_move_repo_between_fragments_changes_only_the_moved_item(tmp_path: Path) -> None:
    root = _split_tree(tmp_path)
    alpha = tmp_path / "projects" / "alpha.yml"
    beta = tmp_path / "projects" / "beta.yml"
    alpha_before = alpha.read_text(encoding="utf-8")
    beta_before = beta.read_text(encoding="utf-8")
    root_before = root.read_text(encoding="utf-8")
    _manager, loaded = _load(root)
    result = WorkspaceLayoutService().move_repo(
        loaded,
        str(root),
        str(tmp_path),
        repo_name="a1",
        from_project="alpha",
        to_project="beta",
        move_disk=False,
    )
    assert result.ok, result.error
    item = (
        "              - name: a1\n"
        "                description: |\n"
        "                    moved line one\n"
        "                    moved line two\n"
    )
    alpha_after = alpha.read_text(encoding="utf-8")
    beta_after = beta.read_text(encoding="utf-8")
    assert alpha_after == alpha_before.replace(item, "")
    assert beta_after == beta_before + item
    assert "description: stays behind\n" in alpha_after
    assert f"description: {LONG_DESCRIPTION}\n" in beta_after
    assert root.read_text(encoding="utf-8") == root_before


BLANK_LINE_DESCRIPTION = "one\n  \ntwo\n"


def _blank_line_tree(tmp_path: Path) -> Path:
    alpha = ALPHA_FRAGMENT.replace(
        "                    moved line one\n                    moved line two\n",
        "                    one\n                      \n                    two\n",
    )
    assert yaml.safe_load(alpha)["workspace"]["projects"][0]["repos"][0]["description"] == BLANK_LINE_DESCRIPTION
    root = _write(tmp_path / ".metagit.yml", ROOT_MANIFEST)
    _write(tmp_path / "projects" / "alpha.yml", alpha)
    _write(tmp_path / "projects" / "beta.yml", BETA_FRAGMENT.format(long=LONG_DESCRIPTION))
    return root


@pytest.mark.parametrize("language", [None, "python"])
def test_move_keeps_whitespace_only_line_inside_literal_block(tmp_path: Path, language: str | None) -> None:
    root = _blank_line_tree(tmp_path)
    beta = tmp_path / "projects" / "beta.yml"
    manager, loaded = _load(root)
    alpha_project, beta_project = loaded.workspace.projects
    moved = alpha_project.repos.pop(0)
    moved.language = language
    beta_project.repos.append(moved)
    assert manager.save_config(loaded) is None
    beta_text = beta.read_text(encoding="utf-8")
    assert "                    one\n                      \n                    two\n" in beta_text
    repos = yaml.safe_load(beta_text)["workspace"]["projects"][0]["repos"]
    assert repos[1]["name"] == "a1"
    assert repos[1]["description"] == BLANK_LINE_DESCRIPTION


def test_move_with_field_edit_splices_into_the_moved_text(tmp_path: Path) -> None:
    root = _split_tree(tmp_path)
    alpha = tmp_path / "projects" / "alpha.yml"
    beta = tmp_path / "projects" / "beta.yml"
    manager, loaded = _load(root)
    alpha_project, beta_project = loaded.workspace.projects
    moved = alpha_project.repos.pop(0)
    moved.language = "python"
    beta_project.repos.append(moved)
    assert manager.save_config(loaded) is None
    beta_after = beta.read_text(encoding="utf-8")
    assert (
        "              - name: a1\n"
        "                description: |\n"
        "                    moved line one\n"
        "                    moved line two\n"
        "                language: python\n"
    ) in beta_after
    assert f"description: {LONG_DESCRIPTION}\n" in beta_after
    assert "a1" not in alpha.read_text(encoding="utf-8")
    assert "description: stays behind\n" in alpha.read_text(encoding="utf-8")
