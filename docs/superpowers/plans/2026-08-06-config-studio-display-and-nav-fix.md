# Config Studio Display Options and Nav Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Config Studio display options (minimal tree defaults, bottom optional YAML preview, left chevron expand) and fix `metagit nav` (global `-c` manifest detect, non-preview FuzzyFinder layout, definition-rooted sync path).

**Architecture:** Frontend-only session display prefs on `ConfigPage`/`SchemaTree`; CLI setup sniffs global `-c` into AppConfig vs `definition_path`; `nav` prefers stashed definition path and `resolve_workspace_root`; FuzzyFinder non-preview CSS uses full-width results.

**Tech Stack:** React + TypeScript (Vite web/), Click CLI, Pydantic AppConfig/MetagitConfig, Textual FuzzyFinder, pytest, Taskfile (`web:build`, `qa:prepush`, `gitnexus:analyze`).

**Spec:** `docs/superpowers/specs/2026-08-06-config-studio-display-and-nav-fix-design.md`

## Global Constraints

- Display option defaults (all off unless noted): YAML preview off; unassigned off; list item headers off; element numbering off; type labels off. List headers **on** is not the default.
- Session-only prefs (no `localStorage`).
- Unassigned = `enabled === false` schema nodes.
- When list headers off: omit list-item rows; inline object-item children under the array; scalar list items hidden until headers re-enabled; array `+` append remains.
- Global `-c` manifest detect: no top-level `config:` + manifest shape (`name` / `kind` / `workspace`); stash `definition_path`; load default AppConfig.
- Nav sync root must use `resolve_workspace_root(manifest_path, app_config.workspace.path)`.
- FuzzyFinder non-preview results must not use the 35%-width split-only class.
- Commits: conventional `fix:` / `feat:` as appropriate; do not amend pushed commits; do not force-push.
- Before claiming done: `task qa:prepush` then `task gitnexus:analyze`.
- Update `CHANGELOG.md` and `.mex/ROUTER.md` on closeout.
- Use `uv run` for Python; 2-space indent in Python; GitNexus `impact` before editing symbols when MCP available.
- Before any `gh` command: `unset GH_TOKEN GITHUB_TOKEN`.

---

## File map

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/utils/fuzzyfinder.py` | Non-preview full-width results CSS/compose |
| `src/metagit/cli/config_path.py` (new) | Sniff AppConfig vs Metagit manifest path |
| `src/metagit/cli/main.py` | Use sniffer; set `ctx.obj["definition_path"]` |
| `src/metagit/cli/commands/nav.py` | Prefer definition_path; resolve sync root into ProjectManager |
| `web/src/pages/ConfigPage.tsx` (+ CSS) | Display options; 2-col + optional bottom preview |
| `web/src/components/SchemaTree.tsx` (+ CSS) | Chevrons; filter/display flags |
| `web/src/components/ConfigPreview.tsx` (+ CSS) | Bottom-span friendly max-height |
| `tests/test_utils_fuzzyfinder.py` | Non-preview CSS assertion |
| `tests/cli/test_config_path.py` (new) | Sniffer unit tests |
| `tests/cli/commands/test_nav.py` | Nav definition_path + sync root |
| `CHANGELOG.md`, `.mex/ROUTER.md` | Closeout |

---

### Task 1: FuzzyFinder non-preview layout

**Files:**
- Modify: `src/metagit/core/utils/fuzzyfinder.py`
- Test: `tests/test_utils_fuzzyfinder.py`

**Interfaces:**
- Produces: Non-preview `ListView` uses class `fuzzy-finder-results-full` (or equivalent) with `width: 100%` and parent `height: 1fr`; preview mode keeps `fuzzy-finder-results` at 35% inside split.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_utils_fuzzyfinder.py`:

```python
def test_fuzzyfinder_non_preview_css_is_full_width():
  assert "fuzzy-finder-results-full" in FuzzyFinderApp.CSS
  assert ".fuzzy-finder-results-full" in FuzzyFinderApp.CSS
  # split list stays narrow
  assert "width: 35%" in FuzzyFinderApp.CSS


def test_fuzzyfinder_compose_non_preview_uses_full_width_class():
  config = FuzzyFinderConfig(items=["a", "b"], enable_preview=False)
  app = FuzzyFinderApp(config)
  widgets = list(app.compose())
  # Walk compose yield tree: Vertical contains ListView with full class
  css_classes = FuzzyFinderApp.CSS
  assert "fuzzy-finder-results-full" in css_classes
```

Prefer asserting compose markup by inspecting `FuzzyFinderApp.compose` source or by checking the class string applied in the non-preview branch after implementation. Minimal assert that is stable:

