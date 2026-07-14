#!/usr/bin/env python
"""Textual application for the Metagit interactive CLI hub."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static

from metagit.core.tui.catalog import build_command_catalog, flatten_actions
from metagit.core.tui.interactive import run_interactive_catalog_action
from metagit.core.tui.models import TuiCommandAction, TuiMenuSection, WizardAnswers
from metagit.core.tui.navigation import (
    list_manifest_projects,
    list_manifest_repos,
    maybe_single_project,
    open_selected_repo,
)
from metagit.core.tui.runner import CommandRunResult, MetagitCommandRunner
from metagit.core.tui.wizard import ConfigWizardService


class BackScreen(Screen):
    """Screen that supports ESC / Back to return to the previous view."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back", priority=True),
    ]

    def action_pop_screen(self) -> None:
        self.app.pop_screen()


class OutputScreen(BackScreen):
    """Display captured CLI output."""

    BINDINGS = [
        *BackScreen.BINDINGS,
        Binding("q", "pop_screen", "Back"),
    ]

    def __init__(self, title: str, result: CommandRunResult) -> None:
        super().__init__()
        self._title = title
        self._result = result

    def compose(self) -> ComposeResult:
        status = "OK" if self._result.ok else f"exit {self._result.returncode}"
        body = self._result.stdout.strip() or self._result.stderr.strip() or "(no output)"
        yield Header(show_clock=False)
        yield Static(f"[bold]{self._title}[/bold] — {status}", id="output_title")
        yield Static(" ".join(self._result.argv), id="output_cmd")
        with VerticalScroll():
            yield Static(body, id="output_body")
        yield Footer()


class MessageScreen(BackScreen):
    """Simple status / error message screen."""

    BINDINGS = [
        *BackScreen.BINDINGS,
        Binding("q", "pop_screen", "Back"),
        Binding("enter", "pop_screen", "Back"),
    ]

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"[bold]{self._title}[/bold]")
        yield Static(self._body)
        yield Footer()


