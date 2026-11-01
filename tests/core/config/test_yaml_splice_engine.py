#!/usr/bin/env python
"""Tests for the value-preserving YAML splice engine."""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from metagit.core.config.yaml_edit_types import ItemRef, YamlEdit
from metagit.core.config.yaml_splice import (
    apply_yaml_edits,
    list_item_text,
    render_scalar,
)

STYLE_DOC = """\
# top comment
name: demo
# comment above untouched
untouched: keep  # same-line comment
folded: >-
  folded text
  continues here
folded_clip: >
  clip folded
  second line
literal: |
  line one
  line two
strip: |-
  strip one
  strip two
plain_multi: first plain line
  second plain line
single_multi: 'single quoted
  continues here'
double_multi: "double quoted
  continues here"
target: old  # target comment
tail: end
"""

SIBLING_SNIPPETS = [
    "# top comment\n",
    "# comment above untouched\nuntouched: keep  # same-line comment\n",
    "folded: >-\n  folded text\n  continues here\n",
    "folded_clip: >\n  clip folded\n  second line\n",
    "literal: |\n  line one\n  line two\n",
    "strip: |-\n  strip one\n  strip two\n",
    "plain_multi: first plain line\n  second plain line\n",
    "single_multi: 'single quoted\n  continues here'\n",
    'double_multi: "double quoted\n  continues here"\n',
    "tail: end\n",
]

REPOS_DOC = """\
workspace:
  projects:
    - name: p1
      repos:
        - name: a
          description: first
        # comment for b
        - name: b
          description: second  # trailing
        - name: c
          description: third
"""


def edit(
    op: str, *path: Any, value: Any = None, raw_text: str | None = None
) -> YamlEdit:
    return YamlEdit(op=op, path=tuple(path), value=value, raw_text=raw_text)


def apply(
    text: str, *edits: YamlEdit, aliases: dict[str, tuple[str, ...]] | None = None
) -> str:
    result = apply_yaml_edits(text, list(edits), aliases=aliases)
    assert not isinstance(result, Exception), result
    return result


def repo(name: str) -> ItemRef:
    return ItemRef(kind="name", value=name)


REPOS_PATH = ("workspace", "projects", repo("p1"), "repos")


# -- replace ------------------------------------------------------------------


def test_replace_scalar_keeps_every_sibling_style_and_comment() -> None:
    result = apply(STYLE_DOC, edit("replace", "target", value="new"))
    for snippet in SIBLING_SNIPPETS:
        assert snippet in result
    assert "target: new  # target comment\n" in result
    before, after = yaml.safe_load(STYLE_DOC), yaml.safe_load(result)
    assert after["target"] == "new"
    assert {k: v for k, v in after.items() if k != "target"} == {
        k: v for k, v in before.items() if k != "target"
    }


def test_replace_scalar_does_not_touch_other_lines_byte_for_byte() -> None:
    result = apply(STYLE_DOC, edit("replace", "target", value="new"))
    assert result.replace("target: new", "target: old") == STYLE_DOC


@pytest.mark.parametrize(
    "key", ["folded", "literal", "strip", "plain_multi", "single_multi", "double_multi"]
)
def test_replace_multiline_scalar_with_short_string(key: str) -> None:
    result = apply(STYLE_DOC, edit("replace", key, value="short"))
    assert yaml.safe_load(result)[key] == "short"
    assert yaml.safe_load(result)["tail"] == "end"
    assert "tail: end\n" in result
    assert "target: old  # target comment\n" in result


@pytest.mark.parametrize(
    "value",
    ["line1\nline2\n", "line1\nline2", "a\n\nb\n\n", "  lead\nnext", "x\ny\n\n"],
)
def test_replace_with_newline_string_roundtrips_as_block(value: str) -> None:
    result = apply(STYLE_DOC, edit("replace", "target", value=value))
    assert yaml.safe_load(result)["target"] == value
    assert "target: |" in result
    assert "# target comment" in result
    assert "tail: end\n" in result


def test_replace_block_scalar_with_block_scalar() -> None:
    result = apply(STYLE_DOC, edit("replace", "literal", value="x\ny"))
    assert yaml.safe_load(result)["literal"] == "x\ny"
    assert "literal: |-\n  x\n  y\nstrip: |-\n" in result


