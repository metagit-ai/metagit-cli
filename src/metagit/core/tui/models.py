#!/usr/bin/env python
"""Pydantic models for the Metagit TUI command catalog."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ManifestPlacement = Literal["after_group", "after_subcommand", "after_args"]


class TuiCommandAction(BaseModel):
    """A CLI command the TUI can launch with optional prompt fields."""

    id: str
    label: str
    description: str
    argv: list[str] = Field(default_factory=list)
    prompt_fields: list[str] = Field(default_factory=list)
    manifest_option: Optional[str] = None
    manifest_placement: ManifestPlacement = "after_group"
    interactive: bool = Field(
        default=False,
        description="When true, run with terminal control (not captured subprocess output)",
    )


class TuiMenuSection(BaseModel):
    """Grouped menu entries shown in the main TUI browser."""

    id: str
    title: str
    actions: list[TuiCommandAction]


class WizardAnswers(BaseModel):
    """Collected answers for the app configuration wizard."""

    editor: str = "code"
    workspace_path: str = "./.metagit"
    default_project: Optional[str] = None
    ui_show_preview: bool = True
    ui_menu_length: int = 10
    ui_ignore_hidden: bool = True
