#!/usr/bin/env python
"""Collect init template answers from defaults, files, and interactive prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import click

from metagit.core.init.models import InitPromptSpec, InitTemplateManifest
from metagit.core.utils.yaml_class import yaml

PromptFn = Callable[..., str]


def load_answers_file(path: Path) -> dict[str, str]:
    """Load answers from a YAML or JSON mapping file."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        import json

        loaded = json.loads(text)
    else:
        loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError("answers file must be a mapping of variable names to values")
    return {str(key): "" if value is None else str(value) for key, value in loaded.items()}


def build_builtin_defaults(
    target_dir: Path,
    *,
    directory_name: str,
    git_remote_url: Optional[str],
) -> dict[str, str]:
    """Built-in default resolvers for template prompts."""
    _ = target_dir
    return {
        "directory_name": directory_name,
        "git_remote_url": git_remote_url or "",
    }


def resolve_prompt_default(
    prompt: InitPromptSpec,
    builtins: dict[str, str],
) -> str:
    """Resolve the default value for one prompt spec."""
    if prompt.default is not None:
        return prompt.default
    if prompt.default_from:
        return builtins.get(prompt.default_from, "")
    return ""


def collect_answers(
    manifest: InitTemplateManifest,
    *,
    target_dir: Path,
    directory_name: str,
    git_remote_url: Optional[str],
    answers: Optional[dict[str, str]] = None,
    overrides: Optional[dict[str, str]] = None,
    no_prompt: bool = False,
    prompt_fn: Optional[PromptFn] = None,
) -> dict[str, str]:
    """
    Merge answers file, overrides, and interactive prompts.

    Raises click.UsageError when required values are missing in no_prompt mode.
    """
    merged: dict[str, str] = {}
    if answers:
        merged.update(answers)
    if overrides:
        merged.update({key: value for key, value in overrides.items() if value is not None})

    builtins = build_builtin_defaults(
        target_dir,
        directory_name=directory_name,
        git_remote_url=git_remote_url,
    )
    ask = prompt_fn or click.prompt

    for prompt in manifest.prompts:
        if prompt.name in merged and merged[prompt.name] != "":
            continue
        default = resolve_prompt_default(prompt, builtins)
        if no_prompt:
            if prompt.required and not default:
                raise click.UsageError(
                    f"Missing required init answer {prompt.name!r} (provide --answers-file or drop --no-prompt)"
                )
            merged[prompt.name] = default
            continue
        value = ask(
            prompt.label,
            default=default or None,
            hide_input=prompt.secret,
            show_default=True,
        )
        merged[prompt.name] = str(value).strip()

    for prompt in manifest.prompts:
        if prompt.required and not merged.get(prompt.name):
            raise click.UsageError(f"Required init answer {prompt.name!r} is empty")

    merged.setdefault("kind", manifest.kind)
    return merged
