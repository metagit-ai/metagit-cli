---
name: config-studio-display-and-nav-fix
description: Config Studio tree display options + YAML preview layout; fix metagit nav empty picker and global -c manifest detect.
last_updated: 2026-08-06
---

# Config Studio Display Options and Nav Fixes

**Date:** 2026-08-06  
**Status:** Approved (design)

## Summary

Improve Metagit Web Config Studio (`/config/metagit`, `/config/appconfig`) with polished tree expand/collapse, a bottom optional YAML preview, and session-only display toggles that default to a minimal tree. Fix `metagit nav` so global `-c` pointing at a `.metagit.yml` works, the project FuzzyFinder list is visible when preview is off, and the repo step homes `workspace.path` to the manifest directory.

## Problem

1. **Config Studio density:** Schema trees show unassigned optional fields, list item headers (`[0]`), numbering, and type labels by default, making large manifests hard to scan. YAML preview competes for horizontal space in a three-column grid.
2. **Global `-c` vs nav `-c`:** `metagit -c path/to/.metagit.yml nav` feeds the top-level AppConfig loader, which expects a `config:` key and fails with `Error loading config: 'config'`.
3. **Empty project picker:** `metagit nav` (and `nav -c <manifest>`) opens the project FuzzyFinder but the results list appears empty from both the umbrella directory and other cwds. Root cause: non-preview FuzzyFinder still applies `.fuzzy-finder-results { width: 35%; height: 1fr }` outside the split layout.
4. **Wrong sync root:** `nav` builds `ProjectManager` from `app_config.workspace.path` without `resolve_workspace_root()`, so relative `./.metagit` resolves against cwd rather than the manifest directory (unlike `project` / `workspace`).

## Decisions

1. **Approach:** Frontend-only display prefs + small CLI detect (no server-side tree query flags; no global `-c` rename across the CLI).
2. **Expand/collapse:** Keep per-node toggles; polish to a left chevron with a clearer hit target. No expand-all/collapse-all; no default-collapsed nested levels.
3. **YAML preview:** Optional full-width card under Schema | Field editor; **hidden by default**; session toggle.
4. **Display options:** Session-only React state (reset on refresh). Defaults all minimize the tree:

   | Option | Default |
   |--------|---------|
   | Show YAML preview | off |
   | Show unassigned fields (`enabled === false`) | off |
   | Show list item header row | off |
   | Show element numbering (`[0]`) | off |
   | Show object/type labels (e.g. `Workspace`, `string`) | off |

5. **Unassigned fields:** Mean schema nodes with `enabled === false`. Hidden by default; when shown, enable/disable checkboxes remain available.
6. **List headers / numbering:** When list item header rows are off, list-item rows are omitted and each item’s children are inlined under the parent array (scalar list items are skipped in the tree until headers are re-enabled; edit via Field editor after selecting the array or enabling headers). Array-level append (`+`) stays available. When headers are on but numbering is off, keep the header row but omit the `[0]` key label; type labels follow the separate type-label toggle.
7. **Type labels:** The `type` / `type_label` chips next to keys in the schema tree (not YAML tags).
8. **Global `-c` auto-detect:** If the file exists and is a Metagit manifest (no top-level `config:`; has manifest shape such as `name` / `kind` / `workspace`), load default AppConfig, stash `ctx.obj["definition_path"]`, and let `nav` prefer that when its `-c` is still the default `.metagit.yml`. Neither AppConfig nor manifest → clear error describing both expected shapes.
9. **FuzzyFinder fix:** Non-preview mode uses full-width results with a proper height parent (do not reuse the 35% split width).
10. **Nav sync root:** Resolve via `resolve_workspace_root(manifest_path, app_config.workspace.path)` before `ProjectManager` / `select_repo`.

## Architecture

### Config Studio

```text
ConfigPage
  header + DisplayOptions (session state)
  layout row: SchemaTree | FieldEditor
  optional full-width ConfigPreview (when showYamlPreview)
```

- `SchemaTree` / `TreeNode` accept display flags; filter unassigned; optionally suppress list-item header rows, `[0]` labels, and type chips.
- Expand control moves to a left chevron button.
- No `localStorage`; prefs live in `ConfigPage` (or a tiny hook) for the page session.

### CLI / nav

```text
cli() load path
  → if AppConfig shape: load as today
  → else if Metagit manifest shape: default AppConfig + definition_path
  → else: clear error

nav_cmd
  → manifest = nav -c if non-default else ctx.obj definition_path or default
  → sync_root = resolve_workspace_root(manifest, app_config.workspace.path)
  → ProjectManager(sync_root, ...)
  → project FuzzyFinder → repo FuzzyFinder → open_editor
```

### Expected files

| Path | Role |
|------|------|
| `web/src/pages/ConfigPage.tsx` (+ CSS) | Two-column + optional bottom preview; display options state |
| `web/src/components/SchemaTree.tsx` (+ CSS) | Chevrons; filter/display flags |
| `web/src/components/ConfigPreview.tsx` (+ CSS) | Consume bottom-span layout |
| `web/src/components/*DisplayOptions*` (or inline) | Toggle UI |
| `src/metagit/cli/main.py` | Manifest sniff + `definition_path` |
| `src/metagit/cli/commands/nav.py` | Prefer definition_path; resolve sync root |
| `src/metagit/core/utils/fuzzyfinder.py` | Non-preview results layout |
| `tests/cli/commands/test_nav.py` (+ CLI setup tests as needed) | Detect, sync root, nav wiring |
| `tests/test_utils_fuzzyfinder.py` (or adjacent) | Non-preview layout / search regression |
| `CHANGELOG.md`, `.mex/ROUTER.md` | Record change |

Rebuild packaged SPA with `task web:build` so `metagit web serve` serves the new UI.

## Error handling

- Global `-c` junk file: abort with an explicit message that the path is neither `metagit.config.yaml` (top-level `config:`) nor a `.metagit.yml` manifest.
- Nav missing/invalid manifest: existing `ClickException` paths.
- FuzzyFinder cancel / empty selection: existing non-zero exits.

## Testing

- Config Studio: unit/component coverage where the repo already tests React pieces; otherwise lean on build + manual checks for toggle defaults and layout.
- CLI: global `-c` manifest → `definition_path` set; junk `-c` → helpful error; nav uses definition-rooted sync path.
- FuzzyFinder: empty-query search still returns all string items; non-preview compose/CSS uses full-width results class (not 35% split-only styles).

## Out of scope

- Renaming or unifying `-c` / `--definition` across all commands.
- Persisting display preferences across reloads.
- Server-side `/v3/config/*/tree` query flags for display filtering.
- Expand-all / collapse-all / default-collapsed nested trees.

## Verification

1. `task qa:prepush`
2. `task gitnexus:analyze`
3. Manual: Config Studio toggles on `/config/metagit` and `/config/appconfig`; `metagit -c <umbrella>/.metagit.yml nav` and `metagit nav` from umbrella and another cwd show project names.
