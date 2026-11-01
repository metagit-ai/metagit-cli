# YAML Round-trip Fidelity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A save of an existing manifest rewrites only the nodes that changed, so untouched scalars keep their original bytes.

**Architecture:** `yaml_edit_diff` compares two `build_metagit_payload` dicts and returns `YamlEdit` values. `yaml_splice` applies those edits to the original file text using PyYAML node marks. `save_config` and `save_partitioned` splice files that already exist and keep today's full renderer only when the destination file is missing. `fmt` stays on `format_yaml_document`.

**Tech Stack:** Python 3.12, PyYAML compose/scan marks, Pydantic `MetagitConfig`, pytest, existing `build_metagit_payload`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-31-yaml-roundtrip-fidelity-design.md`. Follow it verbatim.
- Public functions that can fail return `Exception` (or a union with `Exception`). They do not raise for expected failures.
- New Python files start with `#!/usr/bin/env python`. Type hints on every function. Imports at the top. No unused imports.
- Match Black's 4-space style used by `src/metagit`. Run `uv run pytest` on the tests you add.
- Do not commit. Do not edit files outside your task.
- Do not change `format_yaml_document`, `fmt`, or appconfig rendering.
- A new or replaced string must `yaml.safe_load` back to the assigned value. Never insert newlines into a string that had none.
- `--no-format` on an existing file uses the same splice as a normal save.
- If a splice cannot be applied, return an error and write no file in that save.
- `YamlEdit` and `ItemRef` live in `src/metagit/core/config/yaml_edit_types.py`. Do not move them.

---

### Task 1: Value-preserving splice

**Files:**
- Create: `src/metagit/core/config/yaml_splice.py`
- Create: `tests/core/config/test_yaml_splice_engine.py`
- Consumes: `yaml_edit_types.YamlEdit`, `yaml_edit_types.ItemRef`
- Produces: `apply_yaml_edits(text: str, edits: list[YamlEdit], *, aliases: dict[str, tuple[str, ...]] | None = None) -> str | Exception`
- Produces: `render_scalar(value: object) -> str`
- Produces: `list_item_text(text: str, path: tuple[str | ItemRef, ...]) -> str | Exception`

- [ ] **Step 1: Write failing engine tests**

Cover at least:

- Replacing one short scalar leaves a folded `>-` sibling, a `|` sibling, a `|-` sibling, a plain multi-line sibling, a single-quoted multi-line sibling, a double-quoted multi-line sibling, and both a same-line comment and a comment on the previous line as exact substrings.
- The replacement parses back to the assigned string.
- A replacement string that contains a newline is a `|` or `|-` block and parses back to that string, including a string that does not end in a newline (`|-`).
- A long single-line replacement stays one line.
- `insert_key` adds one line and does not change an existing sibling line.
- `delete_key` removes that key and leaves the previous-line comment.
- `delete_item` removes one repo and leaves a comment that sits between items attached to the following item.
- Deleting the last list item leaves `repos: []` (parsed value is a list).
- `insert_item` into `repos: []` writes a block item and parses back.
- `insert_item` with `raw_text` copies that text, reindented to the destination list, and does not restyle an existing sibling.
- A flow-style mapping around the edited key returns an `Exception` and the function does not return new text.
- An alias key `from_endpoint` is updated when the path key is `from` and `aliases={"from": ("from_endpoint",)}`. The key text stays `from_endpoint`.
- Two edits in one call both apply. Untouched lines stay byte-identical.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/core/config/test_yaml_splice_engine.py -q`

Expected: fail because `yaml_splice` does not exist.

- [ ] **Step 3: Implement**

`render_scalar` rules:

- `True`/`False`/`None` → `true` / `false` / `null`. `int` and `float` → `str(value)`.
- A `str` with no newline is one line. Plain when it is non-empty, has no leading or trailing whitespace, does not start with `-` or `?`, does not parse as a boolean, null, or number, and contains none of `: { } [ ] , & * ! | >` quotes `# % @` or a backtick. Otherwise double-quoted via `json.dumps`.
- A `str` that contains newlines uses `|` when it ends with a newline and `|-` otherwise. Content lines are copied, not wrapped or stripped. The caller indents them.

`apply_yaml_edits`:

