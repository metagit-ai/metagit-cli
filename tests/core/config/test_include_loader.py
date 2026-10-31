#!/usr/bin/env python
"""Unit tests for multi-file manifest includes."""

from __future__ import annotations

import os
from pathlib import Path

from metagit.core.config.include_loader import (
    MAX_INCLUDE_DEPTH,
    load_composed_manifest,
    manifest_declares_includes,
)
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.utils import yaml_class


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _root(tmp_path: Path, includes: str, body: str = "name: umbrella\nkind: umbrella\n") -> Path:
    path = tmp_path / ".metagit.yml"
    _write(path, f"{body}includes:\n{includes}")
    return path


def test_glob_order_is_lexicographic(tmp_path: Path) -> None:
    _write(
        tmp_path / "parts" / "b.yml",
        "workspace:\n  projects:\n    - name: beta\n      repos: []\n",
    )
    _write(
        tmp_path / "parts" / "a.yml",
        "workspace:\n  projects:\n    - name: alpha\n      repos: []\n",
    )
    root = _root(tmp_path, "  - parts/*.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert not isinstance(loaded, Exception)
    assert [project.name for project in loaded.workspace.projects] == ["alpha", "beta"]


def test_nested_include_resolves_against_fragment_directory(tmp_path: Path) -> None:
    _write(
        tmp_path / ".metagit.d" / "nested" / "leaf.yml",
        "workspace:\n  projects:\n    - name: leaf\n      repos: []\n",
    )
    _write(
        tmp_path / ".metagit.d" / "mid.yml",
        "includes:\n  - nested/leaf.yml\n",
    )
    root = _root(tmp_path, "  - .metagit.d/mid.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert not isinstance(loaded, Exception)
    assert loaded.workspace.projects[0].name == "leaf"


def test_absolute_parent_url_and_symlink_are_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-include.yml"
    _write(outside, "name: outside\nkind: application\n")
    link = tmp_path / "escape.yml"
    link.symlink_to(outside)

    cases = {
        "absolute": "  - /etc/passwd\n",
        "escape": "  - ../outside-include.yml\n",
        "url": "  - https://example.com/a.yml\n",
        "symlink": "  - escape.yml\n",
    }
    for label, includes in cases.items():
        root = _root(tmp_path, includes)
        loaded = MetagitConfigManager(root).load_config()
        assert isinstance(loaded, Exception), label
        message = str(loaded)
        assert ".metagit.yml:" in message
        if label == "url":
            assert "URL" in message
        elif label == "absolute":
            assert "absolute" in message
        elif label == "symlink":
            assert "symlink" in message
        else:
            assert "escapes" in message


def test_cycle_depth_and_same_file_twice(tmp_path: Path) -> None:
    _write(tmp_path / "a.yml", "includes:\n  - b.yml\n")
    _write(tmp_path / "b.yml", "includes:\n  - a.yml\n")
    root = _root(tmp_path, "  - a.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    assert "include cycle" in str(loaded)

    chain = tmp_path / "chain"
    previous = "start.yml"
    _write(chain / previous, "name: ignored\n")
    for index in range(MAX_INCLUDE_DEPTH + 1):
        name = f"level-{index}.yml"
        _write(chain / name, f"includes:\n  - {previous}\n")
        previous = name
    root = _root(tmp_path, f"  - chain/{previous}\n")
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    assert "depth" in str(loaded)

    _write(tmp_path / "once.yml", "workspace:\n  projects:\n    - name: once\n      repos: []\n")
    root = _root(tmp_path, "  - once.yml\n  - once.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    assert "more than once" in str(loaded)


def test_duplicate_project_names_report_both_locations(tmp_path: Path) -> None:
    _write(
        tmp_path / "one.yml",
        "workspace:\n  projects:\n    - name: api\n      repos: []\n",
    )
    _write(
        tmp_path / "two.yml",
        "workspace:\n  projects:\n    - name: api\n      repos: []\n",
    )
    root = _root(tmp_path, "  - one.yml\n  - two.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    message = str(loaded)
    assert "duplicate project name" in message
    assert "one.yml:" in message
    assert "two.yml:" in message


def test_disallowed_fragment_key_and_shared_scalar(tmp_path: Path) -> None:
    _write(tmp_path / "bad.yml", "name: other\nkind: application\n")
    root = _root(tmp_path, "  - bad.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    assert "not allowed" in str(loaded)
    assert "bad.yml:" in str(loaded)

    _write(tmp_path / "desc.yml", "workspace:\n  description: from-fragment\n")
    root = _root(
        tmp_path,
        "  - desc.yml\n",
        body="name: umbrella\nkind: umbrella\nworkspace:\n  description: from-root\n",
    )
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    assert "workspace.description" in str(loaded)
    assert "defined in both" in str(loaded)


def test_empty_glob_is_ok_and_missing_literal_is_not(tmp_path: Path) -> None:
    root = _root(tmp_path, "  - missing/*.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert not isinstance(loaded, Exception)
    assert loaded.name == "umbrella"
    assert manifest_declares_includes(root) is True

    root = _root(tmp_path, "  - missing.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    assert "not found" in str(loaded)
    assert ".metagit.yml:" in str(loaded)


def test_validation_error_points_at_fragment_line(tmp_path: Path) -> None:
    _write(
        tmp_path / "alpha.yml",
        "workspace:\n  projects:\n    - name: alpha\n      unexpected: true\n      repos: []\n",
    )
    root = _root(tmp_path, "  - alpha.yml\n")
    loaded = MetagitConfigManager(root).load_config()
    assert isinstance(loaded, Exception)
    message = str(loaded)
    assert "alpha.yml:" in message
    assert "unexpected" in message or "Extra" in message


def test_split_load_matches_single_file_model(tmp_path: Path) -> None:
    single = tmp_path / "single.yml"
    _write(
        single,
        "name: umbrella\nkind: umbrella\nworkspace:\n  projects:\n"
        "    - name: alpha\n      repos: []\n"
        "    - name: beta\n      repos: []\n",
    )
    single_model = MetagitConfigManager(single).load_config()
    assert not isinstance(single_model, Exception)
    root = tmp_path / ".metagit.yml"
    _write(
        root,
        "name: umbrella\nkind: umbrella\nincludes:\n  - .metagit.d/alpha.yml\n  - .metagit.d/beta.yml\n",
    )
    _write(tmp_path / ".metagit.d" / "alpha.yml", "workspace:\n  projects:\n    - name: alpha\n      repos: []\n")
    _write(tmp_path / ".metagit.d" / "beta.yml", "workspace:\n  projects:\n    - name: beta\n      repos: []\n")
    split_model = MetagitConfigManager(root).load_config()
    assert not isinstance(split_model, Exception)
    assert split_model.model_dump(mode="json", exclude_none=True) == single_model.model_dump(
        mode="json",
        exclude_none=True,
    )
    assert "includes" not in split_model.model_dump(exclude_none=True)


def test_include_yaml_tag_is_rejected() -> None:
    loaded = yaml_class.load("a: !include other.yml\n")
    assert isinstance(loaded, Exception)


def test_duplicate_graph_node_and_relationship(tmp_path: Path) -> None:
    _write(
        tmp_path / "nodes-a.yml",
        "graph:\n  nodes:\n    - identity: github://acme/api\n      name: api\n",
    )
    _write(
        tmp_path / "nodes-b.yml",
        "graph:\n  nodes:\n    - identity: github://acme/api\n      name: api\n",
    )
    root = _root(tmp_path, "  - nodes-a.yml\n  - nodes-b.yml\n")
    loaded = load_composed_manifest(root)
    assert isinstance(loaded, Exception)
    assert "duplicate graph node" in str(loaded)

    _write(
        tmp_path / "rel-a.yml",
        "graph:\n  relationships:\n    - id: edge\n      from:\n        project: alpha\n"
        "      to:\n        project: beta\n      type: depends_on\n",
    )
    _write(
        tmp_path / "rel-b.yml",
        "graph:\n  relationships:\n    - id: other\n      from:\n        project: alpha\n"
        "      to:\n        project: beta\n      type: depends_on\n",
    )
    root = _root(tmp_path, "  - rel-a.yml\n  - rel-b.yml\n")
    loaded = load_composed_manifest(root)
    assert isinstance(loaded, Exception)
    assert "duplicate graph relationship" in str(loaded)


def test_resolved_files_lists_root_and_fragments(tmp_path: Path) -> None:
    _write(tmp_path / "alpha.yml", "workspace:\n  projects:\n    - name: alpha\n      repos: []\n")
    root = _root(tmp_path, "  - alpha.yml\n")
    manager = MetagitConfigManager(root)
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    names = [path.name for path in manager.resolved_files]
    assert names[0] == ".metagit.yml"
    assert "alpha.yml" in names


def test_digest_mtime_uses_fragment(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    from metagit.core.context.session_digest_service import SessionDigestService

    _write(tmp_path / "alpha.yml", "workspace:\n  projects:\n    - name: alpha\n      repos: []\n")
    root = _root(tmp_path, "  - alpha.yml\n")
    os.utime(root, (1_000, 1_000))
    os.utime(tmp_path / "alpha.yml", (5_000, 5_000))
    config = MetagitConfig(name="umbrella", kind="umbrella", workspace={"projects": []})
    digest = SessionDigestService.build(
        config,
        str(root),
        str(tmp_path),
        since=datetime.fromtimestamp(2_000, tz=timezone.utc).isoformat(),
    )
    assert digest.manifest_changed is True
