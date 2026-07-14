#!/usr/bin/env python
"""Helpers for launching interactive catalog actions from the TUI hub."""

from __future__ import annotations

from typing import Optional

from textual.app import App, SuspendNotSupported

from metagit.core.tui.models import TuiCommandAction
from metagit.core.tui.repo_picker import run_repo_picker_session
from metagit.core.tui.runner import MetagitCommandRunner


def run_interactive_catalog_action(
    app: App,
    *,
    action: TuiCommandAction,
    runner: MetagitCommandRunner,
    app_config_path: str,
    manifest_path: Optional[str],
    extra_args: Optional[list[str]] = None,
) -> None:
    """
    Release terminal control and run an interactive workflow.

    The hub must suspend while nested Textual apps (repo picker) or inherited-
    stdio subprocesses run, otherwise they hang waiting for a TTY.
    """
    try:
        with app.suspend():
            if action.id == "workspace-select":
                run_repo_picker_session(
                    app_config_path=app_config_path,
                    manifest_path=manifest_path,
                )
                return
            runner.run_interactive(action, extra_args=extra_args)
    except SuspendNotSupported:
        # Headless / unsupported drivers should not dump a traceback on the hub.
        app.notify(
            "Interactive terminal suspend is unavailable in this environment.",
            severity="warning",
            timeout=4,
        )
    except Exception as exc:
        app.notify(f"Interactive action failed: {exc}", severity="error", timeout=6)
