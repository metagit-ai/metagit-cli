---
name: release-0382-defects
description: Defects found against 0.38.1 and the constraints that keep the 0.38.2 fixes from drifting.
triggers:
  - "0.38.2"
  - "graph rewrite"
  - "config patch append"
  - "merge regenerate"
edges:
  - target: patterns/split-manifest-includes.md
    condition: when a graph edit must land in the fragment that owns the relationship
  - target: patterns/release-0381-defects.md
    condition: when the failure is split fidelity, worktree discovery, or pull-request lookup
last_updated: 2026-11-03
---

# 0.38.2 defect fixes

## Context

Regression coverage is `tests/cli/commands/test_0382_release.py`. The version comes from setuptools-scm. Do not edit `src/metagit/_version.py`.

Release notes belong under `## Unreleased`. Semantic Release on `main` skips the tag when that section is empty, even if a `## [0.38.x]` heading is already present. A push that only touches `CHANGELOG.md` and `docs/changelog.md` is ignored by that workflow.

## Gotchas

- `rewrite_graph_references` rewrites `{project, repo}` and a `project/repo` identity. An identity containing `://` or `git@` is a URL and stays. `repo_from is None` means a project rename.
- A project-qualified endpoint that misses the local project must not fall through to the global index. A bare `repo:` or `identity:` endpoint still may.
- Partitioned save writes the relationship into the fragment that owns it. The layout service constructs a fresh manager; the includes path loads the baseline itself.
- `config set` parses JSON, then YAML, when the field is a dict, list, or model. Echo the path with `click.echo`. `UnifiedLogger.success` eats `[name=]` selectors.
- CLI and `--file` patch pass `allow_default_append=False`. The web add-row button keeps the default placeholder. Duplicate-repo findings stay warnings and do not fail a patch. Graph and component issues do.
- A top-level patch file may contain `operations`, `save`, and `auto_format`. Any other key is rejected. `--save` ORs with the file's `save`.
- Printed paths use `from` and `graph.nodes[id=]`. The resolver aliases `from` to `from_endpoint` and matches a node `id` selector on `identity` only when the item has no `id`.
- Usage errors exit 2. JSON is `{"ok": false, "error": ...}` with no `schema_version`.
- `diff_values` matches lists by name, id, or identity and reports a pure reorder as one `order` entry. `yaml_edit_diff._diff_lists` already matches by identity; leave it. Glob split sorts named lists before the fidelity diff, so that diff stays empty.
- `project repo move` accepts repeated `-n` and saves once. `workspace repo move` stays a single name. There is no free-form repo `metadata` field, so there is no `--meta`.
- When regenerate meets a path absent from the target HEAD, remove it from the index and do not `git add` a path that is now ignored. A path that exists on the target still uses `git checkout --ours`.

## Verify

- `uv run pytest tests/cli/commands/test_0382_release.py`
- `task qa:prepush`
