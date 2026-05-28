#!/usr/bin/env python
"""Shell tab-completion helpers and install utilities for the Metagit CLI."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

import click
from click.shell_completion import (
    BashComplete,
    CompletionItem,
    FishComplete,
    ShellComplete,
    ZshComplete,
)

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.repomix_profile_service import RepomixProfileService

SUPPORTED_SHELLS = ("zsh", "bash", "fish")
_COMPLETION_ENV = "_METAGIT_COMPLETE"
_DEFINITION_PARAM_KEYS = (
    "definition_path",
    "definition",
    "config",
)


def _definition_path_from_ctx(ctx: click.Context) -> Path:
    """Best-effort manifest path from the current Click context."""
    params = ctx.params or {}
    for key in _DEFINITION_PARAM_KEYS:
        raw = params.get(key)
        if isinstance(raw, str) and raw.strip():
            return Path(raw).expanduser()
    parent = ctx.parent
    while parent is not None:
        params = parent.params or {}
        for key in _DEFINITION_PARAM_KEYS:
            raw = params.get(key)
            if isinstance(raw, str) and raw.strip():
                return Path(raw).expanduser()
        parent = parent.parent
    return Path(".metagit.yml")


def _project_names_from_manifest(definition_path: Path) -> list[str]:
    if not definition_path.is_file():
        return []
    manager = MetagitConfigManager(str(definition_path))
    loaded = manager.load_config()
    if isinstance(loaded, Exception) or not loaded.workspace:
        return []
    return sorted(
        {project.name for project in loaded.workspace.projects if project.name}
    )


def _repo_names_from_manifest(
    definition_path: Path,
    *,
    project_name: Optional[str],
) -> list[str]:
    if not definition_path.is_file():
        return []
    manager = MetagitConfigManager(str(definition_path))
    loaded = manager.load_config()
    if isinstance(loaded, Exception) or not loaded.workspace:
        return []
    names: list[str] = []
    for project in loaded.workspace.projects:
        if project_name and project.name != project_name:
            continue
        for repo in project.repos:
            if repo.name:
                names.append(repo.name)
    return sorted(set(names))


def _filter_incomplete(values: Iterable[str], incomplete: str) -> list[CompletionItem]:
    prefix = incomplete or ""
    return [CompletionItem(value) for value in values if value.startswith(prefix)]


def complete_projects(
    ctx: click.Context,
    _param: click.Parameter,
    incomplete: str,
) -> list[CompletionItem]:
    """Complete workspace project names from the active manifest."""
    definition_path = _definition_path_from_ctx(ctx)
    return _filter_incomplete(_project_names_from_manifest(definition_path), incomplete)


def complete_repos(
    ctx: click.Context,
    _param: click.Parameter,
    incomplete: str,
) -> list[CompletionItem]:
    """Complete repository names, optionally scoped to ``--project``."""
    definition_path = _definition_path_from_ctx(ctx)
    params = ctx.params or {}
    project_name = params.get("project_name") or params.get("project")
    if not isinstance(project_name, str) or not project_name.strip():
        parent = ctx.parent
        while parent is not None:
            parent_params = parent.params or {}
            candidate = parent_params.get("project")
            if isinstance(candidate, str) and candidate.strip():
                project_name = candidate
                break
            parent = parent.parent
    project_key = project_name.strip() if isinstance(project_name, str) else None
    repos = _repo_names_from_manifest(definition_path, project_name=project_key)
    return _filter_incomplete(repos, incomplete)


def complete_repomix_profiles(
    _ctx: click.Context,
    _param: click.Parameter,
    incomplete: str,
) -> list[CompletionItem]:
    """Complete bundled repomix context profile names."""
    try:
        names = RepomixProfileService().profile_names()
    except (FileNotFoundError, ValueError, KeyError):
        names = []
    return _filter_incomplete(names, incomplete)


def _completion_class(shell: str) -> type[ShellComplete]:
    mapping = {
        "zsh": ZshComplete,
        "bash": BashComplete,
        "fish": FishComplete,
    }
    key = shell.strip().lower()
    if key not in mapping:
        supported = ", ".join(SUPPORTED_SHELLS)
        raise click.ClickException(
            f"Unsupported shell {shell!r}; expected one of: {supported}"
        )
    return mapping[key]


def render_completion_script(
    cli: click.Command,
    *,
    shell_name: str,
    prog_name: str = "metagit",
) -> str:
    """Return a shell completion script for ``cli``."""
    shell_class = _completion_class(shell_name)
    comp = shell_class(cli, {}, prog_name, _COMPLETION_ENV)
    return comp.source()


def default_install_path(shell_name: str) -> Path:
    """Return the conventional user-level completion install path."""
    home = Path.home()
    key = shell_name.strip().lower()
    if key == "zsh":
        zdot = os.environ.get("ZDOTDIR")
        base = Path(zdot).expanduser() if zdot else home
        return base / ".zfunc" / "_metagit"
    if key == "bash":
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return (
                Path(xdg).expanduser() / "bash-completion" / "completions" / "metagit"
            )
        return home / ".local" / "share" / "bash-completion" / "completions" / "metagit"
    if key == "fish":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        config_home = Path(xdg).expanduser() if xdg else home / ".config"
        return config_home / "fish" / "completions" / "metagit.fish"
    supported = ", ".join(SUPPORTED_SHELLS)
    raise click.ClickException(
        f"Unsupported shell {shell_name!r}; expected one of: {supported}"
    )


def install_completion_script(
    script: str,
    *,
    shell_name: str,
    destination: Path,
) -> Path:
    """Write ``script`` to ``destination`` and return the resolved path."""
    resolved = destination.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(script, encoding="utf-8")
    if shell_name.strip().lower() == "zsh":
        try:
            os.chmod(resolved, 0o644)
        except OSError:
            pass
    return resolved


def shell_activation_hint(shell_name: str, *, prog_name: str = "metagit") -> str:
    """One-line eval/source hint when a file install is not used."""
    key = shell_name.strip().lower()
    if key == "fish":
        return (
            f"mkdir -p ~/.config/fish/completions && "
            f"{_COMPLETION_ENV}=fish_source {prog_name} "
            f"> ~/.config/fish/completions/{prog_name}.fish"
        )
    env = f"{_COMPLETION_ENV}={key}_source"
    return f'eval "$({env} {prog_name})"'


def metagit_executable() -> str:
    """Resolve the ``metagit`` binary used for completion callbacks."""
    override = os.environ.get("METAGIT_COMPLETION_EXECUTABLE")
    if override:
        return override
    discovered = shutil.which("metagit")
    if discovered:
        return discovered
    scripts_dir = Path(sys.executable).resolve().parent
    for candidate_name in ("metagit.exe", "metagit"):
        candidate = scripts_dir / candidate_name
        if candidate.is_file():
            return str(candidate)
    return "metagit"


def verify_completion_callback(prog_name: str = "metagit") -> tuple[bool, str]:
    """Check that completion env invocation returns a non-empty script."""
    executable = metagit_executable()
    env = os.environ.copy()
    env[_COMPLETION_ENV] = "zsh_source"
    try:
        completed = subprocess.run(
            [executable],
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, f"{executable} not runnable: {exc}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return False, detail or f"{executable} exited {completed.returncode}"
    if "#compdef" not in completed.stdout and "_completion" not in completed.stdout:
        return False, "completion callback produced unexpected output"
    return True, executable


def format_install_message(shell_name: str, path: Path) -> str:
    """Human instructions after writing a completion file."""
    key = shell_name.strip().lower()
    if key == "zsh":
        return (
            f"Installed zsh completion: {path}\n"
            f"Ensure fpath includes {path.parent} before compinit, e.g.:\n"
            f"  fpath=({shlex.quote(str(path.parent))} $fpath)\n"
            f"  autoload -Uz compinit && compinit"
        )
    if key == "bash":
        return (
            f"Installed bash completion: {path}\n"
            "Restart your shell or source the file to activate."
        )
    return (
        f"Installed fish completion: {path}\n"
        "Restart fish or run: source ~/.config/fish/config.fish"
    )


__all__ = [
    "SUPPORTED_SHELLS",
    "complete_projects",
    "complete_repos",
    "complete_repomix_profiles",
    "default_install_path",
    "format_install_message",
    "install_completion_script",
    "render_completion_script",
    "shell_activation_hint",
    "verify_completion_callback",
]
