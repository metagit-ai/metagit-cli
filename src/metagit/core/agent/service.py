#!/usr/bin/env python
"""Export and install bundled agent definitions for coding vendors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Literal, Optional

import click

from metagit.core.agent.catalog import AgentCatalogService
from metagit.core.agent.dispatch import AgentDispatchService
from metagit.core.agent.models import (
    AgentDispatchPlan,
    AgentOverlayInitMode,
    AgentOverlayInitResult,
    AgentOverlayScope,
    AgentPreviewResult,
    AgentTemplateDetail,
    AgentTemplateManifest,
    AgentWriteResult,
)
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.agent.overlay import init_overlay_from_bundled
from metagit.core.agent.paths import resolve_agents_directory, resolve_skills_directory
from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.agent.renderer import AgentTemplateRenderer
from metagit.core.init.models import InitTemplateFileSpec
from metagit.core.init.prompts import collect_answers, load_answers_file
from metagit.core.skills.installer import (
    InstallResult,
    install_mcp_for_targets,
    install_skills_for_targets,
)


@dataclass
class AgentService:
    """List, export, and install agent templates."""

    manifest_root: Path | None = None
    registry: AgentTemplateRegistry | None = None
    renderer: AgentTemplateRenderer | None = None
    catalog: AgentCatalogService | None = None

    def __post_init__(self) -> None:
        if self.registry is None:
            self.registry = AgentTemplateRegistry(manifest_root=self.manifest_root)
        if self.renderer is None:
            self.renderer = AgentTemplateRenderer(
                resolve_source=lambda filename: self.registry.resolve_source_file(
                    self._active_template_id or "",
                    filename,
                )
                if self._active_template_id
                else None,
            )
        if self.catalog is None:
            self.catalog = AgentCatalogService(registry=self.registry)
        self._active_template_id: str | None = None

    def list_templates(self) -> list[AgentTemplateManifest]:
        return self.registry.list_templates()

    def template_detail(self, template_id: str) -> AgentTemplateDetail | None:
        manifest = self.registry.load_manifest(template_id)
        if manifest is None:
            return None
        return AgentTemplateDetail(
            source=self.registry.resolve_source(template_id),
            overlay_path=(
                str(self.registry.overlay_path_for(template_id))
                if self.registry.overlay_path_for(template_id) is not None
                else None
            ),
            manifest=manifest,
            template_files=self.registry.list_template_files(template_id),
        )

    def resolve_vendor_spec(
        self,
        manifest: AgentTemplateManifest,
        vendor: str,
    ):
        return manifest.vendors.get(vendor)

    def resolve_vendor_filename(
        self,
        manifest: AgentTemplateManifest,
        vendor: str,
    ) -> str:
        vendor_spec = self.resolve_vendor_spec(manifest, vendor)
        if vendor_spec is not None:
            return vendor_spec.filename
        return f"{manifest.id}.md"

    def render_vendor_primary(
        self,
        template_id: str,
        vendor: str,
        context: dict[str, str],
    ) -> tuple[AgentTemplateManifest, str]:
        """Render the primary install artifact for one vendor."""
        manifest = self._require_manifest(template_id)
        vendor_spec = self.resolve_vendor_spec(manifest, vendor)
        if vendor_spec is not None and vendor_spec.template:
            source_name = vendor_spec.template
        else:
            source_name = next(
                (item.template for item in manifest.files if not item.optional),
                f"{manifest.id}.md.tpl",
            )
        content = self._render_source(template_id, source_name, context)
        return manifest, content

    def preview(
        self,
        template_id: str,
        *,
        vendor: str,
        directory_name: str,
        git_remote_url: Optional[str],
        answers_file: Optional[Path] = None,
        answers: Optional[dict[str, str]] = None,
        overrides: Optional[dict[str, str]] = None,
        no_prompt: bool = False,
    ) -> AgentPreviewResult:
        """Render one vendor artifact without writing files."""
        manifest = self._require_manifest(template_id)
        context = self.collect_context(
            manifest,
            Path.cwd(),
            directory_name=directory_name,
            git_remote_url=git_remote_url,
            answers_file=answers_file,
            answers=answers,
            overrides=overrides,
            no_prompt=no_prompt,
        )
        _, content = self.render_vendor_primary(template_id, vendor, context)
        return AgentPreviewResult(
            template_id=template_id,
            vendor=vendor,
            filename=self.resolve_vendor_filename(manifest, vendor),
            content=content,
            source=self.registry.resolve_source(template_id),
        )

    def collect_context(
        self,
        manifest: AgentTemplateManifest,
        target_dir: Path,
        *,
        directory_name: str,
        git_remote_url: Optional[str],
        answers_file: Optional[Path] = None,
        answers: Optional[dict[str, str]] = None,
        overrides: Optional[dict[str, str]] = None,
        no_prompt: bool = False,
    ) -> dict[str, str]:
        loaded_answers: dict[str, str] | None = None
        if answers_file is not None:
            loaded_answers = load_answers_file(answers_file)
        prompt_manifest = SimpleNamespace(
            prompts=manifest.prompts,
            kind="agent",
        )
        context = collect_answers(
            prompt_manifest,
            target_dir=target_dir,
            directory_name=directory_name,
            git_remote_url=git_remote_url,
            answers=loaded_answers or answers,
            overrides=overrides,
            no_prompt=no_prompt,
        )
        context.setdefault("id", manifest.id)
        context.setdefault("label", manifest.label)
        return context

    def render_template(
        self,
        template_id: str,
        context: dict[str, str],
    ) -> tuple[AgentTemplateManifest, list[tuple[str, str]]]:
        manifest = self.registry.load_manifest(template_id)
        if manifest is None:
            raise click.ClickException(f"Unknown agent template: {template_id!r}")
        rendered_pairs: list[tuple[str, str]] = []
        for file_spec in manifest.files:
            content = self._render_source(template_id, file_spec.template, context)
            if file_spec.optional and not content.strip():
                continue
            rendered_pairs.append((file_spec.output, content))
        return manifest, rendered_pairs

    def export(
        self,
        template_id: str,
        output_dir: Path,
        *,
        directory_name: str,
        git_remote_url: Optional[str],
        answers_file: Optional[Path] = None,
        answers: Optional[dict[str, str]] = None,
        overrides: Optional[dict[str, str]] = None,
        no_prompt: bool = False,
        force: bool = False,
        dry_run: bool = False,
    ) -> AgentWriteResult:
        context = self.collect_context(
            self._require_manifest(template_id),
            output_dir,
            directory_name=directory_name,
            git_remote_url=git_remote_url,
            answers_file=answers_file,
            answers=answers,
            overrides=overrides,
            no_prompt=no_prompt,
        )
        manifest, rendered_pairs = self.render_template(template_id, context)
        written: list[str] = []
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
        for relative_output, content in rendered_pairs:
            destination = output_dir / relative_output
            if destination.exists() and not force:
                raise click.ClickException(
                    f"Refusing to overwrite existing file: {destination} (use --force)"
                )
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
            written.append(str(destination))
        return AgentWriteResult(
            template_id=manifest.id,
            paths=written,
            dry_run=dry_run,
        )

    def create(
        self,
        template_id: str,
        *,
        vendor: str,
        scope: str,
        project_root: Path,
        directory_name: str,
        git_remote_url: Optional[str],
        answers_file: Optional[Path] = None,
        answers: Optional[dict[str, str]] = None,
        overrides: Optional[dict[str, str]] = None,
        no_prompt: bool = False,
        force: bool = False,
        dry_run: bool = False,
        install_skills: bool = False,
        install_mcp: bool = False,
    ) -> tuple[AgentWriteResult, list[InstallResult]]:
        manifest = self._require_manifest(template_id)
        context = self.collect_context(
            manifest,
            project_root,
            directory_name=directory_name,
            git_remote_url=git_remote_url,
            answers_file=answers_file,
            answers=answers,
            overrides=overrides,
            no_prompt=no_prompt,
        )
        manifest, primary_content = self.render_vendor_primary(
            template_id,
            vendor,
            context,
        )
        vendor_spec = self.resolve_vendor_spec(manifest, vendor)
        install_as = vendor_spec.install_as if vendor_spec is not None else "agent"
        primary_name = self.resolve_vendor_filename(manifest, vendor)

        if install_as == "skill":
            skills_dir = resolve_skills_directory(
                vendor,
                scope,
                project_root=project_root,
            )
            destination = skills_dir / primary_name / "SKILL.md"
        else:
            agents_dir = resolve_agents_directory(
                vendor,
                scope,
                project_root=project_root,
            )
            destination = agents_dir / primary_name

        if destination.exists() and not force:
            raise click.ClickException(
                f"Refusing to overwrite existing agent: {destination} (use --force)"
            )
        written: list[str] = []
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(primary_content, encoding="utf-8")
        written.append(str(destination))

        install_results: list[InstallResult] = []
        if install_skills and manifest.recommended_skills:
            install_results.extend(
                install_skills_for_targets(
                    [vendor],
                    scope,  # type: ignore[arg-type]
                    manifest.recommended_skills,
                    dry_run=dry_run,
                )
            )
        if install_mcp:
            if dry_run:
                install_results.append(
                    InstallResult(
                        target=vendor,
                        mode="mcp",
                        scope=scope,  # type: ignore[arg-type]
                        applied=False,
                        path=str(resolve_agents_directory(vendor, scope)),
                        details="Would install metagit MCP server config",
                        dry_run=True,
                    )
                )
            else:
                install_results.extend(
                    install_mcp_for_targets([vendor], scope)  # type: ignore[arg-type]
                )

        return (
            AgentWriteResult(
                template_id=manifest.id,
                paths=written,
                vendor=vendor,
                scope=scope,
                dry_run=dry_run,
            ),
            install_results,
        )

    def _render_source(
        self,
        template_id: str,
        filename: str,
        context: dict[str, str],
    ) -> str:
        self._active_template_id = template_id
        self.renderer = AgentTemplateRenderer(
            resolve_source=lambda name: self.registry.resolve_source_file(
                template_id,
                name,
            ),
        )
        return self.renderer.render_file(
            self.registry.template_dir(template_id),
            InitTemplateFileSpec(template=filename, output="rendered"),
            context,
        )

    def dispatch_plan(
        self,
        template_id: str,
        *,
        vendor: str,
        scope: Literal["project", "user"] = "project",
        project: str | None = None,
        repo: str | None = None,
        task: str | None = None,
        definition_path: str = ".metagit.yml",
        config: MetagitConfig | None = None,
    ) -> AgentDispatchPlan:
        """Build install, launch, and handoff envelope for one template."""
        resolved_config = config
        if resolved_config is None and self.manifest_root is not None:
            config_path = Path(definition_path)
            if not config_path.is_absolute():
                config_path = self.manifest_root / definition_path
            if config_path.is_file():
                loaded = MetagitConfigManager(config_path=config_path).load_config()
                if not isinstance(loaded, Exception):
                    resolved_config = loaded
        dispatch = AgentDispatchService(
            registry=self.registry,
            manifest_root=self.manifest_root or Path.cwd(),
            config=resolved_config,
        )
        try:
            return dispatch.build_plan(
                template_id,
                vendor=vendor,
                scope=scope,
                project=project,
                repo=repo,
                task=task,
                definition_path=definition_path,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    def init_overlay(
        self,
        template_id: str,
        *,
        scope: AgentOverlayScope = AgentOverlayScope.COMMITTED,
        mode: AgentOverlayInitMode = AgentOverlayInitMode.FULL,
        force: bool = False,
        dry_run: bool = False,
    ) -> AgentOverlayInitResult:
        """Scaffold an editable workspace overlay from a bundled template."""
        if self.manifest_root is None:
            raise click.ClickException(
                "Manifest root is required for overlay init (pass --root)"
            )
        bundled = self.registry.load_bundled_manifest(template_id)
        if bundled is None:
            raise click.ClickException(
                f"No bundled template to overlay: {template_id!r}"
            )
        try:
            return init_overlay_from_bundled(
                template_id=template_id,
                manifest_root=self.manifest_root,
                bundled_dir=self.registry.template_dir(template_id),
                scope=scope,
                mode=mode,
                force=force,
                dry_run=dry_run,
            )
        except FileExistsError as exc:
            raise click.ClickException(f"{exc} (use --force)") from exc
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    def _require_manifest(self, template_id: str) -> AgentTemplateManifest:
        manifest = self.registry.load_manifest(template_id)
        if manifest is None:
            raise click.ClickException(f"Unknown agent template: {template_id!r}")
        return manifest
