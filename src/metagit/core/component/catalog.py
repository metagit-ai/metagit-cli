#!/usr/bin/env python
"""Catalog native and adapter-mapped components from a MetagitConfig."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from metagit.core.component.identity import component_id
from metagit.core.component.models import Component
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.project.path_metadata import path_metadata_kwargs

CatalogSource = Literal["native", "path", "legacy_component"]


class ResolvedComponent(BaseModel):
    """A component with catalog identity and provenance."""

    model_config = ConfigDict(extra="forbid")

    project: str
    repo: str
    source: CatalogSource
    spec: Component

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def id(self) -> str:
        result = component_id(self.project, self.repo, self.spec.name)
        if isinstance(result, Exception):
            return f"{self.project}/{self.repo}/{self.spec.name}"
        return result


class ComponentCatalog:
    """List components from workspace repos and application adapter sources."""

    def list(self, config: MetagitConfig) -> list[ResolvedComponent]:
        rows: list[ResolvedComponent] = []
        if config.workspace is not None:
            for project in config.workspace.projects:
                for repo in project.repos:
                    for spec in repo.components:
                        rows.append(
                            ResolvedComponent(
                                project=project.name,
                                repo=repo.name,
                                source="native",
                                spec=spec,
                            )
                        )
        app_name = config.name
        for entry in config.paths or []:
            mapped = self._from_project_path(entry)
            if mapped is None:
                continue
            rows.append(
                ResolvedComponent(
                    project=app_name,
                    repo=app_name,
                    source="path",
                    spec=mapped,
                )
            )
        for entry in config.components or []:
            mapped = self._from_project_path(entry)
            if mapped is None:
                continue
            rows.append(
                ResolvedComponent(
                    project=app_name,
                    repo=app_name,
                    source="legacy_component",
                    spec=mapped,
                )
            )
        return rows

    def _from_project_path(self, entry: ProjectPath) -> Component | None:
        if not entry.path:
            return None
        metadata = path_metadata_kwargs(entry)
        return Component(name=entry.name, path=entry.path, **metadata)
