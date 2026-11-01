#!/usr/bin/env python
"""Apply value-preserving edits to the original text of a YAML document.

The splice locates nodes with PyYAML compose and scan marks (character offsets in
the original string) and rewrites only the spans that an edit touches. Every other
byte of the document, including scalar style and comments, is left alone.
"""

from __future__ import annotations

import bisect
import copy
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.reader import Reader
from yaml.tokens import AliasToken, BlockEntryToken

from metagit.core.config.include_loader import node_key, relationship_key
from metagit.core.config.yaml_edit_types import ItemRef, YamlEdit
from metagit.core.config.yaml_roundtrip import _list_item_identity

_PLAIN_FORBIDDEN = frozenset(":{}[],&*!|>'\"#%@`")
_NON_PRINTABLE = Reader.NON_PRINTABLE
_LINE_BREAKS = re.compile("[\r\x85\u2028\u2029]")
_UNSAFE_CHARS = re.compile(f"{_NON_PRINTABLE.pattern}|{_LINE_BREAKS.pattern}")
_BLOCK_HEADER = re.compile(r"[|>][-+0-9]*[ \t]*(#.*)?$")
_BLOCK_CHOMP_KEEP = re.compile(r"[|>][0-9]*\+|[|>]\+")
_EXP_FLOAT = re.compile(r"^(-?\d+)(e[-+]?\d+)$")


# ---------------------------------------------------------------------------
# Value-preserving emitter
# ---------------------------------------------------------------------------


def _is_plain_safe(value: str) -> bool:
    """Return True when ``value`` can be written as a plain one-line scalar."""
    if value == "" or value != value.strip() or value[0] in "-?":
        return False
    if any(char in _PLAIN_FORBIDDEN for char in value):
        return False
    if _NON_PRINTABLE.search(value) or _LINE_BREAKS.search(value):
        return False
    try:
        parsed = yaml.safe_load(value)
    except yaml.YAMLError:
        return False
    return isinstance(parsed, str) and parsed == value


def _escape_char(match: re.Match[str]) -> str:
    """Return the YAML double-quoted escape for one non-printable character."""
    code = ord(match.group(0))
    if code <= 0xFF:
        return f"\\x{code:02x}"
    if code <= 0xFFFF:
        return f"\\u{code:04x}"
    return f"\\U{code:08x}"


def _quote(value: str) -> str:
    """Return a double-quoted one-line scalar that parses back to ``value``."""
    quoted = json.dumps(value, ensure_ascii=False)
    return _UNSAFE_CHARS.sub(_escape_char, quoted)


def _inline_string(value: str) -> str:
    """Return ``value`` as a single-line plain or double-quoted scalar."""
    return value if _is_plain_safe(value) else _quote(value)


def _can_block(value: str) -> bool:
    """Return True when a string with newlines can be a literal block scalar."""
    return (
        "\n" in value
        and value.strip("\n") != ""
        and not _NON_PRINTABLE.search(value)
        and not _LINE_BREAKS.search(value)
    )


def _is_block_string(value: object) -> bool:
    return isinstance(value, str) and _can_block(value)


def _block_parts(value: str, pad: int) -> tuple[str, list[str]]:
    """Return the block header and content lines for a multi-line string.

    ``pad`` is the number of spaces put in front of each non-empty content line.
    The header carries an indentation indicator of 2 when the first content line
    starts with a space, so callers must indent content two columns past the owner.
    """
    parts = value.split("\n")
    ends_with_newline = value.endswith("\n")
    if ends_with_newline:
        parts.pop()
    first = next((line for line in parts if line != ""), "")
    indicator = "2" if first.startswith(" ") else ""
    chomp = "-" if not ends_with_newline else ("+" if value.endswith("\n\n") else "")
    indent = " " * pad
    lines = [f"{indent}{line}" if line != "" else "" for line in parts]
    return f"|{indicator}{chomp}", lines


def _render_float(value: float) -> str:
    if math.isnan(value):
        return ".nan"
    if math.isinf(value):
        return ".inf" if value > 0 else "-.inf"
    text = repr(value)
    return _EXP_FLOAT.sub(r"\1.0\2", text)


