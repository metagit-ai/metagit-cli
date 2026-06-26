#!/usr/bin/env python
"""
Apply planned workspace layout filesystem steps.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from metagit.core.utils.common import create_vscode_workspace
from metagit.core.workspace.layout_models import LayoutPlan, LayoutStep


def apply_plan(plan: LayoutPlan, *, dry_run: bool) -> list[LayoutStep]:
    """Execute disk steps from a layout plan."""
    applied: list[LayoutStep] = []
    for step in plan.disk_steps:
        if dry_run:
            applied.append(step.model_copy())
            continue
        result = _apply_step(step)
        applied.append(result)
        if result.action != "noop" and not result.applied and result.detail:
            raise LayoutExecutionError(result.detail)
    return applied


class LayoutExecutionError(Exception):
    """Raised when a layout step cannot be applied."""


def _apply_step(step: LayoutStep) -> LayoutStep:
    if step.action == "noop":
        return step.model_copy(update={"applied": True})
    if step.action == "mkdir":
        if step.target:
            Path(step.target).mkdir(parents=True, exist_ok=True)
        return step.model_copy(update={"applied": True})
    if step.action in {"rename", "move"}:
        return _apply_rename_or_move(step)
    if step.action == "unlink":
        return _apply_unlink(step)
    if step.action == "symlink":
        return _apply_symlink(step)
    if step.action == "regenerate_vscode":
        return _apply_vscode(step)
    if step.action == "migrate_session":
        return _apply_session(step)
    return step.model_copy(update={"applied": False, "detail": "unknown action"})


def _apply_rename_or_move(step: LayoutStep) -> LayoutStep:
    if not step.source or not step.target:
        return step.model_copy(update={"applied": False, "detail": "missing source or target"})
    source = Path(step.source)
    target = Path(step.target)
    if not source.exists():
        return step.model_copy(update={"applied": True, "detail": "source missing"})
    if target.exists():
        return step.model_copy(update={"applied": False, "detail": f"target already exists: {target}"})
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(source, target)
    except OSError:
        shutil.move(str(source), str(target))
    return step.model_copy(update={"applied": True})


def _apply_unlink(step: LayoutStep) -> LayoutStep:
    if not step.source:
        return step.model_copy(update={"applied": False, "detail": "missing source"})
    path = Path(step.source)
    if not path.exists() and not path.is_symlink():
        return step.model_copy(update={"applied": True, "detail": "already absent"})
    if path.is_symlink():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)
    return step.model_copy(update={"applied": True})


def _apply_symlink(step: LayoutStep) -> LayoutStep:
    if not step.source or not step.target:
        return step.model_copy(update={"applied": False, "detail": "missing source or target"})
    from metagit.core.workspace import workspace_dedupe

    mount = Path(step.target)
    target = Path(step.source)
    changed, error = workspace_dedupe.ensure_symlink(mount, target)
    if error:
        return step.model_copy(update={"applied": False, "detail": error})
    detail = "created symlink" if changed else "symlink already correct"
    return step.model_copy(update={"applied": True, "detail": detail})


def _apply_vscode(step: LayoutStep) -> LayoutStep:
    if not step.source or not step.target:
        return step.model_copy(update={"applied": False, "detail": "missing project dir or name"})
    project_dir = Path(step.source)
    project_name = step.target
    repo_names = [
        entry.name
        for entry in project_dir.iterdir()
        if entry.name != "workspace.code-workspace" and (entry.is_dir() or entry.is_symlink())
    ]
    if not repo_names:
        return step.model_copy(update={"applied": True, "detail": "no repos to index"})
    content = create_vscode_workspace(project_name, repo_names)
    if isinstance(content, Exception):
        return step.model_copy(update={"applied": False, "detail": str(content)})
    out_path = project_dir / "workspace.code-workspace"
    out_path.write_text(content, encoding="utf-8")
    return step.model_copy(update={"applied": True})


def _apply_session(step: LayoutStep) -> LayoutStep:
    if not step.source or not step.target:
        return step.model_copy(update={"applied": False, "detail": "missing session paths"})
    source = Path(step.source)
    target = Path(step.target)
    if not source.is_file():
        return step.model_copy(update={"applied": True, "detail": "no session file"})
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    os.rename(source, target)
    return step.model_copy(update={"applied": True})