```python
def test_fuzzyfinder_non_preview_results_class_in_css_and_compose_source():
  import inspect
  from metagit.core.utils.fuzzyfinder import FuzzyFinderApp

  assert ".fuzzy-finder-results-full" in FuzzyFinderApp.CSS
  assert "width: 100%" in FuzzyFinderApp.CSS
  src = inspect.getsource(FuzzyFinderApp.compose)
  assert "fuzzy-finder-results-full" in src
  assert "enable_preview" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_utils_fuzzyfinder.py::test_fuzzyfinder_non_preview_results_class_in_css_and_compose_source -v`  
Expected: FAIL (class missing)

- [ ] **Step 3: Implement layout fix**

In `FuzzyFinderApp.CSS`, add:

```css
.fuzzy-finder-results-full {
    width: 100%;
    border: solid $primary;
    scrollbar-gutter: stable;
    overflow-y: auto;
    height: 1fr;
}

.fuzzy-finder-body {
    height: 1fr;
}
```

In `compose`, non-preview branch:

```python
with Vertical(classes="fuzzy-finder-body"):
    yield ListView(id="results_list", classes="fuzzy-finder-results-full")
```

Keep preview branch using `fuzzy-finder-results` (35%) inside `fuzzy-finder-split`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_utils_fuzzyfinder.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/utils/fuzzyfinder.py tests/test_utils_fuzzyfinder.py
git commit -m "$(cat <<'EOF'
fix: show full-width FuzzyFinder results when preview is off

EOF
)"
```

---

### Task 2: CLI config path sniffer

**Files:**
- Create: `src/metagit/cli/config_path.py`
- Create: `tests/cli/test_config_path.py`
- Modify: `src/metagit/cli/main.py`

**Interfaces:**
- Produces:
  - `detect_cli_config_file(path: str) -> Literal["appconfig", "manifest", "missing", "invalid"]`
  - `resolve_cli_bootstrap(path: str) -> tuple[AppConfig | Exception, str | None]`  
    Returns `(app_config_or_error, definition_path_or_None)`.
- Consumes: `load_config`, `DEFAULT_CONFIG`, `yaml.safe_load`

- [ ] **Step 1: Write failing tests** in `tests/cli/test_config_path.py`

```python
#!/usr/bin/env python
from pathlib import Path

from metagit.cli.config_path import detect_cli_config_file, resolve_cli_bootstrap


def test_detect_appconfig(tmp_path: Path) -> None:
  p = tmp_path / "metagit.config.yaml"
  p.write_text("config:\n  description: x\n  editor: code\n", encoding="utf-8")
  assert detect_cli_config_file(str(p)) == "appconfig"


def test_detect_manifest(tmp_path: Path) -> None:
  p = tmp_path / ".metagit.yml"
  p.write_text("name: umb\nkind: umbrella\nworkspace:\n  projects: []\n", encoding="utf-8")
  assert detect_cli_config_file(str(p)) == "manifest"


def test_detect_invalid(tmp_path: Path) -> None:
  p = tmp_path / "junk.yml"
  p.write_text("foo: 1\n", encoding="utf-8")
  assert detect_cli_config_file(str(p)) == "invalid"


def test_resolve_manifest_loads_default_appconfig(tmp_path: Path) -> None:
  p = tmp_path / ".metagit.yml"
  p.write_text("name: umb\nkind: umbrella\nworkspace:\n  projects: []\n", encoding="utf-8")
  cfg, definition = resolve_cli_bootstrap(str(p))
  assert not isinstance(cfg, Exception)
  assert definition == str(p)
