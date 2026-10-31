---
name: split-manifest-includes
description: Compose and write back a .metagit.yml that lists includes of project and graph fragments.
triggers:
  - "includes:"
  - "split manifest"
  - "config split"
  - "config flatten"
  - "fragment schema"
edges:
  - target: patterns/bootstrap-metagit-config.md
    condition: when creating a new single-file manifest before any split
  - target: context/architecture.md
    condition: when tracing load and save through MetagitConfigManager
last_updated: 2026-10-31
---

# Split manifest includes

## Context
A root `.metagit.yml` may list `includes` of relative paths or globs. `include_loader` merges `workspace.projects`, `graph.nodes`, and `graph.relationships`. `include_writer` partitions a later save back onto those files. Manifests with no `includes` key stay on the original single-file load and save path.

## Steps
1. Load with `MetagitConfigManager.load_config`. When the file declares `includes`, the manager sets `source_map` and `resolved_files`. `includes` is stripped from the merged model so `model_dump` matches a single-file manifest.
2. Save with `save_config`. If the destination file declares `includes`, the save reloads a source map from disk even when the manager was built with an in-memory config. That is what keeps catalog, layout, promote, and patch from flattening fragments.
3. New projects go to `<first include directory>/<slug>.yml` only when every current project already lives alone in its file. Otherwise they stay in the root. An emptied fragment stays as an empty list.
4. Split with `split_manifest` / `metagit config split`. It writes explicit ordered include paths, not a glob, so list order is preserved. Flatten with `flatten_manifest`.
5. Point watchers and digest mtimes at `manifest_watch_paths` / `resolved_files`, not only the root.

## Gotchas
- Do not call `yaml.safe_load` on the root and treat that as the full manifest. `cli/config_path.py` uses `manifest_watch_paths`.
- `!include` is not a manifest feature. It was removed from `ExtLoader`.
- Signature skip on save compares model partitions, not formatter bytes. `metagit fmt` still renders every file.
- A second reference to the same resolved path is an error, including a diamond. Depth above 3 is an error. The root is depth 0.
- Older clients reject `includes` because `MetagitConfig` uses `extra = "forbid"`.

## Verify
- [ ] `tests/core/config/test_include_loader.py` and `tests/core/config/test_include_roundtrip.py` pass.
- [ ] `tests/cli/commands/test_config_includes.py` passes.
- [ ] A save that edits one project changes only that fragment's sha256 and mtime.
- [ ] `task generate:schema` includes `schemas/metagit_fragment.schema.json`.
