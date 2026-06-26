#!/usr/bin/env python
"""Run Metagit CLI subprocesses from the TUI."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from metagit.core.tui.models import ManifestPlacement, TuiCommandAction


@dataclass(frozen=True)
class CommandRunResult:
    """Captured output from a metagit subprocess."""

    argv: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _manifest_insert_index(placement: ManifestPlacement) -> Optional[int]:
    """Return argv index after which the manifest option pair is inserted."""
    if placement == "after_group":
        return 1
    if placement == "after_subcommand":
        return 2
    return None


class MetagitCommandRunner:
    """Invoke the metagit CLI in a subprocess with stable cwd/env."""

    def __init__(
        self,
        *,
        cwd: str,
        app_config_path: str,
        manifest_path: Optional[str] = None,
    ) -> None:
        self._cwd = cwd
        self._app_config_path = app_config_path
        self._manifest_path = manifest_path
        self._executable = shutil.which("metagit") or "metagit"

    @property
    def app_config_path(self) -> str:
        return self._app_config_path

    @property
    def manifest_path(self) -> Optional[str]:
        return self._manifest_path

    def build_argv(
        self,
        command_argv: list[str],
        *,
        manifest_option: Optional[str] = None,
        manifest_placement: ManifestPlacement = "after_group",
    ) -> list[str]:
        """Prefix global flags and inject the manifest option for the command group."""
        argv = [self._executable, "--config", self._app_config_path]
        if not command_argv:
            return argv

        insert_after = _manifest_insert_index(manifest_placement)
        if manifest_option and self._manifest_path and insert_after is not None:
            split_at = min(insert_after, len(command_argv))
            argv.extend(command_argv[:split_at])
            argv.extend([manifest_option, self._manifest_path])
            argv.extend(command_argv[split_at:])
            return argv

        argv.extend(command_argv)
        return argv

    def run_action(
        self,
        action: TuiCommandAction,
        *,
        extra_args: Optional[list[str]] = None,
    ) -> CommandRunResult:
        """Execute a catalog action and capture stdout/stderr."""
        placement = action.manifest_placement
        inline_manifest = action.manifest_option and placement != "after_args"
        argv = self.build_argv(
            action.argv,
            manifest_option=action.manifest_option if inline_manifest else None,
            manifest_placement=placement if inline_manifest else "after_group",
        )
        if extra_args:
            argv.extend(extra_args)
        if action.manifest_option and self._manifest_path and placement == "after_args":
            argv.extend([action.manifest_option, self._manifest_path])
        return self._execute(argv)

    def build_action_argv(
        self,
        action: TuiCommandAction,
        *,
        extra_args: Optional[list[str]] = None,
    ) -> list[str]:
        """Build a full argv for a catalog action without executing it."""
        placement = action.manifest_placement
        inline_manifest = action.manifest_option and placement != "after_args"
        argv = self.build_argv(
            action.argv,
            manifest_option=action.manifest_option if inline_manifest else None,
            manifest_placement=placement if inline_manifest else "after_group",
        )
        if extra_args:
            argv.extend(extra_args)
        if action.manifest_option and self._manifest_path and placement == "after_args":
            argv.extend([action.manifest_option, self._manifest_path])
        return argv

    def run_interactive(
        self,
        action: TuiCommandAction,
        *,
        extra_args: Optional[list[str]] = None,
    ) -> int:
        """Run a command with inherited stdio (for nested interactive CLIs)."""
        argv = self.build_action_argv(action, extra_args=extra_args)
        env = os.environ.copy()
        env.pop("METAGIT_AGENT_MODE", None)
        completed = subprocess.run(
            argv,
            cwd=self._cwd,
            env=env,
            check=False,
        )
        return completed.returncode

    def run(
        self,
        command_argv: list[str],
        *,
        manifest_option: Optional[str] = None,
        manifest_placement: ManifestPlacement = "after_group",
        extra_args: Optional[list[str]] = None,
    ) -> CommandRunResult:
        """Execute a metagit command argv tail and capture stdout/stderr."""
        inline_manifest = manifest_option and manifest_placement != "after_args"
        argv = self.build_argv(
            command_argv,
            manifest_option=manifest_option if inline_manifest else None,
            manifest_placement=manifest_placement if inline_manifest else "after_group",
        )
        if extra_args:
            argv.extend(extra_args)
        if manifest_option and self._manifest_path and manifest_placement == "after_args":
            argv.extend([manifest_option, self._manifest_path])
        return self._execute(argv)

    def _execute(self, argv: list[str]) -> CommandRunResult:
        env = os.environ.copy()
        env.pop("METAGIT_AGENT_MODE", None)
        completed = subprocess.run(
            argv,
            cwd=self._cwd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return CommandRunResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
