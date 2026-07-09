#!/usr/bin/env python
"""Opt-in command validators for RFC-0011 merge requests."""

from __future__ import annotations

import subprocess

from metagit.core.merge.models import MergeValidation, MergeValidationCommand


def run_validators(repo_path: str, commands: list[str]) -> MergeValidation:
    """Run validator commands in ``repo_path`` using zsh and capture results."""
    results: list[MergeValidationCommand] = []
    for command in commands:
        completed = subprocess.run(
            ["/bin/zsh", "-c", command],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
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
