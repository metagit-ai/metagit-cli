#!/usr/bin/env python
"""Resolve user-level and local AppConfig file locations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def user_config_home() -> Path:
    """Return the XDG config home, defaulting to ``~/.config``."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg).expanduser() if xdg else Path.home() / ".config"


def user_appconfig_paths() -> list[Path]:
    """Candidate user-level AppConfig files, preferred first."""
    base = user_config_home() / "metagit"
    return [base / "config.yml", base / "config.yaml"]


def default_user_appconfig_path() -> str:
    """Canonical user AppConfig path, even when the file does not exist yet."""
    existing = first_existing_user_appconfig()
    if existing is not None:
        return str(existing)
    return str(user_appconfig_paths()[0])


def first_existing_user_appconfig() -> Optional[Path]:
    """Return the first existing user-level AppConfig file, if any."""
    for candidate in user_appconfig_paths():
        if candidate.is_file():
            return candidate
    return None


def local_appconfig_paths(directory: Path) -> list[Path]:
    """Project-local AppConfig filenames next to a cwd or manifest."""
    return [
        directory / "metagit.config.yaml",
        directory / "metagit.config.yml",
    ]
