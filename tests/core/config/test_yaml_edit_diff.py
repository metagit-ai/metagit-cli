#!/usr/bin/env python
"""Tests for payload diffs that drive YAML splices."""

from __future__ import annotations

from metagit.core.config.include_loader import node_key, relationship_key
from metagit.core.config.yaml_edit_diff import diff_payloads
from metagit.core.config.yaml_edit_types import ItemRef, YamlEdit
from metagit.core.config.yaml_roundtrip import _list_item_identity


def test_equal_payloads_return_no_edits() -> None:
    payload = {
        "name": "demo",
        "workspace": {"projects": [{"name": "alpha", "description": "stay"}]},
    }
    assert diff_payloads(payload, payload) == []


def test_changing_one_string_returns_one_replace() -> None:
    before = {"name": "demo", "description": "old"}
    after = {"name": "demo", "description": "new"}
    assert diff_payloads(before, after) == [
        YamlEdit(op="replace", path=("description",), value="new"),
    ]


def test_adding_a_key_returns_insert_key() -> None:
    before = {"name": "demo"}
    after = {"name": "demo", "metadata": {"kind": "note"}}
    assert diff_payloads(before, after) == [
        YamlEdit(op="insert_key", path=("metadata",), value={"kind": "note"}),
    ]


def test_removing_a_key_returns_delete_key() -> None:
    before = {"name": "demo", "metadata": {"kind": "note"}}
    after = {"name": "demo"}
    assert diff_payloads(before, after) == [
        YamlEdit(op="delete_key", path=("metadata",)),
    ]


def test_key_order_changes_return_no_edits() -> None:
    before = {"b": 1, "a": {"z": True, "y": None}}
    after = {"a": {"y": None, "z": True}, "b": 1}
    assert diff_payloads(before, after) == []


def test_projects_and_repos_match_by_name() -> None:
    before = {
        "workspace": {
            "projects": [
                {"name": "beta", "description": "untouched"},
                {
                    "name": "alpha",
                    "repos": [
                        {"name": "web", "description": "same"},
                        {"name": "api", "description": "old"},
                    ],
                },
            ]
        }
    }
    after = {
        "workspace": {
            "projects": [
                {
                    "name": "alpha",
                    "repos": [
                        {"name": "api", "description": "new"},
                        {"name": "web", "description": "same"},
                    ],
                },
                {"name": "beta", "description": "untouched"},
            ]
        }
    }
    assert diff_payloads(before, after) == [
        YamlEdit(
            op="replace",
            path=(
                "workspace",
                "projects",
                ItemRef(kind="name", value="alpha"),
                "repos",
                ItemRef(kind="name", value="api"),
                "description",
            ),
            value="new",
        )
    ]


def test_appending_a_project_returns_insert_item() -> None:
    sibling = {"name": "alpha", "description": "stay"}
    added = {"name": "gamma", "description": "new"}
    assert diff_payloads({"projects": [sibling]}, {"projects": [sibling, added]}) == [
        YamlEdit(
            op="insert_item",
            path=("projects", ItemRef(kind="name", value="gamma")),
            value=added,
        )
    ]


def test_deleting_a_project_returns_delete_item() -> None:
    sibling = {"name": "alpha", "description": "stay"}
    removed = {"name": "beta", "description": "gone"}
    assert diff_payloads({"projects": [sibling, removed]}, {"projects": [sibling]}) == [
        YamlEdit(
            op="delete_item",
            path=("projects", ItemRef(kind="name", value="beta")),
            value=removed,
        )
    ]


def test_graph_nodes_match_through_node_key() -> None:
    lib = {"identity": "github://org/lib", "classification": {"role": "lib"}}
    app = {"name": "app", "classification": {"role": "app"}}
    changed = {"identity": "github://org/lib", "classification": {"role": "service"}}
    before = {"graph": {"nodes": [lib, app]}}
    after = {"graph": {"nodes": [app, changed]}}
    assert diff_payloads(before, after) == [
        YamlEdit(
            op="replace",
            path=(
                "graph",
                "nodes",
                ItemRef(kind="node", value=node_key(lib)),
                "classification",
                "role",
            ),
            value="service",
        )
    ]


def test_relationships_match_through_relationship_key() -> None:
    by_id = {"id": "e1", "from": "api", "to": "web", "description": "keep"}
    by_tuple = {"from": "web", "to": "db", "type": "owns", "description": "old"}
    changed = {"from": "web", "to": "db", "type": "owns", "description": "new"}
    before = {"graph": {"relationships": [by_id, by_tuple]}}
    after = {"graph": {"relationships": [changed, by_id]}}
    assert diff_payloads(before, after) == [
        YamlEdit(
            op="replace",
            path=(
                "graph",
                "relationships",
                ItemRef(kind="relationship", value=relationship_key(by_tuple)),
                "description",
            ),
            value="new",
        )
    ]


