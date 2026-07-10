#!/usr/bin/env python
"""Opt-in command validators for RFC-0011 merge requests."""

from __future__ import annotations

import subprocess

from metagit.core.merge.models import MergeValidation, MergeValidationCommand


def run_validators(repo_path: str, commands: list[str]) -> MergeValidation:
    """Run validator command strings in ``repo_path`` via the platform shell.

    Uses ``shell=True`` so Unix CI hosts run ``/bin/sh`` and Windows hosts use
    ``ComSpec`` (typically ``cmd.exe``). Validator strings must be valid for the
    host shell (quote paths with spaces accordingly).
    """
    results: list[MergeValidationCommand] = []
    for command in commands:
        try:
            completed = subprocess.run(  # nosec B602 — intentional platform shell for opt-in validator strings
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                shell=True,
            )
        except OSError as exc:
            results.append(
                MergeValidationCommand(
                    cmd=command,
                    exit_code=127,
                    stdout="",
                    stderr=str(exc),
                )
            )
            return MergeValidation(ok=False, commands=results)
        results.append(
            MergeValidationCommand(
                cmd=command,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )
        if completed.returncode != 0:
            return MergeValidation(ok=False, commands=results)
    return MergeValidation(ok=True, commands=results)


def merge_validators_from_config(config: object | None) -> list[str]:
    """Extract configured merge validators from an app config object."""
    merge_config = getattr(config, "merge", None)
    validators = getattr(merge_config, "validators", None)
    if validators is None:
        return []
    return [item for item in validators if item.strip()]


__all__ = ["merge_validators_from_config", "run_validators"]