```

- [ ] **Step 2: Run tests — expect FAIL** (module missing)

Run: `uv run pytest tests/cli/test_config_path.py -v`

- [ ] **Step 3: Implement `config_path.py`**

```python
#!/usr/bin/env python
"""Resolve top-level CLI ``-c`` as AppConfig or Metagit manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Tuple, Union

import yaml

from metagit import DEFAULT_CONFIG
from metagit.core.appconfig import AppConfig, load_config

ConfigKind = Literal["appconfig", "manifest", "missing", "invalid"]


def detect_cli_config_file(path: str) -> ConfigKind:
  file_path = Path(path).expanduser()
  if not file_path.is_file():
    return "missing"
  try:
    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
  except Exception:
    return "invalid"
  if not isinstance(data, dict):
    return "invalid"
  if "config" in data and isinstance(data["config"], dict):
    return "appconfig"
  if any(key in data for key in ("name", "kind", "workspace")):
    return "manifest"
  return "invalid"


def resolve_cli_bootstrap(
  path: str,
) -> Tuple[Union[AppConfig, Exception], Optional[str]]:
  kind = detect_cli_config_file(path)
  if kind == "missing":
    cfg = load_config(DEFAULT_CONFIG)
    return cfg, None
  if kind == "appconfig":
    return load_config(path), None
  if kind == "manifest":
    cfg = load_config(DEFAULT_CONFIG)
    return cfg, str(Path(path).expanduser())
  return (
    ValueError(
      f"Path '{path}' is neither metagit.config.yaml (top-level 'config:') "
      "nor a .metagit.yml manifest (expected keys like name/kind/workspace)."
    ),
    None,
  )
```

Wire `main.py` `cli()` to use `resolve_cli_bootstrap`:
- On missing file: keep current fallback to `DEFAULT_CONFIG` (definition_path None).
- On invalid: log error message from Exception and `ctx.abort()`.
- On success: `ctx.obj["definition_path"] = definition` (may be None); `ctx.obj["config_path"]` remains the AppConfig path actually loaded (DEFAULT_CONFIG when manifest-detected).

When kind is missing and path was user-supplied nonexistent file, preserve existing debug log + DEFAULT_CONFIG behavior.

- [ ] **Step 4: Run tests — expect PASS**

Run: `uv run pytest tests/cli/test_config_path.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/config_path.py src/metagit/cli/main.py tests/cli/test_config_path.py
git commit -m "$(cat <<'EOF'
fix: detect .metagit.yml on global CLI -c

EOF
)"
```

---

### Task 3: Nav uses definition_path + sync root

**Files:**
- Modify: `src/metagit/cli/commands/nav.py`
- Modify: `tests/cli/commands/test_nav.py`

**Interfaces:**
- Consumes: `ctx.obj.get("definition_path")`, `resolve_workspace_root`, `ProjectManager`
- Produces: Nav resolves manifest as: if `manifest_path` != default `.metagit.yml` use it; elif `definition_path` use that; else `.metagit.yml`. Builds `ProjectManager(resolve_workspace_root(manifest, app_config.workspace.path), logger, dedupe=...)`.

- [ ] **Step 1: Write failing tests**

Extend `tests/cli/commands/test_nav.py`:

```python
def test_nav_global_manifest_c_sets_definition_for_nav(tmp_path: Path, monkeypatch) -> None:
  app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
  opened: list[str] = []
  monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda *_a, **_k: opened.append(_a[1]) or None)
  # Invoke with GLOBAL -c as the manifest (no appconfig wrapper)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["--config", str(metagit_yml), "nav", "-p", "platform", "--repo", "backend"],
    catch_exceptions=False,
  )
  assert result.exit_code == 0, result.output
  assert opened


def test_nav_resolves_sync_root_from_manifest_dir(tmp_path: Path, monkeypatch) -> None:
  """Nav must not use cwd-relative ./.metagit when manifest is elsewhere."""
  app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
  other = tmp_path / "othercwd"
  other.mkdir()
  opened: list[str] = []
  monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda e, p: opened.append(p))
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["--config", str(app_cfg), "nav", "-c", str(metagit_yml), "-p", "platform", "--repo", "backend"],
    catch_exceptions=False,
  )
  assert result.exit_code == 0
  assert Path(opened[0]).resolve() == (tmp_path / ".metagit" / "platform" / "backend").resolve()
```

Also add a unit-style assert that `project_manager_from_app` is not used with unresolved relative path — prefer constructing ProjectManager with resolved root inside nav (may stop using `project_manager_from_app` or pass resolved path by constructing `ProjectManager` + `resolve_effective_dedupe` directly).

- [ ] **Step 2: Run — expect FAIL** on global manifest `-c` case

- [ ] **Step 3: Implement nav.py**

```python
from metagit.core.workspace.root_resolver import resolve_definition_root, resolve_workspace_root
from metagit.core.project.manager import ProjectManager, resolve_effective_dedupe
from metagit.core.workspace.layout_resolver import find_project

DEFAULT_MANIFEST = ".metagit.yml"

# inside nav_cmd:
definition_from_ctx = ctx.obj.get("definition_path")
effective_manifest = manifest_path
if manifest_path == DEFAULT_MANIFEST and definition_from_ctx:
  effective_manifest = definition_from_ctx

manager = MetagitConfigManager(effective_manifest)
...
project = find_project(local_config, resolved_project) if resolved_project else None
dedupe = resolve_effective_dedupe(app_config.workspace.dedupe, project)
sync_root = resolve_workspace_root(effective_manifest, app_config.workspace.path)
project_manager = ProjectManager(sync_root, logger, dedupe=dedupe)
```

Use `effective_manifest` everywhere `manifest_path` was used for loading/resolving.

- [ ] **Step 4: Run nav tests**

Run: `uv run pytest tests/cli/commands/test_nav.py tests/cli/test_config_path.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/commands/nav.py tests/cli/commands/test_nav.py
git commit -m "$(cat <<'EOF'
fix: home nav sync root to manifest and honor global -c

EOF
)"
```

---

### Task 4: Config Studio display options + layout + tree polish

**Files:**
- Modify: `web/src/pages/ConfigPage.tsx`, `web/src/pages/ConfigPage.module.css`
- Modify: `web/src/components/SchemaTree.tsx`, `web/src/components/SchemaTree.module.css`
- Modify: `web/src/components/ConfigPreview.module.css` (optional max-height for bottom band)

**Interfaces:**
- Produces display flags type:

```ts
export type ConfigDisplayOptions = {
  showYamlPreview: boolean
  showUnassigned: boolean
  showListItemHeaders: boolean
  showElementNumbering: boolean
  showTypeLabels: boolean
}

export const DEFAULT_CONFIG_DISPLAY_OPTIONS: ConfigDisplayOptions = {
  showYamlPreview: false,
  showUnassigned: false,
  showListItemHeaders: false,
  showElementNumbering: false,
  showTypeLabels: false,
}
```

- `SchemaTree` props gain `displayOptions` (omit `showYamlPreview`).
- Tree behavior per spec decisions 5–7.

- [ ] **Step 1: Add display options state + toolbar on ConfigPage**

Defaults from `DEFAULT_CONFIG_DISPLAY_OPTIONS`. Toolbar checkboxes/labels:
- Show YAML preview
- Show unassigned fields
- Show list item headers
- Show element numbering
- Show type labels

- [ ] **Step 2: Relayout CSS**

```css
.layout {
  display: grid;
  grid-template-columns: minmax(14rem, 1fr) minmax(16rem, 1.2fr);
  gap: 1.25rem;
  align-items: start;
}

.previewBelow {
  grid-column: 1 / -1;
  /* used when preview is a child of a wrapping grid, or separate block below */
}
```

Structure:

```tsx
<div className={styles.layout}>
  <aside>...</aside>
  <FieldEditor ... />
</div>
{displayOptions.showYamlPreview ? (
  <ConfigPreview ... />
) : null}
```

Preview CSS: `max-height: min(40vh, 24rem)` for bottom band (horizontal span).

- [ ] **Step 3: SchemaTree polish + filters**

- Move expand control to **left** chevron (`▸` / `▾`) before checkbox.
- Pass `displayOptions`.
- When mapping children for render:
  - Filter out nodes with `enabled === false` unless `showUnassigned`.
  - For array children that are list items (`/^\[\d+\]$/`):
    - If `!showListItemHeaders`: if node has children, render those children inlined (still applying unassigned/type/numbering rules); if no children (scalar item), skip.
    - If `showListItemHeaders` && `!showElementNumbering`: render header but hide/omit the `[0]` key text (show type only if `showTypeLabels`, plus action buttons).
  - Hide `.type` span unless `showTypeLabels`.

- [ ] **Step 4: Build web**

Run: `task web:build`  
Expected: success; updates `src/metagit/data/web/`

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/ConfigPage.tsx web/src/pages/ConfigPage.module.css \
  web/src/components/SchemaTree.tsx web/src/components/SchemaTree.module.css \
  web/src/components/ConfigPreview.module.css src/metagit/data/web
git commit -m "$(cat <<'EOF'
feat: add Config Studio display options and bottom YAML preview

EOF
)"
```

---

### Task 5: Closeout (CHANGELOG, mex, QA, gitnexus)

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `.mex/ROUTER.md`
- Optionally create: `.mex/patterns/config-studio-display-options.md` if no matching pattern

- [ ] **Step 1: CHANGELOG** under Unreleased — note Config Studio display options + nav/FuzzyFinder fixes.

- [ ] **Step 2: Update `.mex/ROUTER.md` project state** with this work; bump `last_updated`.

- [ ] **Step 3: Run QA**

Run: `task qa:prepush`  
Fix failures until green.

- [ ] **Step 4: GitNexus**

Run: `task gitnexus:analyze`

- [ ] **Step 5: Commit closeout**

```bash
git add CHANGELOG.md .mex/ROUTER.md .mex/patterns 2>/dev/null
git commit -m "$(cat <<'EOF'
docs: record Config Studio display options and nav fixes

EOF
)"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Left chevron expand polish | Task 4 |
| YAML preview bottom optional, default hidden | Task 4 |
| Unassigned default off | Task 4 |
| List headers default off + inline children | Task 4 |
| Numbering default off | Task 4 |
| Type labels default off | Task 4 |
| Session-only prefs | Task 4 |
| Global `-c` manifest detect + definition_path | Task 2–3 |
| Clear error for junk `-c` | Task 2 |
| FuzzyFinder non-preview full width | Task 1 |
| Nav `resolve_workspace_root` | Task 3 |
| web:build packaged SPA | Task 4 |
| CHANGELOG + ROUTER + qa + gitnexus | Task 5 |