def test_replace_block_scalar_in_nested_mapping_indents_content() -> None:
    text = "a:\n  b:\n    c: old\n  d: 1\n"
    result = apply(text, edit("replace", "a", "b", "c", value="l1\nl2"))
    assert result == "a:\n  b:\n    c: |-\n      l1\n      l2\n  d: 1\n"


def test_replace_long_single_line_stays_one_line() -> None:
    long_value = "word " * 60 + "end"
    result = apply(STYLE_DOC, edit("replace", "target", value=long_value))
    assert yaml.safe_load(result)["target"] == long_value
    assert f"target: {long_value}  # target comment\n" in result


@pytest.mark.parametrize(
    "value",
    [
        "plain text",
        "a: b",
        "yes",
        "123",
        "null",
        "",
        " lead",
        "trail ",
        "- dash",
        "has # hash",
        'q"uote',
        "it's",
        "tab\tin",
        "é text",
    ],
)
def test_replace_scalar_values_parse_back(value: str) -> None:
    result = apply("k: old\n", edit("replace", "k", value=value))
    assert yaml.safe_load(result) == {"k": value}


@pytest.mark.parametrize(
    "value",
    [
        "del\x7f \U0001f600 emoji",
        "c1\x85 \U0001f600 emoji",
        "sep\u2028 \U0001f600 emoji",
        "sep\u2029 \U0001f600 emoji",
        "\x7f\U0001f600",
        "\U0001f600 \x9f \u00e9 \u4e2d",
    ],
)
def test_replace_non_printable_with_astral_characters_parses_back(value: str) -> None:
    rendered = render_scalar(value)
    assert yaml.safe_load(f"k: {rendered}\n") == {"k": value}
    assert "\\ud83d" not in rendered.lower()
    assert "\U0001f600" in rendered or "\U0001f600" not in value
    result = apply("k: old\n", edit("replace", "k", value=value))
    assert yaml.safe_load(result) == {"k": value}


@pytest.mark.parametrize("value", [True, False, None, 7, 1.5, 1e-07, float("inf")])
def test_replace_non_string_scalars(value: Any) -> None:
    result = apply("k: old\n", edit("replace", "k", value=value))
    assert yaml.safe_load(result) == {"k": value}


def test_replace_empty_scalar_adds_space_after_colon() -> None:
    result = apply("a:\nb: 1\n", edit("replace", "a", value="x"))
    assert result == "a: x\nb: 1\n"


def test_replace_scalar_with_mapping_and_back() -> None:
    result = apply(
        "a: old  # note\nb: 1\n", edit("replace", "a", value={"x": 1, "y": ["p", "q"]})
    )
    assert yaml.safe_load(result) == {"a": {"x": 1, "y": ["p", "q"]}, "b": 1}
    assert "# note" in result
    back = apply(result, edit("replace", "a", value="plain"))
    assert yaml.safe_load(back) == {"a": "plain", "b": 1}


def test_replace_list_item_scalar() -> None:
    result = apply(
        "items:\n  - one\n  - two\n  - three\n",
        edit("replace", "items", ItemRef("index", "1"), value="2nd"),
    )
    assert result == "items:\n  - one\n  - 2nd\n  - three\n"


def test_replace_in_list_item_by_name() -> None:
    result = apply(
        REPOS_DOC,
        edit("replace", *REPOS_PATH, repo("b"), "description", value="changed"),
    )
    assert "description: changed  # trailing\n" in result
    assert "# comment for b\n" in result
    assert (
        yaml.safe_load(result)["workspace"]["projects"][0]["repos"][1]["description"]
        == "changed"
    )


def test_replace_flow_collection_value_is_allowed() -> None:
    result = apply("a: [1, 2]  # c\nb: 1\n", edit("replace", "a", value="s"))
    assert result == "a: s  # c\nb: 1\n"


# -- insert_key / delete_key -----------------------------------------------------


def test_insert_key_adds_one_line_after_last_key() -> None:
    result = apply(STYLE_DOC, edit("insert_key", "added", value="v"))
    assert result == STYLE_DOC + "added: v\n"


def test_insert_key_in_nested_mapping_uses_child_indent() -> None:
    text = "a:\n  b: 1\n  c: 2\nz: 3\n"
    result = apply(text, edit("insert_key", "a", "d", value="x"))
    assert result == "a:\n  b: 1\n  c: 2\n  d: x\nz: 3\n"