- `yaml.compose` the text. On `YAMLError` or a non-mapping root, return the error.
- Record `start_mark.index` and `end_mark.index`. PyYAML scalar spans include the indicator (`|-`, `|`, quotes). Replacing that span replaces the value token and leaves a same-line comment, which sits outside the scalar span.
- List-item spans start at the beginning of the `-` line. They end at the next item's preamble. A full-line comment between items whose indent is less than or equal to the `-` indent belongs to the following item, not the item being deleted. Confirmed against PyYAML: the mapping node for an item starts after the `-`, and its `end_mark` can swallow the following between-item comment. Do not use the mapping `end_mark` as the item end.
- Resolve mapping keys by the path string or any name in `aliases` for that string. Do not rename the key bytes.
- `ItemRef` kinds: `name` matches `name`, `node` matches `node_key` from `include_loader`, `relationship` matches `relationship_key`, `identity` matches `_list_item_identity`, `index` matches the decimal index. Zero or more than one match returns an `Exception`.
- Abort, returning an `Exception`, when the node is an alias, any ancestor collection has `flow_style` true (except the empty-list cases below), or the node has an anchor.
- Last remaining `delete_item` rewrites the parent value to ` []` so the key line becomes `repos: []`.
- `insert_item` into a flow `[]` replaces `[]` with a block sequence.
- `insert_item` with `raw_text` reindents that block so its `-` matches the destination item indent and nested lines keep relative indent.
- `insert_key` inserts one new line after the last key of the parent, at that parent's child indent.
- Compute every span on the original text. If spans overlap, return an `Exception`. Apply from the end of the string toward the start.
- Child indent for a rendered block is the parent key's column plus 2, or the existing child indent when the parent already has children.

`list_item_text` returns the item span, including its leading indent and `-`, without a surrounding document.

- [ ] **Step 4: Run the engine tests**

Run: `uv run pytest tests/core/config/test_yaml_splice_engine.py -q`

Expected: pass.

### Task 2: Payload diff

**Files:**
- Create: `src/metagit/core/config/yaml_edit_diff.py`
- Create: `tests/core/config/test_yaml_edit_diff.py`
- Consumes: `YamlEdit`, `ItemRef`, `include_loader.node_key`, `include_loader.relationship_key`, `yaml_roundtrip._list_item_identity`
- Produces: `diff_payloads(before: object, after: object) -> list[YamlEdit] | Exception`

- [ ] **Step 1: Write failing diff tests**

- Equal payloads return `[]`.
- Changing one string returns one `replace` whose path is the key tuple and whose `value` is the new string.
- Adding a key returns `insert_key`. Removing a key returns `delete_key`. Key order changes return `[]`.
- Projects and repos match by `name`. Changing one repo description does not emit edits for the sibling repo.
- Appending a project returns one `insert_item`. Deleting one returns one `delete_item`. The sibling is absent from the edit list.
- Graph nodes match through `node_key`. Relationships match through `relationship_key`.
- A list with no identity falls back to `ItemRef(kind="index", value=...)`.
- Two items with the same `name` return an `Exception`.
- A string that becomes a mapping is one `replace` of that path.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/core/config/test_yaml_edit_diff.py -q`

- [ ] **Step 3: Implement `diff_payloads`**

Walk both values.

- Scalars, or values of different types: one `replace`.
- Mappings: keys only on the right are `insert_key`. Keys only on the left are `delete_key`. Shared keys recurse. Ignore key order.
- Lists: pick the identity from the parent key. `projects` and `repos` use `name`. `documentation` uses `name` when present, otherwise the index. `nodes` uses `node_key`. `relationships` uses `relationship_key`. Anything else uses `_list_item_identity`, then the index.
- An identity that matches two items returns `ValueError`.
- Unmatched left items are `delete_item` and carry the old mapping on `value` only when useful; the required field is the path ending in the `ItemRef`.
- Unmatched right items are `insert_item` with `value` set to the new item.
- A matched pair recurses. Its path includes the `ItemRef`. Sibling items produce no edits.

The parent key that selects the list rule is the last string segment of the path (`projects`, `repos`, `nodes`, `relationships`, `documentation`).

- [ ] **Step 4: Run the diff tests**

Run: `uv run pytest tests/core/config/test_yaml_edit_diff.py -q`

Expected: pass.

### Task 3: Wire save

Do this only after Tasks 1 and 2 pass. They touch different files. Task 3 touches the writers.

**Files:**
- Modify: `src/metagit/core/config/manager.py` `save_config`
- Modify: `src/metagit/core/config/include_writer.py` `save_partitioned`
- Modify: `tests/core/config/test_include_roundtrip.py` `test_single_file_save_stays_byte_stable`
- Create: `tests/core/config/test_yaml_splice.py`
- Modify: `docs/reference/splitting-manifests.md`
- Modify: `CHANGELOG.md` under `## Unreleased`
- Modify: `.mex/ROUTER.md` current state

