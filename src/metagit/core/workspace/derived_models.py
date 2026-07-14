#!/usr/bin/env python
"""Result models for derived workspace project operations."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from metagit.core.workspace.catalog_models import CatalogError


class DerivedMutationResult(BaseModel):
    """Result of derived project create/refresh/include/exclude."""

    ok: bool = True
    error: Optional[CatalogError] = None
    operation: str = "create"
    project_name: str = ""
    repo_names: list[str] = Field(default_factory=list)
    config_path: str = ""
    data: Optional[dict[str, Any]] = None
