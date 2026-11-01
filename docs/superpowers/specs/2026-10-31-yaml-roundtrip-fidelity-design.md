---
name: yaml-roundtrip-fidelity
description: Manifest saves splice only the nodes that changed so untouched scalars keep their original bytes.
last_updated: 2026-10-31
---

# YAML round-trip fidelity

**Date:** 2026-10-31
**Status:** Implemented on `feat/yaml-roundtrip-fidelity`

Saves of an existing `.metagit.yml` or fragment rewrite only the nodes that changed. Untouched scalars keep their original style and their original bytes. `metagit fmt` remains the only command that restyles a file.

## Problem

`MetagitConfigManager.save_config` and `save_partitioned` turn the Pydantic model into a document and dump the whole file.

- With formatting, `format_yaml_document` merges that payload in `yaml_roundtrip._merge_map`. Every string goes through `_normalize_value` → `format_yaml_string`. Strings longer than 88 columns become `|-` blocks with inserted newlines. Those newlines are part of the parsed value.
- With `--no-format`, `save_config` `yaml.dump`s the model and `save_partitioned` dumps the partition with PyYAML. That also rewrites every node.

A one-field edit of a single-file umbrella manifest rewrites thousands of lines. The same edit on a split manifest rewrites the fragment and inserts newlines into descriptions that were not edited. `project repo move` restyles the destination fragment beyond the moved block. `fmt` is a separate, explicit restyle and stays that way.

`0.34.1` and `0.37.0` already dump the same bytes. This is the current writer, not a regression.

## Decisions

1. **Splice the original text.** Diff the on-disk model against the model about to be saved. Apply that diff to the original file text. A full-document dump cannot keep exact bytes: ruamel reflows at width 88 even when scalar objects are left alone.
2. **Diff model dumps, not the model against raw YAML.** Both sides use `build_metagit_payload` (`exclude_none`, `exclude_defaults` unless `include_defaults`, `mode="json"`, `by_alias=True`, then `prepare_format_payload`). Alias renames and omitted defaults that the model always produces do not count as edits, so they do not touch the file.
3. **Callers stay on `save_config`.** The writer discovers the edit set. Call sites do not grow an edit log.
4. **A new value parses back to the assigned string.** The emitter never inserts newlines into a string that had none. `--no-format` uses this same emitter. The flag means "do not restyle the file." It does not select a second document dumper.
5. **A missing target file keeps today's renderer.** There is no original text to preserve. `format_yaml_document` still renders that new file when `auto_format` is true, and PyYAML dumps it when `auto_format` is false.
6. **`fmt` is unchanged in this slice.** It may still restyle every node, including the width-88 wrap. Save stops calling it for files that already exist.
7. **Failure writes nothing.** If any edited path cannot be spliced, the save returns an error and no file in that save is opened for write.

## Out of scope

- Lossless `flatten`, `load_composed`, `config diff`, and `content_sha256`.
- `[name=]` / `[id=]` selectors on `set` and `patch`. The splice uses those identities internally. The CLI does not accept them yet.
- Glob includes, `fmt --check` after `split`, and `patch --json` tree output.
- Duplicate-repo validation, `skill_sources`, a single `-c` spelling, and read-only `repo list` / `graph` commands.
- Worktree discovery.
- Appconfig (`metagit.config.yaml`) saves. They stay on `render_appconfig`.
- Changing `fmt` so its wrap is value-preserving.
- `project sync` fetching existing clones. Fetch already exists on MCP and web `WorkspaceSyncService`. `project sync` still only clones.
- Git `insteadOf` reachability. Metagit has no such check.

## Edit set

At save time the destination file on disk is still the pre-edit text.

1. Load that file (composed, when it has `includes`) into a baseline `MetagitConfig`.
2. Build payloads for the baseline and for the config being saved with the same `include_defaults` flag the save is using.
3. For a split manifest, `partition_payload` both payloads with the on-disk source map. A file whose partition signature matches the baseline is not opened. That keeps today's skip of untouched fragments.
4. Diff the two payloads (or the two partitions) into a list of edits. `includes` is copied from the on-disk source map into both partitions, so an unchanged include list is not an edit.

A no-op save, including a single-file manifest, does not write and does not change mtime. Today a single-file `save_config` always rewrites the file.

### Structural diff

Walk the two payloads together.

| Shape | Rule |
| --- | --- |
| Scalars, or unequal types | One `replace` at that path |
| Mappings | Keys only on the right are `insert_key`. Keys only on the left are `delete_key`. Shared keys recurse. Key order is not an edit. |
| Lists of projects | Match by `name` |
| Lists of repos | Match by `name` |
| Lists of documentation entries | Match by `name` when present, otherwise by index |
| Lists of graph nodes | Match by `node_key` (`identity`, else `name`, else the canonical JSON of the mapping) |
| Lists of graph relationships | Match by `relationship_key` (`id`, else the from/to/type tuple) |
| Any other list | Match by `yaml_roundtrip._list_item_identity` (url, path, name, artifact). Items with no identity match by index. |

An unmatched left item is `delete_item`. An unmatched right item is `insert_item`. A matched pair recurses into the item. Sibling items are not edits.

Index fallback can mark items after an insert or delete as changed. Projects, repos, nodes, and relationships do not use that fallback. The acceptance tests use those collections.

### Cross-file move

An item deleted from partition A and inserted into partition B with the same identity is a move.

When that item's field diff is empty, copy its list-item text from A, from the `-` through the end of the item, and insert that text into B. Nested lines keep their relative indent. The destination `-` is reindented to the destination list's item indent. Then delete the item from A. Bytes outside that block stay as they were in both files.

