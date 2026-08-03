# Metagit `nav` / `navigate` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `metagit nav` (alias `navigate`) — FuzzyFinder project pick, then existing FuzzyFinder repo pick, then open the configured editor.

**Architecture:** Thin Click command in `nav.py` resolves the project (flag / sole project / FuzzyFinder helper), then reuses `ProjectManager.select_repo` / `resolve_selected_repo_path` and `open_editor`. Rejects `agent_mode`. Does not modify the TUI hub.

**Tech Stack:** Python 3, Click, Textual FuzzyFinder (`metagit.core.utils.fuzzyfinder`), pytest, CliRunner.

**Design:** [2026-08-03-metagit-nav-design.md](../specs/2026-08-03-metagit-nav-design.md)

## Global Constraints

- 2-space indent; type hints; imports at file top; `#!/usr/bin/env python` on new files.
- Reject interactive use when `ctx.obj["agent_mode"]` is true.
- Intentional deviation from `.mex/patterns/cli-tui-hub.md` (hub prefers ListViews); document in pattern gotcha.
- Before hand-off: `task qa:prepush` then `task gitnexus:analyze`; update `.mex/ROUTER.md`.
- Commit messages: `feat:` for this additive CLI surface.

## File map

| Path | Responsibility |
|------|----------------|
| Create: `src/metagit/core/project/project_picker.py` | `select_project_name(...)` FuzzyFinder over project names |
| Create: `src/metagit/cli/commands/nav.py` | Click `nav` command |
| Modify: `src/metagit/cli/main.py` | Register `nav` + alias `navigate` |
| Create: `tests/core/project/test_project_picker.py` | Unit tests for project picker |
| Create: `tests/cli/commands/test_nav.py` | CLI tests |
| Modify: `CHANGELOG.md` | Unreleased feat entry |
| Modify: `.mex/patterns/cli-tui-hub.md` | Note `nav` Fuzzy→Fuzzy exception |
| Modify: `.mex/ROUTER.md` | Project state |

---

### Task 1: Project name FuzzyFinder helper

**Files:**
- Create: `src/metagit/core/project/project_picker.py`
- Test: `tests/core/project/test_project_picker.py`

**Interfaces:**
- Produces: `select_project_name(project_names: list[str], *, menu_length: int = 10) -> str | None | Exception`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python
"""Unit tests for interactive project name picker."""

from __future__ import annotations

from metagit.core.project import project_picker


def test_select_project_name_empty_list_returns_error() -> None:
  result = project_picker.select_project_name([])
  assert isinstance(result, ValueError)


def test_select_project_name_returns_finder_selection(monkeypatch) -> None:
  class _FakeFinder:
    def __init__(self, config) -> None:
      self.config = config

    def run(self):
      return "platform"

  monkeypatch.setattr(project_picker, "FuzzyFinder", _FakeFinder)
  result = project_picker.select_project_name(["platform", "edge"])
  assert result == "platform"
  assert [i for i in _FakeFinder.__init__.__globals__] or True  # finder was constructed
  assert result == "platform"


def test_select_project_name_none_on_cancel(monkeypatch) -> None:
  class _FakeFinder:
    def __init__(self, _config) -> None:
      pass

    def run(self):
      return None

  monkeypatch.setattr(project_picker, "FuzzyFinder", _FakeFinder)
  assert project_picker.select_project_name(["a", "b"]) is None
```

Fix the sloppy assert in the middle test when implementing — keep only `assert result == "platform"`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/project/test_project_picker.py -v`  
Expected: FAIL with import / module not found.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python
"""Interactive FuzzyFinder selection for workspace project names."""

from __future__ import annotations

from typing import Optional, Union

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def select_project_name(
  project_names: list[str],
  *,
  menu_length: int = 10,
) -> Union[str, None, Exception]:
  """Run FuzzyFinder over project names. Returns selected name, None if cancelled, or Exception."""
  names = [n for n in project_names if n]
  if not names:
    return ValueError("No workspace projects are defined in .metagit.yml")
  config = FuzzyFinderConfig(
    items=sorted(names),
    prompt_text="Search projects: ",
    max_results=menu_length,
    total_count=len(names),
    query_mode_label="matches",
    score_threshold=60.0,
    highlight_color="bold white bg:#0066cc",
    normal_color="cyan",
    prompt_color="bold green",
    separator_color="gray",
    enable_preview=False,
  )
  selected = FuzzyFinder(config).run()
  if isinstance(selected, Exception):
    return selected
  if selected is None:
    return None
  if isinstance(selected, str):
    return selected
  return ValueError(f"Unexpected project selection type: {type(selected)!r}")
```

- [ ] **Step 4: Run tests and ensure they pass**

Run: `uv run pytest tests/core/project/test_project_picker.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/project/project_picker.py tests/core/project/test_project_picker.py
git commit -m "$(cat <<'EOF'
feat: add FuzzyFinder helper for workspace project names