def test_insert_key_into_list_item_mapping() -> None:
    result = apply(
        REPOS_DOC, edit("insert_key", *REPOS_PATH, repo("a"), "url", value="u")
    )
    assert "- name: a\n          description: first\n          url: u\n" in result
    assert yaml.safe_load(result)["workspace"]["projects"][0]["repos"][0]["url"] == "u"


def test_insert_key_after_block_scalar_last_value() -> None:
    result = apply("a: 1\nb: |\n  text\n", edit("insert_key", "c", value=2))
    assert result == "a: 1\nb: |\n  text\nc: 2\n"


def test_insert_key_without_trailing_newline() -> None:
    result = apply("a: 1", edit("insert_key", "b", value=2))
    assert yaml.safe_load(result) == {"a": 1, "b": 2}


def test_insert_key_mapping_value_renders_block() -> None:
    result = apply(
        "a: 1\n", edit("insert_key", "m", value={"x": [1, 2], "y": {"z": "s"}})
    )
    assert result == "a: 1\nm:\n  x:\n    - 1\n    - 2\n  y:\n    z: s\n"


def test_insert_key_existing_returns_exception() -> None:
    assert isinstance(
        apply_yaml_edits("a: 1\n", [edit("insert_key", "a", value=2)]), Exception
    )


def test_insert_key_into_empty_flow_mapping() -> None:
    result = apply("a: {}\nb: 1\n", edit("insert_key", "a", "k", value="v"))
    assert yaml.safe_load(result) == {"a": {"k": "v"}, "b": 1}


def test_delete_key_removes_line_and_keeps_previous_comment() -> None:
    result = apply(STYLE_DOC, edit("delete_key", "untouched"))
    assert "# comment above untouched\n" in result
    assert "untouched:" not in result
    assert "same-line comment" not in result
    assert "name: demo\n# comment above untouched\nfolded: >-\n" in result


def test_delete_key_with_multiline_value() -> None:
    result = apply(STYLE_DOC, edit("delete_key", "literal"))
    assert "literal" not in result and "line one" not in result
    assert "strip: |-\n  strip one\n" in result
    assert "folded_clip: >\n  clip folded\n  second line\nstrip: |-" in result


def test_delete_key_first_key_of_list_item_keeps_dash() -> None:
    result = apply(REPOS_DOC, edit("delete_key", *REPOS_PATH, repo("a"), "name"))
    assert "        - description: first\n" in result
    assert yaml.safe_load(result)["workspace"]["projects"][0]["repos"][0] == {
        "description": "first"
    }


def test_delete_key_only_key_leaves_empty_mapping() -> None:
    result = apply("a:\n  b: 1\nc: 2\n", edit("delete_key", "a", "b"))
    assert yaml.safe_load(result) == {"a": {}, "c": 2}


def test_delete_all_keys_of_root_leaves_empty_mapping() -> None:
    result = apply("# keep\na: 1\n", edit("delete_key", "a"))
    assert yaml.safe_load(result) == {}
    assert "# keep" in result


def test_delete_missing_key_returns_exception() -> None:
    assert isinstance(apply_yaml_edits("a: 1\n", [edit("delete_key", "zz")]), Exception)


# -- delete_item / insert_item -------------------------------------------------------


def test_delete_item_keeps_between_comment_with_following_item() -> None:
    result = apply(REPOS_DOC, edit("delete_item", *REPOS_PATH, repo("a")))
    assert "- name: a" not in result and "first" not in result
    assert "        # comment for b\n        - name: b\n" in result
    names = [
        r["name"] for r in yaml.safe_load(result)["workspace"]["projects"][0]["repos"]
    ]
    assert names == ["b", "c"]


def test_delete_middle_item_leaves_neighbors_byte_identical() -> None:
    result = apply(REPOS_DOC, edit("delete_item", *REPOS_PATH, repo("b")))
    assert result == (
        "workspace:\n  projects:\n    - name: p1\n      repos:\n"
        "        - name: a\n          description: first\n"
        "        # comment for b\n"
        "        - name: c\n          description: third\n"
    )


def test_delete_last_item_in_list() -> None:
    result = apply(REPOS_DOC, edit("delete_item", *REPOS_PATH, repo("c")))
    assert result.endswith("          description: second  # trailing\n")
    assert [
        r["name"] for r in yaml.safe_load(result)["workspace"]["projects"][0]["repos"]
    ] == ["a", "b"]


