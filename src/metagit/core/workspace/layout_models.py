#!/usr/bin/env python
"""
Pydantic models for workspace layout rename and move operations.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.workspace.catalog_models import CatalogError


class LayoutStep(BaseModel):
    """Single filesystem or auxiliary layout action."""

    action: Literal[
        "rename",
        "move",
        "symlink",
        "unlink",
        "mkdir",
        "regenerate_vscode",
        "migrate_session",
        "noop",
    ]
    source: Optional[str] = None
    target: Optional[str] = None
    detail: Optional[str] = None
    applied: bool = False


class LayoutPlan(BaseModel):
    """Planned manifest and disk changes before execution."""

    operation: Literal["rename_project", "rename_repo", "move_repo"] = "rename_project"
    dry_run: bool = False
    manifest_changes: list[str] = Field(default_factory=list)
    disk_steps: list[LayoutStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LayoutMutationResult(BaseModel):
    """Result of rename/move layout operations."""

    ok: bool = True
    error: Optional[CatalogError] = None
    entity: Literal["project", "repo"] = "project"
    operation: Literal["rename", "move"] = "rename"
    project_name: str = ""
    repo_name: Optional[str] = None
    from_project: Optional[str] = None
    to_project: Optional[str] = None
    config_path: str = ""
    data: Optional[dict[str, Any]] = None
