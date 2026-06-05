#!/usr/bin/env python
"""Catalog assembly and validation for agent templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from metagit.core.agent.models import (
    AgentCatalogEntry,
    AgentCatalogEnvelope,
    AgentCatalogTaxonomy,
    AgentTemplateManifest,
)
from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.prompt.catalog import list_catalog as list_prompt_catalog


@dataclass
class AgentValidationIssue:
    """One validation failure for a template manifest."""

    template_id: str
    message: str
    path: str | None = None


@dataclass
class AgentCatalogService:
    """Build catalog envelopes and validate template manifests."""

    registry: AgentTemplateRegistry = field(default_factory=AgentTemplateRegistry)

    def list_catalog(
        self, *, manifest_root: Path | None = None
    ) -> AgentCatalogEnvelope:
        """Return sorted catalog entries with delegation index applied."""
        working_registry = (
            self.registry
            if manifest_root is None
            else AgentTemplateRegistry(manifest_root=manifest_root)
        )
        entries: list[AgentCatalogEntry] = []
        for template_id in working_registry.list_template_ids():
            manifest = working_registry.load_manifest(template_id)
            if manifest is None:
                continue
            source = working_registry.resolve_source(template_id)
            overlay_path = working_registry.overlay_path_for(template_id)
            entries.append(
                AgentCatalogEntry(
                    id=manifest.id,
                    label=manifest.label,
                    description=manifest.description.strip(),
                    archetype=manifest.archetype,
                    scope=manifest.scope,
                    status=manifest.status,
                    version=manifest.version,
                    source=source,
                    overlay_path=str(overlay_path)
                    if overlay_path is not None
                    else None,
                    ui=manifest.ui,
                    prompt_kinds=list(manifest.prompt_kinds),
                    mcp_tools=list(manifest.mcp_tools),
                    recommended_skills=list(manifest.recommended_skills),
                    external_skills=list(manifest.external_skills),
                    vendors=sorted(manifest.vendors.keys()),
                    delegates_to=list(manifest.delegates_to),
                    delegated_by=list(manifest.delegated_by),
                )
            )
        self._apply_delegation_index(entries)
        entries.sort(key=lambda item: (item.ui.sort_order, item.id))
        return AgentCatalogEnvelope(
            templates=entries,
            taxonomy=self._build_taxonomy(entries),
        )

    def build_delegation_index(
        self,
        entries: list[AgentCatalogEntry],
    ) -> dict[str, list[str]]:
        """Map template id to parent ids from ``delegates_to`` edges."""
        index: dict[str, list[str]] = {entry.id: [] for entry in entries}
        known_ids = {entry.id for entry in entries}
        for entry in entries:
            for child_id in entry.delegates_to:
                if child_id not in known_ids:
                    continue
                parents = index.setdefault(child_id, [])
                if entry.id not in parents:
                    parents.append(entry.id)
        for parents in index.values():
            parents.sort()
        return index

    def _apply_delegation_index(self, entries: list[AgentCatalogEntry]) -> None:
        index = self.build_delegation_index(entries)
        for entry in entries:
            computed = index.get(entry.id, [])
            if computed:
                entry.delegated_by = computed

    def _build_taxonomy(self, entries: list[AgentCatalogEntry]) -> AgentCatalogTaxonomy:
        archetypes = sorted({entry.archetype.value for entry in entries})
        scopes = sorted({entry.scope.value for entry in entries})
        vendors: set[str] = set()
        categories: set[str] = set()
        for entry in entries:
            vendors.update(entry.vendors)
            categories.add(entry.ui.category)
        return AgentCatalogTaxonomy(
            archetypes=archetypes,
            scopes=scopes,
            vendors=sorted(vendors),
            categories=sorted(categories),
        )

    def validate_all_templates(
        self,
        *,
        manifest_root: Path | None = None,
        template_id: str | None = None,
    ) -> list[AgentValidationIssue]:
        """Validate bundled and optional overlay templates."""
        working_registry = (
            self.registry
            if manifest_root is None
            else AgentTemplateRegistry(manifest_root=manifest_root)
        )
        issues: list[AgentValidationIssue] = []
        known_kinds = {item.kind for item in list_prompt_catalog()}
        template_ids = (
            [template_id]
            if template_id is not None
            else working_registry.list_template_ids()
        )
        known_ids = set(working_registry.list_template_ids())
        for current_id in template_ids:
            manifest = working_registry.load_manifest(current_id)
            if manifest is None:
                issues.append(
                    AgentValidationIssue(
                        template_id=current_id,
                        message="template manifest not found or invalid",
                    )
                )
                continue
            issues.extend(
                self._validate_manifest(
                    manifest,
                    known_ids=known_ids,
                    known_kinds=known_kinds,
                    registry=working_registry,
                )
            )
        return issues

    def _validate_manifest(
        self,
        manifest: AgentTemplateManifest,
        *,
        known_ids: set[str],
        known_kinds: set[str],
        registry: AgentTemplateRegistry,
    ) -> list[AgentValidationIssue]:
        issues: list[AgentValidationIssue] = []
        if manifest.id not in known_ids:
            issues.append(
                AgentValidationIssue(
                    template_id=manifest.id,
                    message=f"unknown template id: {manifest.id!r}",
                )
            )
        for child_id in manifest.delegates_to:
            if child_id not in known_ids:
                issues.append(
                    AgentValidationIssue(
                        template_id=manifest.id,
                        message=f"delegates_to references unknown template: {child_id!r}",
                    )
                )
        for kind in manifest.prompt_kinds:
            if kind not in known_kinds:
                issues.append(
                    AgentValidationIssue(
                        template_id=manifest.id,
                        message=f"unknown prompt kind: {kind!r}",
                    )
                )
        for file_spec in manifest.files:
            if registry.resolve_source_file(manifest.id, file_spec.template) is None:
                issues.append(
                    AgentValidationIssue(
                        template_id=manifest.id,
                        message=f"missing template file: {file_spec.template}",
                        path=file_spec.template,
                    )
                )
        for vendor, vendor_spec in manifest.vendors.items():
            template_name = vendor_spec.template
            if template_name is None:
                continue
            if registry.resolve_source_file(manifest.id, template_name) is None:
                issues.append(
                    AgentValidationIssue(
                        template_id=manifest.id,
                        message=f"missing vendor template: {template_name} ({vendor})",
                        path=template_name,
                    )
                )
        return issues