def test_delete_last_remaining_item_leaves_empty_list() -> None:
    text = "repos:\n  - name: only\n    description: d\nother: 1\n"
    result = apply(text, edit("delete_item", "repos", repo("only")))
    assert result == "repos: []\nother: 1\n"
    assert yaml.safe_load(result)["repos"] == []


def test_delete_all_items_via_several_edits() -> None:
    result = apply(
        REPOS_DOC,
        edit("delete_item", *REPOS_PATH, repo("a")),
        edit("delete_item", *REPOS_PATH, repo("b")),
        edit("delete_item", *REPOS_PATH, repo("c")),
    )
    assert yaml.safe_load(result)["workspace"]["projects"][0]["repos"] == []
    assert "repos: []\n" in result


def test_delete_item_keeps_deeper_trailing_comment_with_item() -> None:
    text = "l:\n  - a: 1\n    # deep note\n  # shallow note\n  - a: 2\n"
    result = apply(text, edit("delete_item", "l", ItemRef("index", "0")))
    assert result == "l:\n  # shallow note\n  - a: 2\n"


def test_insert_item_into_empty_flow_list() -> None:
    result = apply(
        "repos: []\nother: 1\n",
        edit("insert_item", "repos", value={"name": "n", "description": "d"}),
    )
    assert result == "repos:\n  - name: n\n    description: d\nother: 1\n"
    assert yaml.safe_load(result)["repos"] == [{"name": "n", "description": "d"}]


def test_insert_item_appends_after_last_item_without_restyling() -> None:
    result = apply(
        REPOS_DOC,
        edit(
            "insert_item",
            *REPOS_PATH,
            repo("d"),
            value={"name": "d", "description": "line1\nline2"},
        ),
    )
    assert result.startswith(REPOS_DOC)
    assert result.endswith(
        "        - name: d\n          description: |-\n            line1\n            line2\n"
    )
    repos = yaml.safe_load(result)["workspace"]["projects"][0]["repos"]
    assert repos[-1] == {"name": "d", "description": "line1\nline2"}


def test_insert_item_path_may_name_the_list_directly() -> None:
    result = apply("items:\n  - one\n", edit("insert_item", "items", value="two"))
    assert result == "items:\n  - one\n  - two\n"


def test_insert_item_raw_text_is_reindented_without_restyling_siblings() -> None:
    raw = "  - name: moved\n    description: |\n      keep\n      this\n    extra:\n      - x\n"
    text = (
        "projects:\n      - name: sibling\n        description: >-\n          folded\n"
    )
    result = apply(text, edit("insert_item", "projects", repo("moved"), raw_text=raw))
    assert result.startswith(text)
    assert result.endswith(
        "      - name: moved\n        description: |\n          keep\n          this\n        extra:\n          - x\n"
    )
    parsed = yaml.safe_load(result)["projects"]
    assert parsed[1] == {"name": "moved", "description": "keep\nthis\n", "extra": ["x"]}


@pytest.mark.parametrize("blank", ["      ", "          ", "  ", ""])
def test_insert_item_raw_text_keeps_whitespace_only_block_lines(blank: str) -> None:
    raw = f"  - name: moved\n    description: |\n      one\n{blank}\n      two\n"
    text = "projects:\n      - name: sibling\n"
    original = yaml.safe_load(raw)[0]["description"]
    result = apply(text, edit("insert_item", "projects", repo("moved"), raw_text=raw))
    parsed = yaml.safe_load(result)["projects"][1]
    assert parsed["description"] == original


def test_insert_item_raw_text_shifts_whitespace_only_line_with_the_block() -> None:
    raw = "  - name: moved\n    description: |\n      one\n        \n      two\n"
    result = apply("projects:\n      - name: sibling\n", edit("insert_item", "projects", repo("moved"), raw_text=raw))
    assert result.endswith("          one\n            \n          two\n")
    assert yaml.safe_load(result)["projects"][1]["description"] == "one\n  \ntwo\n"


def test_insert_item_raw_text_keeps_truly_empty_line_empty() -> None:
    raw = "  - name: moved\n    description: |\n      one\n\n      two\n"
    result = apply("projects:\n      - name: sibling\n", edit("insert_item", "projects", repo("moved"), raw_text=raw))
    assert result.endswith("          one\n\n          two\n")
    assert yaml.safe_load(result)["projects"][1]["description"] == "one\n\ntwo\n"


