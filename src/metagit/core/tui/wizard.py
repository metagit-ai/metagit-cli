#!/usr/bin/env python
"""App configuration wizard logic for the Metagit TUI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from metagit.core.appconfig import load_config, save_config
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.tui.models import WizardAnswers


class ConfigWizardService:
    """Apply wizard answers to metagit.config.yaml."""

    def __init__(self, *, app_config_path: str, manifest_path: Optional[str] = None) -> None:
        self._app_config_path = Path(app_config_path).expanduser()
        self._manifest_path = Path(manifest_path).expanduser() if manifest_path else None

    def load_existing(self) -> AppConfig:
        """Load current app config or defaults when the file is missing."""
        if not self._app_config_path.is_file():
            return AppConfig()
        loaded = load_config(str(self._app_config_path))
        if isinstance(loaded, Exception):
            return AppConfig()
        return loaded

    def project_choices(self) -> list[str]:
        """Return manifest project names when a workspace manifest is present."""
        if self._manifest_path is None or not self._manifest_path.is_file():
            return []
        manager = MetagitConfigManager(str(self._manifest_path))
        loaded = manager.load_config()
        if isinstance(loaded, Exception) or not loaded.workspace:
            return []
        return sorted({project.name for project in loaded.workspace.projects if project.name})

    def default_answers(self) -> WizardAnswers:
        """Seed wizard fields from the active config and environment."""
        config = self.load_existing()
        editor = os.environ.get("EDITOR") or config.editor or "code"
        return WizardAnswers(
            editor=editor,
            workspace_path=config.workspace.path or "./.metagit",
            default_project=config.workspace.default_project,
            ui_show_preview=bool(config.workspace.ui_show_preview),
            ui_menu_length=int(config.workspace.ui_menu_length or 10),
            ui_ignore_hidden=bool(config.workspace.ui_ignore_hidden),
        )

    def apply(self, answers: WizardAnswers) -> Union[AppConfig, Exception]:
        """Merge wizard answers and persist metagit.config.yaml."""
        try:
            config = self.load_existing()
            config.editor = answers.editor.strip() or config.editor
            config.workspace.path = answers.workspace_path.strip() or config.workspace.path
            config.workspace.default_project = answers.default_project or None
            config.workspace.ui_show_preview = answers.ui_show_preview
            config.workspace.ui_menu_length = answers.ui_menu_length
            config.workspace.ui_ignore_hidden = answers.ui_ignore_hidden
            self._app_config_path.parent.mkdir(parents=True, exist_ok=True)
            saved = save_config(str(self._app_config_path), config)
            if isinstance(saved, Exception):
                return saved
            return config
        except Exception as exc:
            return exc