def render_scalar(value: object) -> str:
    """Render one scalar as YAML text without wrapping or restyling.

    A string with newlines becomes a ``|`` block (``|-`` when it has no trailing
    newline). The header line is followed by the content lines, which are copied
    unindented; the caller indents them two columns past the owning key or dash.
    A string that cannot be a block scalar (control characters) is double-quoted.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _render_float(value)
    if isinstance(value, str):
        if _can_block(value):
            header, lines = _block_parts(value, 0)
            body = "\n".join(lines) + ("\n" if value.endswith("\n") else "")
            return f"{header}\n{body}"
        return _inline_string(value)
    return json.dumps(value, ensure_ascii=False, default=str)


def _render_key(key: object) -> str:
    return _inline_string(key) if isinstance(key, str) else render_scalar(key)


def _is_container(value: object) -> bool:
    return isinstance(value, (dict, list, tuple)) and len(value) > 0


def _owner_lines(pad: int, label: str, value: object, is_item: bool) -> list[str]:
    """Render ``label`` (``key:`` or ``-``) and its value at column ``pad``."""
    indent = " " * pad
    if isinstance(value, dict) and value:
        child = _mapping_lines(value, pad + 2)
        if is_item:
            child[0] = f"{indent}- {child[0][pad + 2 :]}"
            return child
        return [f"{indent}{label}", *child]
    if isinstance(value, (list, tuple)) and value:
        return [f"{indent}{label}", *_list_lines(list(value), pad + 2)]
    if _is_block_string(value):
        header, lines = _block_parts(str(value), pad + 2)
        return [f"{indent}{label} {header}", *lines]
    return [f"{indent}{label} {render_scalar(value)}"]


def _mapping_lines(mapping: dict[Any, Any], pad: int) -> list[str]:
    lines: list[str] = []
    for key, value in mapping.items():
        lines.extend(_owner_lines(pad, f"{_render_key(key)}:", value, False))
    return lines


def _list_lines(items: list[Any], pad: int) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.extend(_owner_lines(pad, "-", item, True))
    return lines


def _reindent_item(raw_text: str, dash_col: int) -> list[str]:
    """Shift a block list item so its ``-`` sits at ``dash_col``."""
    lines = raw_text.rstrip("\n").split("\n")
    first = next((line for line in lines if line.strip() != ""), "")
    source_col = len(first) - len(first.lstrip(" "))
    shifted: list[str] = []
    for line in lines:
        lead = len(line) - len(line.lstrip(" "))
        rest = line[min(lead, source_col) :]
        # A whitespace-only line keeps the spaces beyond the removed indent: inside
        # a block scalar they are content. At or below it the line collapses to "".
        shifted.append(" " * dash_col + rest if rest else "")
    return shifted


# ---------------------------------------------------------------------------
# Document index
# ---------------------------------------------------------------------------


@dataclass
class _Target:
    """A resolved path: the node and where it hangs."""

    node: Node
    parent: Node | None = None
    key_node: ScalarNode | None = None
    index: int | None = None


@dataclass
class _Splice:
    start: int
    end: int
    text: str
    order: int


@dataclass
class _SeqGroup:
    target: _Target
    deletes: list[int] = field(default_factory=list)
    inserts: list[YamlEdit] = field(default_factory=list)


@dataclass
class _MapGroup:
    target: _Target
    deletes: list[int] = field(default_factory=list)
    inserts: list[tuple[str, Any]] = field(default_factory=list)


class _Doc:
    """Composed document plus the marks needed to splice it."""

    def __init__(
        self,
        text: str,
        root: MappingNode,
        dashes: list[int],
        alias_tokens: list[tuple[int, int]],
        aliases: dict[str, tuple[str, ...]],
    ) -> None:
        self.text = text
        self.root = root
        self.dashes = dashes
        self.aliases = aliases
        self.shared: set[int] = set()
        self.alias_spans: dict[tuple[int, int], tuple[int, int]] = {}
        self._py_cache: dict[int, Any] = {}
        self._loader = yaml.SafeLoader("")
        self._index(alias_tokens)

    @classmethod
    def build(cls, text: str, aliases: dict[str, tuple[str, ...]]) -> _Doc | Exception:
        try:
            root = yaml.compose(text, Loader=yaml.SafeLoader)
            tokens = list(yaml.scan(text, Loader=yaml.SafeLoader))
        except yaml.YAMLError as err:
            return err
        if not isinstance(root, MappingNode):
            return ValueError("document root is not a mapping")
        dashes = sorted(token.start_mark.index for token in tokens if isinstance(token, BlockEntryToken))
        alias_tokens = [
            (token.start_mark.index, token.end_mark.index) for token in tokens if isinstance(token, AliasToken)
        ]
        try:
            return cls(text, root, dashes, alias_tokens, aliases)
        except ValueError as err:
            return err

    # -- indexing ---------------------------------------------------------

    @staticmethod
    def _children(node: Node) -> list[tuple[int, Node]]:
        if isinstance(node, MappingNode):
            out: list[tuple[int, Node]] = []
            for position, (key, value) in enumerate(node.value):
                out.append((2 * position, key))
                out.append((2 * position + 1, value))
            return out
        if isinstance(node, SequenceNode):
            return list(enumerate(node.value))
        return []

    def _index(self, alias_tokens: list[tuple[int, int]]) -> None:
        seen: set[int] = set()
        pending = iter(alias_tokens)

        def visit(node: Node) -> None:
            seen.add(id(node))
            for slot, child in self._children(node):
                if id(child) not in seen:
                    visit(child)
                    continue
                span = next(pending, None)
                if span is None:
                    raise ValueError("alias occurrences do not match alias tokens")
                self.alias_spans[(id(node), slot)] = span
                self.shared.add(id(child))

        visit(self.root)

    # -- text helpers -----------------------------------------------------

    def line_start(self, index: int) -> int:
        return self.text.rfind("\n", 0, index) + 1

    def eol(self, index: int) -> int:
        found = self.text.find("\n", index)
        return len(self.text) if found == -1 else found

    def after_line(self, index: int) -> int:
        if index > 0 and self.text[index - 1] == "\n":
            return index
        found = self.text.find("\n", index)
        return len(self.text) if found == -1 else found + 1

    def trim_end(self, start: int, end: int) -> int:
        while end > start and self.text[end - 1] in " \t\r\n":
            end -= 1
        return end

    # -- node ends --------------------------------------------------------

    def child_end(self, parent: Node, slot: int, child: Node) -> int:
        span = self.alias_spans.get((id(parent), slot))
        return span[1] if span is not None else self.end_of(child)

    def end_of(self, node: Node) -> int:
        """Return the end of a node's content, excluding comments and blank lines."""
        if isinstance(node, ScalarNode):
            start, end = node.start_mark.index, node.end_mark.index
            if node.style not in ("|", ">"):
                return end
            header = self.text[start : self.eol(start)]
            if _BLOCK_CHOMP_KEEP.match(header):
                return end
            return self.trim_end(start, end)
        if node.flow_style or not node.value:
            return node.end_mark.index
        if isinstance(node, MappingNode):
            last = len(node.value) - 1
            return self.child_end(node, 2 * last + 1, node.value[last][1])
        last = len(node.value) - 1
        return self.child_end(node, last, node.value[last])

    def dash_index(self, seq: SequenceNode, position: int) -> int:
        span = self.alias_spans.get((id(seq), position))
        anchor = span[0] if span is not None else seq.value[position].start_mark.index
        found = bisect.bisect_left(self.dashes, anchor) - 1
        return self.dashes[found] if found >= 0 else -1

    def tail_end(self, index: int, dash_col: int) -> int:
        """Extend past deeper-indented comments that follow an item."""
        text = self.text
        last = index
        cursor = index
        while cursor < len(text):
            end = self.eol(cursor)
            line = text[cursor:end]
            stripped = line.strip()
            following = min(end + 1, len(text))
            if stripped == "":
                cursor = following
                continue
            if stripped.startswith("#") and len(line) - len(line.lstrip()) > dash_col:
                last = following
                cursor = following
                continue
            break
        return last

    def item_span(self, seq: SequenceNode, position: int) -> tuple[int, int] | Exception:
        dash = self.dash_index(seq, position)
        if dash < 0:
            return ValueError("list item has no block dash")
        start = self.line_start(dash)
        if self.text[start:dash].strip() != "":
            return ValueError("nested list item is not supported")
        content_end = self.child_end(seq, position, seq.value[position])
        end = self.tail_end(self.after_line(content_end), dash - start)
        return start, end

    # -- python values and identity --------------------------------------

    def python_value(self, node: Node) -> Any:
        cached = self._py_cache.get(id(node))
        if cached is not None:
            return cached
        try:
            value = self._loader.construct_object(copy.deepcopy(node), deep=True)
        except yaml.YAMLError:
            value = None
        self._py_cache[id(node)] = value
        return value

    def match_item(self, seq: SequenceNode, ref: ItemRef) -> int | Exception:
        matches: list[int] = []
        for position, item in enumerate(seq.value):
            if ref.kind == "index":
                hit = str(position) == ref.value
            else:
                hit = self._identity_matches(self.python_value(item), ref)
            if hit:
                matches.append(position)
        if len(matches) != 1:
            return ValueError(f"list item {ref.kind}={ref.value!r} matched {len(matches)} items")
        return matches[0]

    @staticmethod
    def _identity_matches(data: Any, ref: ItemRef) -> bool:
        try:
            if ref.kind == "identity":
                return _list_item_identity(data) == ref.value
            if not isinstance(data, dict):
                return False
            if ref.kind == "name":
                return data.get("name") is not None and str(data["name"]) == ref.value
            if ref.kind == "node":
                return node_key(data) == ref.value
            if ref.kind == "relationship":
                return relationship_key(data) == ref.value
        except (TypeError, ValueError):
            return False
        return False

    # -- path resolution --------------------------------------------------

    def guard(self, node: Node, label: str) -> Exception | None:
        if id(node) in self.shared:
            return ValueError(f"{label} is a YAML alias or anchor target")
        start, end = node.start_mark.index, node.end_mark.index
        if end > start and self.text[start] in "&!":
            return ValueError(f"{label} has an anchor or tag")
        return None

    def find_key(self, mapping: MappingNode, key: str) -> int | None | Exception:
        for name in (key, *self.aliases.get(key, ())):
            hits = [
                position
                for position, (key_node, _) in enumerate(mapping.value)
                if isinstance(key_node, ScalarNode) and key_node.value == name
            ]
            if len(hits) > 1:
                return ValueError(f"duplicate key {name!r}")
            if hits:
                return hits[0]
        return None

    def resolve(self, path: tuple[str | ItemRef, ...]) -> _Target | Exception:
        node: Node = self.root
        problem = self.guard(node, "document root")
        if problem is not None:
            return problem
        target = _Target(node)
        for segment in path:
            if node.flow_style:
                return ValueError(f"flow-style collection on path {path!r}")
            if isinstance(segment, str):
                if not isinstance(node, MappingNode):
                    return ValueError(f"{segment!r} is not inside a mapping")
                position = self.find_key(node, segment)
                if isinstance(position, Exception):
                    return position
                if position is None:
                    return KeyError(f"path {path!r} is missing key {segment!r}")
                key_node, child = node.value[position]
                target = _Target(child, node, key_node, position)  # type: ignore[arg-type]
            else:
                if not isinstance(node, SequenceNode):
                    return ValueError(f"{segment!r} is not inside a list")
                position = self.match_item(node, segment)
                if isinstance(position, Exception):
                    return position
                child = node.value[position]
                target = _Target(child, node, None, position)
            problem = self.guard(child, f"node at {path!r}")
            if problem is not None:
                return problem
            node = child
        return target

    def colon_after(self, key_node: ScalarNode) -> int | Exception:
        index = key_node.end_mark.index
        while index < len(self.text) and self.text[index] in " \t":
            index += 1
        if index >= len(self.text) or self.text[index] != ":":
            return ValueError("mapping key is not followed by a colon")
        return index


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