def test_insert_item_raw_text_into_empty_list() -> None:
    raw = "- name: moved\n  description: text\n"
    result = apply(
        "repos: []\n", edit("insert_item", "repos", repo("moved"), raw_text=raw)
    )
    assert result == "repos:\n  - name: moved\n    description: text\n"


def test_replace_sole_item_with_delete_and_insert() -> None:
    text = "repos:\n  - name: old\n    description: x\nnext: 1\n"
    result = apply(
        text,
        edit("delete_item", "repos", repo("old")),
        edit("insert_item", "repos", repo("new"), value={"name": "new"}),
    )
    assert yaml.safe_load(result) == {"repos": [{"name": "new"}], "next": 1}


def test_delete_and_insert_in_same_list_keeps_remaining_items() -> None:
    result = apply(
        REPOS_DOC,
        edit("delete_item", *REPOS_PATH, repo("c")),
        edit("insert_item", *REPOS_PATH, repo("z"), value={"name": "z"}),
    )
    names = [
        r["name"] for r in yaml.safe_load(result)["workspace"]["projects"][0]["repos"]
    ]
    assert names == ["a", "b", "z"]


def test_item_ref_kinds_resolve() -> None:
    text = (
        "graph:\n  nodes:\n    - identity: ident-1\n      name: n1\n    - name: n2\n"
        "  relationships:\n    - id: rel-1\n      type: depends_on\n"
        "other:\n  - https://example.com/x\n  - plain/path\n"
    )
    result = apply(
        text,
        edit(
            "replace",
            "graph",
            "nodes",
            ItemRef("node", "ident-1"),
            "name",
            value="renamed",
        ),
        edit("replace", "graph", "nodes", ItemRef("node", "n2"), "name", value="n2b"),
        edit(
            "replace",
            "graph",
            "relationships",
            ItemRef("relationship", "rel-1"),
            "type",
            value="uses",
        ),
        edit(
            "replace",
            "other",
            ItemRef("identity", "url:https://example.com/x"),
            value="https://example.com/y",
        ),
        edit("replace", "other", ItemRef("index", "1"), value="other/path"),
    )
    data = yaml.safe_load(result)
    assert data["graph"]["nodes"][0]["name"] == "renamed"
    assert data["graph"]["nodes"][1]["name"] == "n2b"
    assert data["graph"]["relationships"][0]["type"] == "uses"
    assert data["other"] == ["https://example.com/y", "other/path"]


def test_item_ref_with_no_match_returns_exception() -> None:
    result = apply_yaml_edits(
        REPOS_DOC, [edit("delete_item", *REPOS_PATH, repo("missing"))]
    )
    assert isinstance(result, Exception)


def test_item_ref_with_duplicate_match_returns_exception() -> None:
    text = "repos:\n  - name: a\n  - name: a\n"
    assert isinstance(
        apply_yaml_edits(text, [edit("delete_item", "repos", repo("a"))]), Exception
    )


# -- aborts and aliases ------------------------------------------------------------------


def test_flow_mapping_around_key_returns_exception() -> None:
    text = "outer: {a: 1, b: 2}\nz: 1\n"
    result = apply_yaml_edits(text, [edit("replace", "outer", "a", value=5)])
    assert isinstance(result, Exception)
    assert not isinstance(result, str)


def test_flow_list_edit_returns_exception() -> None:
    assert isinstance(
        apply_yaml_edits("l: [a, b]\n", [edit("insert_item", "l", value="c")]),
        Exception,
    )
    assert isinstance(
        apply_yaml_edits("m: {a: 1}\n", [edit("insert_key", "m", "b", value=2)]),
        Exception,
    )
    assert isinstance(
        apply_yaml_edits("m: {a: 1}\n", [edit("delete_key", "m", "a")]), Exception
    )


def test_anchor_and_alias_nodes_return_exception() -> None:
    text = "base: &b\n  x: 1\nuse: *b\nname: &n old\n"
    assert isinstance(
        apply_yaml_edits(text, [edit("replace", "name", value="new")]), Exception
    )
    assert isinstance(
        apply_yaml_edits(text, [edit("replace", "use", value="new")]), Exception
    )
    assert isinstance(
        apply_yaml_edits(text, [edit("replace", "base", "x", value=2)]), Exception
    )


