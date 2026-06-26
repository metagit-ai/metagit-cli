#!/usr/bin/env python
"""Detect how the running Metagit package was installed."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution

from metagit.core.release.models import InstallMethod

_PACKAGE_NAME = "metagit-cli"
_UV_TOOL_MARKER = os.path.join("uv", "tools", _PACKAGE_NAME)


def detect_install_method() -> InstallMethod:
    """Return the best-effort install channel for the running package."""
    if _is_editable_install():
        return "editable"
    if _is_uv_tool_install():
        return "uv_tool"
    if _package_is_installed():
        return "pip"
    return "unknown"


def build_upgrade_command(method: InstallMethod) -> str:
    """Return the package-manager command for upgrading Metagit."""
    if method == "uv_tool":
        return "uv tool upgrade metagit-cli"
    if method == "pip":
        return f"{sys.executable} -m pip install -U {_PACKAGE_NAME}"
    if method == "editable":
        return "git pull && uv pip install -e ."
    return "uv tool install -U metagit-cli"


def _package_is_installed() -> bool:
    try:
        distribution(_PACKAGE_NAME)
    except PackageNotFoundError:
        return False
    return True


def _is_editable_install() -> bool:
    try:
        dist = distribution(_PACKAGE_NAME)
    except PackageNotFoundError:
        return False
    for path in dist.files or []:
        if path.name != "direct_url.json":
            continue
        raw = dist.locate_file(path).read_text(encoding="utf-8")
        payload = json.loads(raw)
        dir_info = payload.get("dir_info")
        if isinstance(dir_info, dict) and dir_info.get("editable"):
            return True
    return False


def _is_uv_tool_install() -> bool:
    executable = os.path.realpath(sys.executable)
    if _UV_TOOL_MARKER in executable.replace("\\", "/"):
        return True
    uv_bin = shutil.which("uv")
    if uv_bin is None:
        return False
    try:
        completed = subprocess.run(
            [uv_bin, "tool", "list"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode != 0:
        return False
    return any(line.strip().lower().startswith(f"{_PACKAGE_NAME} ") for line in completed.stdout.splitlines())