def test_documentation_matches_by_name_then_index() -> None:
    before = {
        "documentation": [
            {"name": "guide", "title": "Old"},
            {"path": "README.md", "description": "old"},
        ]
    }
    after = {
        "documentation": [
            {"name": "guide", "title": "New"},
            {"path": "README.md", "description": "new"},
        ]
    }
    assert diff_payloads(before, after) == [
        YamlEdit(
            op="replace",
            path=("documentation", ItemRef(kind="name", value="guide"), "title"),
            value="New",
        ),
        YamlEdit(
            op="replace",
            path=("documentation", ItemRef(kind="index", value="1"), "description"),
            value="new",
        ),
    ]


def test_other_lists_use_list_item_identity() -> None:
    kept = "https://example.com/b"
    removed = "https://example.com/a"
    added = "https://example.com/c"
    removed_id = _list_item_identity(removed)
    added_id = _list_item_identity(added)
    assert removed_id is not None
    assert added_id is not None
    result = diff_payloads({"refs": [removed, kept]}, {"refs": [kept, added]})
    assert result == [
        YamlEdit(
            op="delete_item",
            path=("refs", ItemRef(kind="identity", value=removed_id)),
            value=removed,
        ),
        YamlEdit(
            op="insert_item",
            path=("refs", ItemRef(kind="identity", value=added_id)),
            value=added,
        ),
    ]


def test_list_without_identity_uses_index() -> None:
    before = {"widgets": [{"color": "red"}, {"color": "blue"}]}
    after = {"widgets": [{"color": "red"}, {"color": "green"}]}
    assert diff_payloads(before, after) == [
        YamlEdit(
            op="replace",
            path=("widgets", ItemRef(kind="index", value="1"), "color"),
            value="green",
        )
    ]


def test_duplicate_names_return_exception() -> None:
    duplicated = {
        "projects": [
            {"name": "api", "description": "one"},
            {"name": "api", "description": "two"},
        ]
    }
    unique = {"projects": [{"name": "api", "description": "one"}]}
    assert isinstance(diff_payloads(duplicated, unique), ValueError)
    assert isinstance(diff_payloads(unique, duplicated), ValueError)
    assert isinstance(diff_payloads(duplicated, duplicated), ValueError)


def test_equal_string_repos_allow_list_returns_no_edits() -> None:
    payload = {
        "workspace": {
            "projects": [
                {
                    "name": "alpha",
                    "derived": {"sources": [{"project": "core", "repos": ["api", "web"]}]},
                    "repos": [{"name": "api", "description": "stay"}],
                }
            ]
        }
    }
    assert diff_payloads(payload, payload) == []


def test_changing_one_string_repo_edits_only_that_item() -> None:
    before = {
        "workspace": {
            "projects": [
                {
                    "name": "alpha",
                    "derived": {"sources": [{"project": "core", "repos": ["api", "web"]}]},
                    "repos": [{"name": "api", "description": "stay"}],
                }
            ]
        }
    }
    after = {
        "workspace": {
            "projects": [
                {
                    "name": "alpha",
                    "derived": {"sources": [{"project": "core", "repos": ["api", "worker"]}]},
                    "repos": [{"name": "api", "description": "stay"}],
                }
            ]
        }
    }
    removed_id = _list_item_identity("web")
    added_id = _list_item_identity("worker")
    assert removed_id is not None
    assert added_id is not None
    repos_path = (
        "workspace",
        "projects",
        ItemRef(kind="name", value="alpha"),
        "derived",
        "sources",
        ItemRef(kind="index", value="0"),
        "repos",
    )
    assert diff_payloads(before, after) == [
        YamlEdit(
            op="delete_item",
            path=repos_path + (ItemRef(kind="identity", value=removed_id),),
            value="web",
        ),
        YamlEdit(
            op="insert_item",
            path=repos_path + (ItemRef(kind="identity", value=added_id),),
            value="worker",
        ),
    ]


def test_string_project_items_fall_through_to_identity() -> None:
    removed_id = _list_item_identity("web")
    added_id = _list_item_identity("worker")
    assert removed_id is not None
    assert added_id is not None
    assert diff_payloads({"projects": ["api", "web"]}, {"projects": ["api", "web"]}) == []
    assert diff_payloads({"projects": ["api", "web"]}, {"projects": ["api", "worker"]}) == [
        YamlEdit(
            op="delete_item",
            path=("projects", ItemRef(kind="identity", value=removed_id)),
            value="web",
        ),
        YamlEdit(
            op="insert_item",
            path=("projects", ItemRef(kind="identity", value=added_id)),
            value="worker",
        ),
    ]


def test_string_that_becomes_a_mapping_is_one_replace() -> None:
    before = {"metadata": "plain"}
    after = {"metadata": {"kind": "note"}}
    assert diff_payloads(before, after) == [
        YamlEdit(op="replace", path=("metadata",), value={"kind": "note"}),
    ]