EOF
)"
```

---

### Task 2: CLI `nav` / `navigate` command

**Files:**
- Create: `src/metagit/cli/commands/nav.py`
- Modify: `src/metagit/cli/main.py` (import + `cli.add_command(nav_cmd, name="nav")` and `cli.add_command(nav_cmd, name="navigate")`)
- Test: `tests/cli/commands/test_nav.py`

**Interfaces:**
- Consumes: `select_project_name`, `list_project_names`, `find_project`, `project_manager_from_app`, `open_editor`
- Produces: Click command registered as `nav` and `navigate`

- [ ] **Step 1: Write failing CLI tests**

```python
#!/usr/bin/env python
"""CLI tests for metagit nav / navigate."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _write_multi_project_fixture(tmp_path: Path) -> tuple[Path, Path]:
  workspace = tmp_path / ".metagit"
  for project, repo in (("platform", "backend"), ("edge", "gateway")):
    repo_dir = workspace / project / repo
    repo_dir.mkdir(parents=True)
    (repo_dir / "README.md").write_text("hello", encoding="utf-8")

  metagit_yml = tmp_path / ".metagit.yml"
  metagit_yml.write_text(
    "\n".join(
      [
        "name: test",
        "kind: umbrella",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: backend",
        "          url: https://example.com/backend.git",
        "    - name: edge",
        "      repos:",
        "        - name: gateway",
        "          url: https://example.com/gateway.git",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  app_cfg = tmp_path / "metagit.config.yaml"
  app_cfg.write_text(
    "\n".join(
      [
        "config:",
        "  description: test",
        "  editor: echo",
        "  workspace:",
        f"    path: {workspace.as_posix()}",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return app_cfg, metagit_yml


def test_nav_project_and_repo_flags_open_editor(tmp_path: Path, monkeypatch) -> None:
  app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
  opened: list[str] = []

  def _fake_open(editor: str, path: str):
    opened.append(path)
    return None

  monkeypatch.setattr("metagit.cli.commands.nav.open_editor", _fake_open)
  monkeypatch.setattr(
    "metagit.cli.commands.nav.select_project_name",
    lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("project picker should not run")),
  )

  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "nav",
      "-c",
      str(metagit_yml),
      "-p",
      "platform",
      "--repo",
      "backend",
    ],
    catch_exceptions=False,
  )
  assert result.exit_code == 0
  assert len(opened) == 1
  assert Path(opened[0]).resolve() == (tmp_path / ".metagit" / "platform" / "backend").resolve()


def test_navigate_alias_works(tmp_path: Path, monkeypatch) -> None:
  app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
  monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda *_a, **_k: None)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "navigate",
      "-c",
      str(metagit_yml),
      "-p",
      "edge",
      "--repo",
      "gateway",
    ],
    catch_exceptions=False,
  )
  assert result.exit_code == 0


def test_nav_rejects_agent_mode(tmp_path: Path, monkeypatch) -> None:
  app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
  monkeypatch.setenv("METAGIT_AGENT_MODE", "true")
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "nav",
      "-c",
      str(metagit_yml),
      "-p",
      "platform",
      "--repo",
      "backend",
    ],
  )
  assert result.exit_code != 0
  assert "agent mode" in result.output.lower() or "agent mode" in (result.exception.args[0] if result.exception else "").lower()


def test_nav_unknown_project_exits_nonzero(tmp_path: Path) -> None:
  app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "nav",
      "-c",
      str(metagit_yml),
      "-p",
      "missing",
      "--repo",
      "backend",
    ],
  )
  assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/cli/commands/test_nav.py -v`  
Expected: FAIL (command not registered / module missing).

- [ ] **Step 3: Implement `nav.py` and register in `main.py`**

`src/metagit/cli/commands/nav.py`:

```python
#!/usr/bin/env python
"""Top-level interactive project → repo navigation (FuzzyFinder)."""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.shell_completion import complete_projects, complete_repos
from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.project.manager import project_manager_from_app
from metagit.core.project.project_picker import select_project_name
from metagit.core.utils.common import open_editor
from metagit.core.workspace.layout_resolver import find_project, list_project_names
from metagit.core.workspace.root_resolver import resolve_definition_root


@click.command("nav")
@click.option(
  "--config",
  "-c",
  "manifest_path",
  default=".metagit.yml",
  show_default=True,
  help="Path to the metagit definition file",
)
@click.option(
  "--project",
  "-p",
  "project_name",
  default=None,
  help="Project within workspace (skips project picker)",
  shell_complete=complete_projects,
)
@click.option(
  "--repo",
  "repo_name",
  default=None,
  help="Repository name (skips repo picker)",
  shell_complete=complete_repos,
)
@click.pass_context
def nav_cmd(
  ctx: click.Context,
  manifest_path: str,
  project_name: Optional[str],
  repo_name: Optional[str],
) -> None:
  """Pick a project, then a repo, and open it in the configured editor."""
  logger = ctx.obj["logger"]
  if ctx.obj.get("agent_mode"):
    raise click.UsageError("Interactive navigation is disabled in agent mode")

  app_config: AppConfig = ctx.obj["config"]
  manager = MetagitConfigManager(manifest_path)
  local_config = manager.load_config()
  if isinstance(local_config, Exception):
    raise click.ClickException(str(local_config))

  names = list_project_names(local_config)
  resolved_project = project_name
  if resolved_project:
    if find_project(local_config, resolved_project) is None and resolved_project != "local":
      raise click.ClickException(f"Project '{resolved_project}' not found in workspace configuration.")
  elif len(names) == 1:
    resolved_project = names[0]
  else:
    picked = select_project_name(
      names,
      menu_length=app_config.workspace.ui_menu_length,
    )
    if isinstance(picked, Exception):
      raise click.ClickException(str(picked))
    if picked is None:
      raise click.ClickException("No project selected")
    resolved_project = picked

  project_manager = project_manager_from_app(
    app_config,
    logger,
    metagit_config=local_config,
    project_name=resolved_project,
  )
  definition_root = resolve_definition_root(manifest_path)

  if repo_name:
    selected_repo = project_manager.resolve_selected_repo_path(
      local_config,
      resolved_project,
      repo_name,
      definition_root=definition_root,
    )
  else:
    selected_repo = project_manager.select_repo(
      local_config,
      resolved_project,
      show_preview=app_config.workspace.ui_show_preview,
      menu_length=app_config.workspace.ui_menu_length,
      ignore_hidden=app_config.workspace.ui_ignore_hidden,
      agent_mode=False,
    )

  if isinstance(selected_repo, Exception):
    raise click.ClickException(str(selected_repo))
  if selected_repo is None:
    raise click.ClickException("No repo selected")

  logger.info(f"Selected repo: {selected_repo}")
  editor_result = open_editor(app_config.editor, selected_repo)
  if isinstance(editor_result, Exception):
    raise click.ClickException(f"Failed to open editor: {editor_result}")
  logger.info(f"Opened {selected_repo} in {app_config.editor}")
```

In `main.py`: add `from metagit.cli.commands.nav import nav_cmd` and:

```python
cli.add_command(nav_cmd, name="nav")
cli.add_command(nav_cmd, name="navigate")
```

- [ ] **Step 4: Run CLI tests**

Run: `uv run pytest tests/cli/commands/test_nav.py tests/core/project/test_project_picker.py -v`  
Expected: PASS

Also: `uv run metagit nav --help` and `uv run metagit navigate --help` show the same options.

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/commands/nav.py src/metagit/cli/main.py tests/cli/commands/test_nav.py
git commit -m "$(cat <<'EOF'
feat: add metagit nav/navigate for project then repo open

EOF
)"
```

---

### Task 3: Docs, changelog, pattern, router

**Files:**
- Modify: `CHANGELOG.md` (Unreleased / Added)
- Modify: `.mex/patterns/cli-tui-hub.md` (gotcha: `metagit nav` is Fuzzy→Fuzzy by design)
- Modify: `.mex/ROUTER.md` (Working bullet for nav)
- Optionally mention in `docs/install.md` or CLI help is enough for v1 — prefer a one-line note in `docs/agents.md` only if agent docs list human shortcuts; otherwise changelog + help is enough.

- [ ] **Step 1: Add CHANGELOG entry under Unreleased Added**

```markdown
- `metagit nav` / `metagit navigate`: FuzzyFinder project pick then repo pick, then open editor.
```

- [ ] **Step 2: Pattern gotcha**

Append to Gotchas in `.mex/patterns/cli-tui-hub.md`:

```markdown
- `metagit nav` / `navigate` intentionally uses FuzzyFinder for project then repo (not in-TUI ListViews). Do not fold that UX into the hub without an explicit design change.
```

Bump `last_updated: 2026-08-03`.

- [ ] **Step 3: Update ROUTER project state**

Add a Working bullet for `metagit nav|navigate` with link to the design/plan.

- [ ] **Step 4: QA gate**

Run: `task qa:prepush`  
Fix until green.

- [ ] **Step 5: GitNexus**

Run: `task gitnexus:analyze`

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md .mex/patterns/cli-tui-hub.md .mex/ROUTER.md
git commit -m "$(cat <<'EOF'
docs: document metagit nav FuzzyFinder shortcut

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| `nav` + `navigate` alias | Task 2 |
| Fuzzy→Fuzzy UX | Tasks 1–2 |
| `-p` / `--repo` skips | Task 2 |
| Sole project skips project picker | Task 2 (branch in `nav_cmd`) |
| Agent mode rejected | Task 2 |
| Reuse `select_repo` / `open_editor` | Task 2 |
| No TUI hub / MCP changes | All tasks |
| Tests | Tasks 1–2 |
| CHANGELOG / pattern / ROUTER | Task 3 |