def test_alias_value_as_last_key_does_not_confuse_insert() -> None:
    text = "base: &b\n  x: 1\nuse: *b\n"
    result = apply(text, edit("insert_key", "after", value=1))
    assert result == text + "after: 1\n"


def test_missing_path_for_replace_returns_exception() -> None:
    assert isinstance(
        apply_yaml_edits("a: 1\n", [edit("replace", "b", value=1)]), Exception
    )


def test_invalid_yaml_and_non_mapping_root_return_exception() -> None:
    assert isinstance(
        apply_yaml_edits("a: [unclosed\n", [edit("replace", "a", value=1)]), Exception
    )
    assert isinstance(
        apply_yaml_edits("- a\n- b\n", [edit("replace", "a", value=1)]), Exception
    )
    assert isinstance(apply_yaml_edits("", [edit("replace", "a", value=1)]), Exception)


def test_unknown_op_returns_exception() -> None:
    assert isinstance(apply_yaml_edits("a: 1\n", [edit("explode", "a")]), Exception)


def test_overlapping_edits_return_exception() -> None:
    text = "a:\n  b: 1\n"
    result = apply_yaml_edits(
        text, [edit("replace", "a", value="x"), edit("replace", "a", "b", value=2)]
    )
    assert isinstance(result, Exception)


def test_alias_key_is_updated_without_renaming_it() -> None:
    text = "relationships:\n  - from_endpoint: old\n    to: x\n"
    result = apply(
        text,
        edit("replace", "relationships", ItemRef("index", "0"), "from", value="new"),
        aliases={"from": ("from_endpoint",)},
    )
    assert result == "relationships:\n  - from_endpoint: new\n    to: x\n"


def test_alias_key_requires_alias_map() -> None:
    text = "r:\n  - from_endpoint: old\n"
    assert isinstance(
        apply_yaml_edits(
            text, [edit("replace", "r", ItemRef("index", "0"), "from", value="n")]
        ),
        Exception,
    )


# -- multiple edits ---------------------------------------------------------------------


def test_two_edits_apply_and_untouched_lines_stay_identical() -> None:
    result = apply(
        STYLE_DOC,
        edit("replace", "target", value="new"),
        edit("replace", "tail", value="fin"),
    )
    assert (
        result.replace("target: new", "target: old").replace("tail: fin", "tail: end")
        == STYLE_DOC
    )


def test_edits_in_any_order_produce_the_same_text() -> None:
    first = edit("replace", "target", value="new")
    second = edit("delete_key", "untouched")
    third = edit("insert_key", "added", value=1)
    assert apply(STYLE_DOC, first, second, third) == apply(
        STYLE_DOC, third, second, first
    )


def test_two_insert_keys_into_same_mapping_keep_order() -> None:
    result = apply(
        "a: 1\n", edit("insert_key", "b", value=2), edit("insert_key", "c", value=3)
    )
    assert result == "a: 1\nb: 2\nc: 3\n"


def test_delete_several_keys_including_first_of_item() -> None:
    text = "l:\n  - a: 1\n    b: 2\n    c: 3\n"
    result = apply(
        text,
        edit("delete_key", "l", ItemRef("index", "0"), "a"),
        edit("delete_key", "l", ItemRef("index", "0"), "b"),
    )
    assert result == "l:\n  - c: 3\n"


def test_no_edits_returns_same_text() -> None:
    assert apply(STYLE_DOC) == STYLE_DOC


# -- list_item_text -------------------------------------------------------------------


def test_list_item_text_returns_item_span() -> None:
    text = list_item_text(REPOS_DOC, (*REPOS_PATH, repo("b")))
    assert text == "        - name: b\n          description: second  # trailing\n"


def test_list_item_text_excludes_between_item_comment() -> None:
    text = list_item_text(REPOS_DOC, (*REPOS_PATH, repo("a")))
    assert text == "        - name: a\n          description: first\n"


def test_list_item_text_roundtrips_through_insert_item() -> None:
    item = list_item_text(REPOS_DOC, (*REPOS_PATH, repo("b")))
    assert isinstance(item, str)
    target = "repos:\n  - name: x\n"
    result = apply(target, edit("insert_item", "repos", repo("b"), raw_text=item))
    assert (
        result
        == "repos:\n  - name: x\n  - name: b\n    description: second  # trailing\n"
    )