Before editing `save_config` or `save_partitioned`, run GitNexus impact:

`node .gitnexus/run.cjs impact save_config --direction upstream --repo .`

`node .gitnexus/run.cjs impact save_partitioned --direction upstream --repo .`

Report the risk. `HIGH` or `CRITICAL` means stop and report. `UNKNOWN` means confirm callers with a text search before editing.

**Save behavior:**

- Build the baseline by loading the destination path from disk into `MetagitConfig` (composed when it has `includes`).
- Build both payloads with `build_metagit_payload` and the save's `include_defaults` flag.
- Split manifests: `partition_payload` both sides with the on-disk source map. A file whose partition signature matches is not opened.
- `includes` is copied from the source map into both partitions, so an unchanged include list is not an edit.
- For a file that exists and whose payload differs, `diff_payloads` then `apply_yaml_edits`. Pass aliases so `from` updates a file key `from_endpoint` without renaming it. Build that map from pydantic validation aliases (`from` → `from_endpoint` and the reverse).
- A cross-file move is a `delete_item` in one partition and an `insert_item` in another with the same `ItemRef`. Copy `list_item_text` from the source. When the item payloads differ, splice the field diff into that item text first, then set `raw_text` on the destination insert. Then delete the source item.
- Render every spliced string before writing any file. The first error returns and leaves every destination unchanged.
- A path that does not exist still uses `_render_part` / `render_metagit` / `yaml.dump`, selected by `auto_format`, as today.
- A no-op save does not open the file for write.

**Tests in `tests/core/config/test_yaml_splice.py`:**

1. Style fixture through `MetagitConfigManager.save_config`. One unrelated short string changes. The unified diff touches only that key's lines. Every other scalar style remains as an exact substring. `yaml.safe_load` differs only at the edited path.
2. Table of one edit each: set a string, set a string that contains a newline, add a key, delete a key, append a repo, delete a repo. Parsed YAML matches except at the edited path.
3. No-op save of a single-file manifest and of a split fragment does not change bytes.
4. `save_config(..., auto_format=False)` does not rewrite an untouched long string.
5. Save to a missing path still returns text from the existing renderer (`render_metagit` when `auto_format` is true).
6. A flow-style mapping around the edited key returns an `Exception` and the file bytes stay the same.
7. `WorkspaceLayoutService.move_repo(..., move_disk=False)` between two project fragments. Each file's diff is only the moved list item. The moved description keeps its original newlines. A repo that stayed behind keeps its exact description substring.

Update `test_single_file_save_stays_byte_stable`: the first unchanged `save_config()` must leave the original bytes in place. Remove the assertion that the first save equals `render_metagit`. A second save also leaves those bytes. `includes:` is still absent.

Run:

`uv run pytest tests/core/config/test_yaml_splice_engine.py tests/core/config/test_yaml_edit_diff.py tests/core/config/test_yaml_splice.py tests/core/config/test_yaml_roundtrip.py tests/core/config/test_include_roundtrip.py tests/cli/commands/test_config_includes.py -q`

**Docs:** one paragraph in `docs/reference/splitting-manifests.md`: a save rewrites edited nodes in the owning fragment; `fmt` is the restyle command. Changelog `## Unreleased` line for the save behavior. `.mex/ROUTER.md` current-state bullet that the splice is implemented.

### Task 4: Gate

- [ ] `task qa:prepush` from the repo root, outside the sandbox if `.metagit/*.log` is blocked.
- [ ] `task gitnexus:analyze` after QA passes.