class _Planner:
    """Turn edits into non-overlapping splices of the original text."""

    def __init__(self, doc: _Doc) -> None:
        self.doc = doc
        self.splices: list[_Splice] = []
        self._seq_groups: dict[int, _SeqGroup] = {}
        self._map_groups: dict[int, _MapGroup] = {}

    def add(self, start: int, end: int, text: str) -> None:
        self.splices.append(_Splice(start, end, text, len(self.splices)))

    def plan(self, edits: list[YamlEdit]) -> Exception | None:
        for edit in edits:
            problem = self._dispatch(edit)
            if problem is not None:
                return problem
        for seq_group in self._seq_groups.values():
            problem = self._finish_seq(seq_group)
            if problem is not None:
                return problem
        for map_group in self._map_groups.values():
            problem = self._finish_map(map_group)
            if problem is not None:
                return problem
        return None

    # -- dispatch ---------------------------------------------------------

    def _dispatch(self, edit: YamlEdit) -> Exception | None:
        if edit.op == "replace":
            return self._replace(edit)
        if edit.op in ("insert_key", "delete_key"):
            return self._queue_key_edit(edit)
        if edit.op in ("insert_item", "delete_item"):
            return self._queue_item_edit(edit)
        return ValueError(f"unknown edit op {edit.op!r}")

    def _replace(self, edit: YamlEdit) -> Exception | None:
        target = self.doc.resolve(edit.path)
        if isinstance(target, Exception):
            return target
        return self._region(target, value=edit.value)

    def _queue_key_edit(self, edit: YamlEdit) -> Exception | None:
        if not edit.path or not isinstance(edit.path[-1], str):
            return ValueError(f"{edit.op} path must end with a key: {edit.path!r}")
        key = edit.path[-1]
        target = self.doc.resolve(edit.path[:-1])
        if isinstance(target, Exception):
            return target
        mapping = target.node
        if not isinstance(mapping, MappingNode):
            return ValueError(f"{edit.path[:-1]!r} is not a mapping")
        position = self.doc.find_key(mapping, key)
        if isinstance(position, Exception):
            return position
        group = self._map_groups.setdefault(id(mapping), _MapGroup(target))
        if edit.op == "insert_key":
            if position is not None:
                return ValueError(f"key {key!r} already exists at {edit.path!r}")
            group.inserts.append((key, edit.value))
            return None
        if position is None:
            return KeyError(f"path {edit.path!r} is missing key {key!r}")
        if mapping.flow_style:
            return ValueError(f"flow-style mapping around {edit.path!r}")
        group.deletes.append(position)
        return None

    def _queue_item_edit(self, edit: YamlEdit) -> Exception | None:
        path = edit.path
        has_ref = bool(path) and isinstance(path[-1], ItemRef)
        list_path = path[:-1] if has_ref else path
        target = self.doc.resolve(list_path)
        if isinstance(target, Exception):
            return target
        seq = target.node
        if not isinstance(seq, SequenceNode):
            return ValueError(f"{list_path!r} is not a list")
        group = self._seq_groups.setdefault(id(seq), _SeqGroup(target))
        if edit.op == "insert_item":
            group.inserts.append(edit)
            return None
        if not has_ref:
            return ValueError(f"delete_item path must end with an ItemRef: {path!r}")
        if seq.flow_style:
            return ValueError(f"flow-style list around {path!r}")
        position = self.doc.match_item(seq, path[-1])  # type: ignore[arg-type]
        if isinstance(position, Exception):
            return position
        group.deletes.append(position)
        return None

    # -- value regions ----------------------------------------------------

    def _region(
        self,
        target: _Target,
        *,
        value: Any = None,
        container_lines: Callable[[int], list[str]] | None = None,
    ) -> Exception | None:
        """Replace one node's value, keeping its key, indent and comments."""
        doc = self.doc
        node = target.node
        if target.parent is None:
            return ValueError("cannot replace the document root")
        is_item = target.key_node is None
        if is_item:
            if container_lines is not None:
                return ValueError("cannot rebuild a list item from raw lines")
            seq = target.parent
            assert isinstance(seq, SequenceNode) and target.index is not None
            dash = doc.dash_index(seq, target.index)
            if dash < 0:
                return ValueError("list item has no block dash")
            region_start = dash
            pad = dash - doc.line_start(dash)
            floor = region_start
        else:
            assert target.key_node is not None
            colon = doc.colon_after(target.key_node)
            if isinstance(colon, Exception):
                return colon
            region_start = colon + 1
            floor = region_start
            pad = target.key_node.start_mark.column

        end, inside, after, block_coll, existing_pad = self._old_info(node, floor, is_item)

        if container_lines is not None:
            child_pad = existing_pad if existing_pad > pad else pad + 2
            lines = ["", *container_lines(child_pad)]
        elif is_item:
            lines = _owner_lines(pad, "-", value, True)
            lines[0] = lines[0][pad:]
        elif _is_container(value):
            child_pad = existing_pad if existing_pad > pad else pad + 2
            body = _mapping_lines(value, child_pad) if isinstance(value, dict) else _list_lines(list(value), child_pad)
            lines = ["", *body]
        elif _is_block_string(value):
            header, content = _block_parts(str(value), pad + 2)
            lines = [f" {header}", *content]
        else:
            lines = [f" {render_scalar(value)}"]

        multi = len(lines) > 1
        region_end = end
        append = inside
        if multi and after is not None:
            region_end = doc.eol(end)
            append = inside or after
        if block_coll:
            region_end = doc.eol(end)
        if append:
            lines[0] = f"{lines[0]} {append}"
        replacement = "\n".join(lines)
        if self._is_keep_chomp_block(node):
            # The old span runs to the start of the next line (blank lines are
            # part of a ``|+`` value), so the replacement must end the line.
            replacement += "\n"
        self.add(region_start, region_end, replacement)
        return None

    def _is_keep_chomp_block(self, node: Node) -> bool:
        """Return True for a block scalar whose header keeps trailing newlines."""
        if not isinstance(node, ScalarNode) or node.style not in ("|", ">"):
            return False
        start = node.start_mark.index
        header = self.doc.text[start : self.doc.eol(start)]
        return _BLOCK_CHOMP_KEEP.match(header) is not None

    def _old_info(self, node: Node, floor: int, is_item: bool) -> tuple[int, str | None, str | None, bool, int]:
        """Describe the old value: end, comments, block-collection flag, child indent."""
        doc = self.doc
        text = doc.text
        if isinstance(node, ScalarNode):
            start = node.start_mark.index
            if node.style in ("|", ">"):
                end = doc.end_of(node)
                header = text[start : doc.eol(start)]
                match = _BLOCK_HEADER.match(header)
                inside = match.group(1) if match and match.group(1) else None
                return end, inside, None, False, 0
            end = node.end_mark.index
            if end == start:
                end = floor
            rest = text[end : doc.eol(end)].strip()
            return end, None, rest if rest.startswith("#") else None, False, 0
        end = doc.end_of(node)
        if node.flow_style:
            rest = text[end : doc.eol(end)].strip()
            return end, None, rest if rest.startswith("#") else None, False, 0
        inside = None
        if not is_item:
            head = text[floor : doc.eol(floor)].strip()
            inside = head if head.startswith("#") else None
        if isinstance(node, MappingNode):
            existing = node.value[0][0].start_mark.column
        else:
            first = doc.dash_index(node, 0)
            existing = first - doc.line_start(first)
        return end, inside, None, True, existing

    # -- mapping groups ---------------------------------------------------

    def _finish_map(self, group: _MapGroup) -> Exception | None:
        doc = self.doc
        mapping = group.target.node
        assert isinstance(mapping, MappingNode)
        deletes = sorted(set(group.deletes))
        remaining = len(mapping.value) - len(deletes)

        if mapping.flow_style:
            if mapping.value:
                return ValueError("flow-style mapping cannot be edited in place")
            new_map = dict(group.inserts)
            if group.target.parent is None:
                self.add(
                    mapping.start_mark.index,
                    mapping.end_mark.index,
                    "\n".join(_mapping_lines(new_map, 0)),
                )
                return None
            return self._region(group.target, value=new_map)

        if remaining == 0:
            new_map = dict(group.inserts)
            if group.target.parent is not None:
                return self._region(group.target, value=new_map)
            first_key = mapping.value[0][0]
            start = doc.line_start(first_key.start_mark.index)
            end = doc.after_line(doc.end_of(mapping))
            body = "\n".join(_mapping_lines(new_map, 0)) if new_map else "{}"
            self.add(start, end, body + "\n")
            return None

        problem = self._plan_key_deletes(mapping, deletes)
        if problem is not None:
            return problem
        if group.inserts:
            self._plan_key_inserts(mapping, group.inserts)
        return None

    def _plan_key_deletes(self, mapping: MappingNode, deletes: list[int]) -> Exception | None:
        doc = self.doc
        skip_below = 0
        if deletes and deletes[0] == 0:
            first_key = mapping.value[0][0]
            lead = doc.text[doc.line_start(first_key.start_mark.index) : first_key.start_mark.index]
            if lead.strip() != "":
                remaining_at = next(position for position in range(len(mapping.value)) if position not in deletes)
                last_deleted = remaining_at - 1
                end = doc.after_line(doc.child_end(mapping, 2 * last_deleted + 1, mapping.value[last_deleted][1]))
                next_key = mapping.value[remaining_at][0]
                if end == doc.line_start(next_key.start_mark.index):
                    end += next_key.start_mark.column
                self.add(first_key.start_mark.index, end, "")
                skip_below = remaining_at
        for position in deletes:
            if position < skip_below:
                continue
            key_node, value_node = mapping.value[position]
            start = doc.line_start(key_node.start_mark.index)
            end = doc.after_line(doc.child_end(mapping, 2 * position + 1, value_node))
            self.add(start, end, "")
        return None

    def _plan_key_inserts(self, mapping: MappingNode, inserts: list[tuple[str, Any]]) -> None:
        doc = self.doc
        pad = mapping.value[0][0].start_mark.column
        position = doc.after_line(doc.end_of(mapping))
        lines = _mapping_lines(dict(inserts), pad)
        self._add_lines(position, lines)

    def _add_lines(self, position: int, lines: list[str]) -> None:
        text = self.doc.text
        body = "\n".join(lines)
        if position >= len(text) and text and not text.endswith("\n"):
            self.add(position, position, "\n" + body)
            return
        self.add(position, position, body + "\n")

    # -- sequence groups --------------------------------------------------

    def _finish_seq(self, group: _SeqGroup) -> Exception | None:
        doc = self.doc
        seq = group.target.node
        assert isinstance(seq, SequenceNode)
        deletes = sorted(set(group.deletes))
        remaining = len(seq.value) - len(deletes)

        if seq.flow_style and seq.value:
            return ValueError("flow-style list cannot be edited in place")

        if remaining == 0:
            if not group.inserts:
                return self._region(group.target, value=[])
            if group.target.parent is None:
                return ValueError("cannot rebuild the document root")

            def build(pad: int) -> list[str]:
                lines: list[str] = []
                for edit in group.inserts:
                    lines.extend(self._item_lines(edit, pad))
                return lines

            return self._region(group.target, container_lines=build)

        for position in deletes:
            span = doc.item_span(seq, position)
            if isinstance(span, Exception):
                return span
            self.add(span[0], span[1], "")
        if not group.inserts:
            return None
        last = doc.item_span(seq, len(seq.value) - 1)
        if isinstance(last, Exception):
            return last
        first_dash = doc.dash_index(seq, 0)
        pad = first_dash - doc.line_start(first_dash)
        lines: list[str] = []
        for edit in group.inserts:
            lines.extend(self._item_lines(edit, pad))
        self._add_lines(last[1], lines)
        return None

    @staticmethod
    def _item_lines(edit: YamlEdit, pad: int) -> list[str]:
        if edit.raw_text is not None:
            return _reindent_item(edit.raw_text, pad)
        return _owner_lines(pad, "-", edit.value, True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_yaml_edits(
    text: str,
    edits: list[YamlEdit],
    *,
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> str | Exception:
    """Apply ``edits`` to ``text`` and return the new text, or an ``Exception``.

    Only the spans that an edit touches are rewritten. ``aliases`` maps a path key
    to other key names that may hold it in the file (for example
    ``{"from": ("from_endpoint",)}``); the key bytes in the file are never renamed.
    The result is re-composed, so text that no longer parses is returned as an error.
    """
    doc = _Doc.build(text, aliases or {})
    if isinstance(doc, Exception):
        return doc
    planner = _Planner(doc)
    problem = planner.plan(edits)
    if problem is not None:
        return problem
    ordered = sorted(planner.splices, key=lambda s: (s.start, s.end, s.order))
    reach = 0
    for splice in ordered:
        if splice.start < reach:
            return ValueError("edits overlap the same text span")
        reach = max(reach, splice.end)
    pieces: list[str] = []
    cursor = 0
    for splice in ordered:
        pieces.append(text[cursor : splice.start])
        pieces.append(splice.text)
        cursor = splice.end
    pieces.append(text[cursor:])
    result = "".join(pieces)
    try:
        yaml.compose(result, Loader=yaml.SafeLoader)
    except yaml.YAMLError as err:
        return ValueError(f"splice produced invalid YAML: {err}")
    return result


def list_item_text(text: str, path: tuple[str | ItemRef, ...]) -> str | Exception:
    """Return the text of one list item, from its indent and ``-`` to its end.

    ``path`` walks mappings by key and ends with the ``ItemRef`` of the item.
    """
    if not path or not isinstance(path[-1], ItemRef):
        return ValueError(f"path must end with an ItemRef: {path!r}")
    doc = _Doc.build(text, {})
    if isinstance(doc, Exception):
        return doc
    target = doc.resolve(path[:-1])
    if isinstance(target, Exception):
        return target
    seq = target.node
    if not isinstance(seq, SequenceNode):
        return ValueError(f"{path[:-1]!r} is not a list")
    if seq.flow_style:
        return ValueError(f"flow-style list around {path!r}")
    position = doc.match_item(seq, path[-1])
    if isinstance(position, Exception):
        return position
    span = doc.item_span(seq, position)
    if isinstance(span, Exception):
        return span
    return text[span[0] : span[1]]