When the moved item also has field edits, splice those fields inside the source item text, then move the resulting text the same way.

## Splice

New module `metagit.core.config.yaml_splice`. It takes original text plus edits and returns new text or an `Exception`. It does not load or dump a Pydantic model.

Locate nodes with a composer that records character offsets (`start_mark.index` / `end_mark.index` on the stream string). Walk tokens so a list item's span includes the indent and the `-`, and ends before the next sibling.

| Edit | What changes in the file |
| --- | --- |
| `replace` of a scalar | The value token only. The key bytes stay, including an alias such as `from_endpoint` when the dump key is `from`. A same-line comment after the value stays. |
| `replace` of a mapping or list | The value span of that node, rendered with the value-preserving emitter. |
| `insert_key` | One new line after the last key of the parent mapping, at that mapping's indent. |
| `delete_key` | From the indent of the key line through the end of its value. A comment on the preceding line stays. A same-line comment is on the deleted line and goes with it. |
| `delete_item` | From the indent of the `-` through the end of the item, including the newline that ends it. A comment line between items stays with the following item. |
| `insert_item` | The rendered item, or the moved raw block, after the last item. The new `-` uses the list's existing item indent. Nested lines use that same relative indent. |
| Last item removed | The parent key is rewritten to an empty flow list (`repos: []`) so the parsed value stays a list. |
| Insert into `[]` | That empty flow sequence becomes a block sequence holding the new item. |

Apply splices from the end of the file toward the start so earlier offsets stay valid.

Resolve a dump path to a file node by the key and by the model's aliases (`find_source_key`). Do not rename the key that is already in the file.

### Abort cases

Return an error and write nothing when:

- The path is missing and the edit is not an insert.
- The node to change is a YAML alias, or any ancestor collection is flow style, except the empty-list cases in the table above.
- The node is a merge key or an anchor whose span cannot be separated from the value.
- A list identity matches more than one item.
- The original file is not valid YAML.

Block-style manifests written by Metagit take the splice path. `fmt` remains available for a file that uses flow style.

### Value-preserving emitter

Used for every new or replaced node inside an existing file.

- A string with no newline is one single-line scalar. It is plain when the text is non-empty, has no leading or trailing whitespace, does not start with `-` or `?`, does not parse as a boolean, null, or number, and contains none of `:`, `{`, `}`, `[`, `]`, `,`, `&`, `*`, `!`, `|`, `>`, quotes, `#`, `%`, `@`, or a backtick. Otherwise it is double-quoted. The emitter does not wrap at 88 columns.
- A string that already contains newlines is a literal block. Use `|` when the string ends with a newline and `|-` when it does not. Content lines are copied. They are not rewrapped or stripped.
- Mappings and lists render in block style. Keys follow the payload order. Child indent matches the parent mapping's existing child indent, or two spaces when the parent has no children.
- `true` / `false` / `null` / numbers use plain YAML forms.

`--no-format` and a normal save both call this emitter for edits to an existing file.

## Integration

`save_partitioned` keeps signature skip, partition, and the "write after every part is rendered" loop. For a file that exists and whose signature changed, it splices instead of calling `_render_part`. For a file that does not exist, it still calls `_render_part`.

`MetagitConfigManager.save_config` for a single-file manifest uses the same diff and splice when the path exists. The `auto_format` branch that calls `ConfigFormatService.render_metagit`, and the `yaml.dump` branch, run only when the path does not exist.

Build every spliced string first. Write the set only after every file succeeds. A mid-save failure leaves every destination unchanged.

`render_partition` and `metagit fmt` keep `format_yaml_document`.

## Tests

`tests/core/config/test_yaml_splice.py`

1. **Style fixture.** One document contains, on keys other than the one under test: a plain multi-line scalar, `>`, `>-`, `|`, `|-`, a single-quoted multi-line scalar, and a double-quoted multi-line scalar, plus comments on and above an untouched key. Load it, set one unrelated short string, save. The unified diff touches only the edited key's lines. Every other scalar's exact substring is still in the file. `yaml.safe_load` of before and after differs only at the edited path, and that path equals the assigned string.
2. **Property cases.** A table of one-edit operations on a small manifest: set a string, set a string that contains a newline, add a key, delete a key, append a repo, delete a repo. Each case asserts `safe_load(after)` equals `safe_load(before)` except at the edited path. There is no Hypothesis dependency. The table is the property test.
3. **No-op.** Load and save with no mutation. The file bytes stay the same for both a single-file manifest and a split fragment, and the save does not open either file for write.
4. **`--no-format`.** The same one-field edit does not rewrite an untouched long string.
5. **New file.** Saving to a path that does not exist still returns a document from the existing renderer.
6. **Abort.** A flow-style mapping around the edited key returns an error and leaves the file bytes unchanged.
7. **Move.** Two project fragments. `WorkspaceLayoutService.move_repo` with `move_disk=False`. Each file's diff is only the removed or added list item. Descriptions inside the moved item keep their original wording and newlines. A repo in the destination that was not moved keeps its exact description substring.

Run the existing `tests/core/config/test_yaml_roundtrip.py`, `tests/core/config/test_include_roundtrip.py`, and `tests/cli/commands/test_config_includes.py` to confirm `fmt` and include skip still behave as they do today.

## Docs

After implementation, add a short paragraph to `docs/reference/splitting-manifests.md`: a save rewrites edited nodes in the owning fragment, and `fmt` is the restyle command. Add an Unreleased changelog line on that implementation, not for this spec.
