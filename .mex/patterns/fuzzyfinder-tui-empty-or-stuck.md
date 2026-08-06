---
name: fuzzyfinder-tui-empty-or-stuck
description: Diagnose metagit FuzzyFinder TUIs that show no items or ignore Ctrl+C.
last_updated: 2026-08-06
---

# FuzzyFinder empty list or stuck quit

## Symptoms
- `metagit nav` (or project picker) opens with an empty results pane even though the manifest has projects.
- `Ctrl+C` / `Esc` does not leave the TUI.

## Checks
1. **Which binary?** `which metagit` and `metagit --version`. PyPI `0.26.0` lacks the non-preview full-width layout fix; local/`main` has it.
2. **String-item opacity bug:** `FuzzyFinderConfig.get_item_opacity` must use `self.item_opacity`, not `self.config.item_opacity`. The typo raises on plain-string items (project picker); `_perform_search` used to catch that and wipe `current_results` → empty list with meta `Showing 0/N`.
3. **Preview-off layout:** project picker uses `enable_preview=False`. Results must use `.fuzzy-finder-results-full` (`width: 100%`) inside `.fuzzy-finder-body` (`height: 1fr`). A bare `.fuzzy-finder-results` (`width: 35%`) in a vertical stack can collapse to an empty-looking pane.
4. **Quit bindings:** `FuzzyFinderApp.BINDINGS` for `ctrl+c` / `escape` / `ctrl+q` need `priority=True` so focused `Input` does not swallow them. `KeyboardInterrupt` in `_run_textual_app` / `FuzzyFinder.run` should return `None` (cancel).
5. **Manifest path:** `nav -c` should `Path(...).expanduser()`; sync root must home relative `workspace.path` to the manifest directory (`resolve_workspace_root`).

## Reproduce (headless)
```python
# Meta "Showing 0/N | query: all" with current_results=[] after mount = opacity/update exception path
```

## Fix / verify
```bash
# Prefer local tree when unreleased fixes matter
uv tool install --force --reinstall --from . metagit-cli
metagit --version   # expect >= local dirty/dev with results-full + priority quit

metagit nav -c ~/path/to/.metagit.yml
# Esc or Ctrl+C / Ctrl+Q should exit; projects should list without typing
```

## Related
- `src/metagit/core/utils/fuzzyfinder.py`
- `src/metagit/core/project/project_picker.py`
- `src/metagit/cli/commands/nav.py`
