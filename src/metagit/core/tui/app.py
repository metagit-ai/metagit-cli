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
        Binding("ctrl+c", "quit", "Quit"),
        Binding("q", "quit", "Quit"),
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
        yield Static("Enter to choose · Esc does not quit from home")
        items = [
            ListItem(Label("Configuration wizard — set editor, workspace path, defaults")),
            ListItem(Label("Quick: select repository (picker)")),
        ]
        for section in self._sections:
            items.append(ListItem(Label(f"{section.title} commands")))
        items.append(ListItem(Label("Quit")))
        yield ListView(*items, id="home_list")
        yield Footer()

    def on_mount(self) -> None:
        if self._start_wizard:
            self.push_screen(WizardScreen(self._wizard))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "home_list":
            return
        index = event.list_view.index
        if index is None:
            return
        if index == 0:
            self.push_screen(WizardScreen(self._wizard))
            return
        if index == 1:
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
        if 2 <= index < 2 + section_count:
            section = self._sections[index - 2]
            self.push_screen(CommandBrowserScreen(section, self._runner))
            return
        if index == 2 + section_count:
            self.exit(None)


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
    app.run()