def test_list_item_text_errors() -> None:
    assert isinstance(list_item_text(REPOS_DOC, (*REPOS_PATH, repo("zz"))), Exception)
    assert isinstance(list_item_text(REPOS_DOC, REPOS_PATH), Exception)
    assert isinstance(
        list_item_text("a: [1]\n", ("a", ItemRef("index", "0"))), Exception
    )


# -- render_scalar --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, "true"),
        (False, "false"),
        (None, "null"),
        (3, "3"),
        (2.5, "2.5"),
        ("plain", "plain"),
        ("", '""'),
        ("yes", '"yes"'),
        ("12", '"12"'),
        ("null", '"null"'),
        ("a: b", '"a: b"'),
        (" x", '" x"'),
        ("- x", '"- x"'),
        ("?x", '"?x"'),
        ("a#b", '"a#b"'),
    ],
)
def test_render_scalar_forms(value: Any, expected: str) -> None:
    assert render_scalar(value) == expected


def test_render_scalar_multiline_blocks() -> None:
    assert render_scalar("a\nb\n") == "|\na\nb\n"
    assert render_scalar("a\nb") == "|-\na\nb"


def test_render_scalar_does_not_wrap_long_lines() -> None:
    long_value = "word " * 40 + "end"
    assert render_scalar(long_value) == long_value
    assert "\n" not in render_scalar(long_value)


def test_render_scalar_control_characters_use_quotes() -> None:
    value = "a\nb\x07"
    assert yaml.safe_load("k: " + render_scalar(value)) == {"k": value}


# -- keep-chomp block scalars and exponent floats -------------------------------


@pytest.mark.parametrize("header", ["|+", ">+", "|2+", "|+  # note"])
@pytest.mark.parametrize("value", ["s", "s\nt", "s\nt\n", " lead\nt", "s\n\n"])
def test_replace_keep_chomp_block_scalar_keeps_next_key(
    header: str, value: str
) -> None:
    text = f"a: {header}\n  x\n\nb: 1\n"
    result = apply(text, edit("replace", "a", value=value))
    assert yaml.safe_load(result) == {"a": value, "b": 1}


def test_replace_keep_chomp_block_scalar_with_short_string_exact() -> None:
    result = apply("a: |+\n  x\n\nb: 1\n", edit("replace", "a", value="s"))
    assert result == "a: s\nb: 1\n"


def test_replace_keep_chomp_block_scalar_at_end_of_file() -> None:
    result = apply("b: 1\na: |+\n  x\n\n", edit("replace", "a", value="s"))
    assert yaml.safe_load(result) == {"a": "s", "b": 1}


def test_replace_keep_chomp_block_scalar_nested_mapping() -> None:
    text = "p:\n  a: |+\n    x\n\n  b: 1\nc: 2\n"
    result = apply(text, edit("replace", "p", "a", value="s\nt"))
    assert yaml.safe_load(result) == {"p": {"a": "s\nt", "b": 1}, "c": 2}


@pytest.mark.parametrize("value", ["s", "s\nt", "s\nt\n"])
def test_replace_keep_chomp_list_item_keeps_next_dash(value: str) -> None:
    text = "items:\n  - |+\n    x\n\n  - y\n"
    result = apply(text, edit("replace", "items", ItemRef("index", "0"), value=value))
    assert yaml.safe_load(result) == {"items": [value, "y"]}


@pytest.mark.parametrize(
    "value", [1.5e20, 1.5e-07, 2.5e-10, -1.5e20, 1e20, 1e-07, 1.25e300, 5e-324]
)
def test_render_scalar_exponent_floats_parse_back_as_floats(value: float) -> None:
    loaded = yaml.safe_load("k: " + render_scalar(value))["k"]
    assert isinstance(loaded, float)
    assert loaded == value


def test_replace_exponent_float_parses_back_as_float() -> None:
    result = apply("k: old\n", edit("replace", "k", value=1.5e-07))
    assert yaml.safe_load(result) == {"k": 1.5e-07}


@pytest.mark.parametrize("value", ["1.5e+20", "1e-07", "1.5", "2.5e-10", "1e+20"])
def test_render_scalar_strings_that_look_like_floats_stay_strings(
    value: str,
) -> None:
    assert yaml.safe_load("k: " + render_scalar(value)) == {"k": value}


@pytest.mark.parametrize("value", ["1.5e+20", "1.5", "2.5e-10"])
def test_render_scalar_float_looking_strings_are_quoted(value: str) -> None:
    assert render_scalar(value) == f'"{value}"'
