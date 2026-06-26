#!/usr/bin/env python
"""Self-update Metagit via the detected package manager."""

from __future__ import annotations

import shlex
import subprocess
from typing import Protocol

from metagit.core.release.install_detect import (
    build_upgrade_command,
    detect_install_method,
)
from metagit.core.release.models import VersionUpgradeResult
from metagit.core.release.release_check_service import ReleaseCheckService

_UPGRADE_TIMEOUT_SECONDS = 300


class _Runner(Protocol):
    def __call__(
        self,
        command: list[str],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]: ...


def _default_runner(
    command: list[str],
    *,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


class VersionUpgradeService:
    """Check for updates and optionally upgrade the running install."""

    def __init__(
        self,
        *,
        check_service: ReleaseCheckService | None = None,
        runner: _Runner | None = None,
    ) -> None:
        self._check_service = check_service or ReleaseCheckService()
        self._runner = runner or _default_runner

    def upgrade(
        self,
        *,
        apply: bool = False,
        include_notes: bool = False,
    ) -> VersionUpgradeResult:
        """Plan or execute a self-update when a newer release is published."""
        check = self._check_service.check(include_notes=include_notes)
        method = detect_install_method()
        command = build_upgrade_command(method)
        dry_run = not apply

        if method == "editable":
            return VersionUpgradeResult(
                ok=False,
                dry_run=dry_run,
                install_method=method,
                command=command,
                check=check,
                error="editable_install",
                message=(
                    "Editable development installs cannot self-update. "
                    "Use git pull and reinstall from the repository root."
                ),
            )

        if not check.update_available:
            return VersionUpgradeResult(
                ok=True,
                dry_run=dry_run,
                skipped=True,
                install_method=method,
                command=command,
                check=check,
                message="Already on the latest published release.",
            )

        if dry_run:
            return VersionUpgradeResult(
                ok=True,
                dry_run=True,
                install_method=method,
                command=command,
                check=check,
                message=(f"Update available. Re-run with --apply to execute: {command}"),
            )

        argv = shlex.split(command)
        try:
            completed = self._runner(argv, timeout=_UPGRADE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return VersionUpgradeResult(
                ok=False,
                applied=True,
                dry_run=False,
                install_method=method,
                command=command,
                check=check,
                error="upgrade_timeout",
                message="Upgrade command timed out.",
            )
        except OSError as exc:
            return VersionUpgradeResult(
                ok=False,
                applied=True,
                dry_run=False,
                install_method=method,
                command=command,
                check=check,
                error="upgrade_failed",
                message=str(exc),
            )

        ok = completed.returncode == 0
        return VersionUpgradeResult(
            ok=ok,
            applied=True,
            dry_run=False,
            install_method=method,
            command=command,
            check=check,
            stdout=completed.stdout.strip() or None,
            stderr=completed.stderr.strip() or None,
            exit_code=completed.returncode,
            error=None if ok else "upgrade_failed",
            message=(
                "Upgrade completed. Re-run `metagit version` in a new shell to confirm."
                if ok
                else "Upgrade command failed."
            ),
        )
