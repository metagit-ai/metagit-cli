#!/usr/bin/env python
"""Static command catalog for the Metagit TUI."""

from __future__ import annotations

from metagit.core.tui.models import TuiCommandAction, TuiMenuSection


def build_command_catalog() -> list[TuiMenuSection]:
    """Return menu sections wrapping common CLI workflows."""
    return [
        TuiMenuSection(
            id="workspace",
            title="Workspace",
            actions=[
                TuiCommandAction(
                    id="workspace-list",
                    label="List workspace catalog",
                    description="Show projects and repositories from .metagit.yml",
                    argv=["workspace", "list", "--json"],
                    manifest_option="--config",
                    manifest_placement="after_group",
                ),
                TuiCommandAction(
                    id="workspace-sync",
                    label="Sync active project",
                    description="Clone or update repositories for the active project",
                    argv=["project", "sync"],
                    manifest_option="-c",
                    manifest_placement="after_group",
                ),
                TuiCommandAction(
                    id="workspace-select",
                    label="Select project → repository",
                    description="Choose a workspace project, then a repo, and open the editor",
                    argv=["project", "select"],
                    manifest_option="-c",
                    manifest_placement="after_group",
                    interactive=True,
                ),
                TuiCommandAction(
                    id="workspace-grep",
                    label="Search file contents",
                    description="Ripgrep across managed repositories",
                    argv=["workspace", "grep"],
                    prompt_fields=["query"],
                    manifest_option="--config",
                    manifest_placement="after_group",
                ),
            ],
        ),
        TuiMenuSection(
            id="config",
            title="Configuration",
            actions=[
                TuiCommandAction(
                    id="config-validate",
                    label="Validate .metagit.yml",
                    description="Run schema validation on the workspace manifest",
                    argv=["config", "validate"],
                    manifest_option="-c",
                    manifest_placement="after_group",
                ),
                TuiCommandAction(
                    id="appconfig-show",
                    label="Show app configuration",
                    description="Print metagit.config.yaml settings",
                    argv=["appconfig", "show"],
                ),
                TuiCommandAction(
                    id="appconfig-validate",
                    label="Validate app configuration",
                    description="Validate metagit.config.yaml",
                    argv=["appconfig", "validate"],
                ),
            ],
        ),
        TuiMenuSection(
            id="tools",
            title="Tools",
            actions=[
                TuiCommandAction(
                    id="search",
                    label="Search managed repos",
                    description="Manifest-aware repository search",
                    argv=["search"],
                    prompt_fields=["query"],
                    manifest_option="--definition",
                    manifest_placement="after_args",
                ),
                TuiCommandAction(
                    id="version-check",
                    label="Check for updates",
                    description="Compare installed version to PyPI/GitHub release",
                    argv=["version", "check", "--json"],
                ),
            ],
        ),
    ]


def flatten_actions(sections: list[TuiMenuSection]) -> list[TuiCommandAction]:
    """Return all actions in menu order."""
    actions: list[TuiCommandAction] = []
    for section in sections:
        actions.extend(section.actions)
    return actions