class PromptScreen(BackScreen):
    """Collect prompt values before launching a command."""

    BINDINGS = [
        *BackScreen.BINDINGS,
        Binding("q", "cancel", "Cancel", priority=True),
    ]

    def __init__(
        self,
        action: TuiCommandAction,
        on_submit: Callable[[dict[str, str]], None],
    ) -> None:
        super().__init__()
        self._action = action
        self._on_submit = on_submit

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"[bold]{self._action.label}[/bold]")
        yield Static(self._action.description)
        for field in self._action.prompt_fields:
            yield Label(field)
            yield Input(placeholder=field, id=f"field-{field}")
        with Horizontal():
            yield Button("Run", variant="primary", id="run_btn")
            yield Button("Cancel", id="cancel_btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.action_cancel()
            return
        values: dict[str, str] = {}
        for field in self._action.prompt_fields:
            widget = self.query_one(f"#field-{field}", Input)
            values[field] = widget.value.strip()
        self._on_submit(values)
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class WizardScreen(BackScreen):
    """Step through app configuration fields and save metagit.config.yaml."""

    def __init__(self, wizard: ConfigWizardService) -> None:
        super().__init__()
        self._wizard = wizard
        self._answers = wizard.default_answers()
        self._project_choices = wizard.project_choices()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("[bold]Configuration wizard[/bold]")
        yield Static("Set workspace and UI defaults for metagit.config.yaml")
        yield Label("Editor command")
        yield Input(value=self._answers.editor, id="editor")
        yield Label("Workspace path")
        yield Input(value=self._answers.workspace_path, id="workspace_path")
        yield Label("Default project (optional)")
        default_project = self._answers.default_project or ""
        yield Input(value=default_project, id="default_project")
        if self._project_choices:
            yield Static(f"Manifest projects: {', '.join(self._project_choices)}")
        yield Label("Menu length")
        yield Input(value=str(self._answers.ui_menu_length), id="ui_menu_length")
        with Horizontal():
            yield Button("Save configuration", variant="primary", id="save_btn")
            yield Button("Back", id="back_btn")
        yield Static("", id="wizard_status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_btn":
            self.action_pop_screen()
            return
        answers = WizardAnswers(
            editor=self.query_one("#editor", Input).value.strip() or "code",
            workspace_path=self.query_one("#workspace_path", Input).value.strip() or "./.metagit",
            default_project=self.query_one("#default_project", Input).value.strip() or None,
            ui_show_preview=True,
            ui_menu_length=max(1, int(self.query_one("#ui_menu_length", Input).value.strip() or "10")),
            ui_ignore_hidden=True,
        )
        result = self._wizard.apply(answers)
        status = self.query_one("#wizard_status", Static)
        if isinstance(result, Exception):
            status.update(f"[red]Save failed:[/red] {result}")
            return
        status.update(f"[green]Saved[/green] editor={result.editor} workspace.path={result.workspace.path}")


class RepoSelectScreen(BackScreen):
    """Choose a repository within a workspace project and open the editor."""

    BINDINGS = [
        *BackScreen.BINDINGS,
        Binding("q", "pop_screen", "Back"),
    ]

    def __init__(
        self,
        *,
        app_config_path: str,
        manifest_path: str,
        project_name: str,
    ) -> None:
        super().__init__()
        self._app_config_path = app_config_path
        self._manifest_path = manifest_path
        self._project_name = project_name
        repos = list_manifest_repos(manifest_path, project_name)
        self._repos: list[str] = [] if isinstance(repos, Exception) else list(repos)
        self._load_error = repos if isinstance(repos, Exception) else None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"[bold]Select repository[/bold] — project [cyan]{self._project_name}[/cyan]")
        yield Static("Enter to open in editor · Esc to go back")
        if self._load_error is not None:
            yield Static(f"[red]{self._load_error}[/red]")
        elif not self._repos:
            yield Static("[yellow]No repositories in this project.[/yellow]")
        else:
            items = [ListItem(Label(name)) for name in self._repos]
            yield ListView(*items, id="repo_list")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "repo_list":
            return
        index = event.list_view.index
        if index is None or index >= len(self._repos):
            return
        repo_name = self._repos[index]
        result = open_selected_repo(
            app_config_path=self._app_config_path,
            manifest_path=self._manifest_path,
            project_name=self._project_name,
            repo_name=repo_name,
        )
        if isinstance(result, Exception):
            self.app.push_screen(MessageScreen("Open failed", str(result)))
            return
        self.app.push_screen(
            MessageScreen(
                "Opened repository",
                f"{result.project}/{result.repo}\n{result.path}",
            ),
        )


class ProjectSelectScreen(BackScreen):
    """Choose a workspace project, then continue to repository selection."""

    BINDINGS = [
        *BackScreen.BINDINGS,
        Binding("q", "pop_screen", "Back"),
    ]

    def __init__(
        self,
        *,
        app_config_path: str,
        manifest_path: Optional[str],
    ) -> None:
        super().__init__()
        self._app_config_path = app_config_path
        self._manifest_path = manifest_path
        self._projects: list[str] = []
        self._load_error: Exception | None = None
        if not manifest_path:
            self._load_error = ValueError(
                "No .metagit.yml found. Run from a workspace root or pass --manifest.",
            )
        else:
            loaded = list_manifest_projects(manifest_path)
            if isinstance(loaded, Exception):
                self._load_error = loaded
            else:
                self._projects = list(loaded)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("[bold]Select project[/bold]")
        yield Static("Enter a project, then pick a repository · Esc to go back")
        if self._load_error is not None:
            yield Static(f"[red]{self._load_error}[/red]")
        elif not self._projects:
            yield Static("[yellow]No workspace projects in .metagit.yml.[/yellow]")
        else:
            items = [ListItem(Label(name)) for name in self._projects]
            yield ListView(*items, id="project_list")
        yield Footer()

    def on_mount(self) -> None:
        if self._load_error is not None or not self._manifest_path:
            return
        sole = maybe_single_project(self._projects)
        if sole is None:
            return
        # Single-project umbrellas skip straight to repo selection.
        self.app.push_screen(
            RepoSelectScreen(
                app_config_path=self._app_config_path,
                manifest_path=self._manifest_path,
                project_name=sole,
            ),
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "project_list" or not self._manifest_path:
            return
        index = event.list_view.index
        if index is None or index >= len(self._projects):
            return
        self.app.push_screen(
            RepoSelectScreen(
                app_config_path=self._app_config_path,
                manifest_path=self._manifest_path,
                project_name=self._projects[index],
            ),
        )


class CommandBrowserScreen(BackScreen):
    """Browse and run commands from one catalog section."""

    BINDINGS = [
        *BackScreen.BINDINGS,
        Binding("q", "pop_screen", "Back"),
    ]

    def __init__(self, section: TuiMenuSection, runner: MetagitCommandRunner) -> None:
        super().__init__()
        self._section = section
        self._runner = runner

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"[bold]{self._section.title}[/bold]")
        yield Static("Enter to run · Esc to go back")
        items = [ListItem(Label(f"{action.label} — {action.description}")) for action in self._section.actions]
        yield ListView(*items, id="command_list")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "command_list":
            return
        index = event.list_view.index
        if index is None or index >= len(self._section.actions):
            return
        action = self._section.actions[index]
        self._launch_action(action)

    def _launch_action(self, action: TuiCommandAction) -> None:
        if action.prompt_fields:
            self.app.push_screen(
                PromptScreen(action, on_submit=lambda values: self._run_action(action, values)),
            )
            return
        self._run_action(action, {})

    def _run_action(self, action: TuiCommandAction, values: dict[str, str]) -> None:
        extra: list[str] = []
        if "query" in values and values["query"]:
            extra.append(values["query"])
        if action.id.endswith("grep"):
            extra.append("--json")
        if action.interactive:
            run_interactive_catalog_action(
                self.app,
                action=action,
                runner=self._runner,
                app_config_path=self._runner.app_config_path,
                manifest_path=self._runner.manifest_path,
                extra_args=extra or None,
            )
            return
        result = self._runner.run_action(action, extra_args=extra or None)
        self.app.push_screen(OutputScreen(action.label, result))


class MetagitTuiApp(App):
    """Top-level Metagit TUI hub."""

    CSS = """
  #home_list {
    height: 1fr;
    border: solid $primary;
  }
  #home_hint {
    height: auto;
    padding: 1 2;
  }
  """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        *,
        app_config_path: str,
        manifest_path: Optional[str] = None,
        cwd: Optional[str] = None,
        start_wizard: bool = False,
    ) -> None:
        super().__init__()
        self._app_config_path = app_config_path
        self._manifest_path = manifest_path
        self._cwd = cwd or str(Path.cwd())
        self._start_wizard = start_wizard
        self._sections = build_command_catalog()
        self._runner = MetagitCommandRunner(
            cwd=self._cwd,
            app_config_path=app_config_path,
            manifest_path=manifest_path,
        )
        self._wizard = ConfigWizardService(
            app_config_path=app_config_path,
            manifest_path=manifest_path,
        )

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        manifest_line = self._manifest_path or "(none detected)"
        yield Static(
            f"[bold]Metagit[/bold] interactive hub\nApp config: {self._app_config_path}\nManifest: {manifest_line}",
            id="home_hint",
        )
        yield Static("Enter to choose · q / Ctrl+C to quit")
        items = [
            ListItem(Label("Select project → repository")),
            ListItem(Label("Configuration wizard — set editor, workspace path, defaults")),
            ListItem(Label("Fuzzy repo picker (legacy)")),
        ]
        for section in self._sections:
            items.append(ListItem(Label(f"{section.title} commands")))
        items.append(ListItem(Label("Quit")))
        yield ListView(*items, id="home_list")
        yield Footer()

    def on_mount(self) -> None:
        if self._start_wizard:
            self.push_screen(WizardScreen(self._wizard))

    def action_quit(self) -> None:
        """Exit the hub without raising after terminal restore."""
        self.exit(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "home_list":
            return
        index = event.list_view.index
        if index is None:
            return
        if index == 0:
            self.push_screen(
                ProjectSelectScreen(
                    app_config_path=self._app_config_path,
                    manifest_path=self._manifest_path,
                ),
            )
            return
        if index == 1:
            self.push_screen(WizardScreen(self._wizard))
            return
        if index == 2:
            action = next(item for item in flatten_actions(self._sections) if item.id == "workspace-select")
            run_interactive_catalog_action(
                self,
                action=action,
                runner=self._runner,
                app_config_path=self._app_config_path,
                manifest_path=self._manifest_path,
            )
            return
        section_count = len(self._sections)
        if 3 <= index < 3 + section_count:
            section = self._sections[index - 3]
            self.push_screen(CommandBrowserScreen(section, self._runner))
            return
        if index == 3 + section_count:
            self.action_quit()


def run_tui(
    *,
    app_config_path: str,
    manifest_path: Optional[str] = None,
    cwd: Optional[str] = None,
    start_wizard: bool = False,
) -> None:
    """Launch the Metagit TUI application."""
    app = MetagitTuiApp(
        app_config_path=app_config_path,
        manifest_path=manifest_path,
        cwd=cwd,
        start_wizard=start_wizard,
    )
    try:
        app.run()
    except KeyboardInterrupt:
        # Ctrl+C during driver teardown should not surface as a CLI traceback.
        return
