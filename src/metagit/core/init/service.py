#!/usr/bin/env python
"""Orchestrate metagit init from templates or minimal kind profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import click

from metagit.core.config.manifest_gate import (
    ManifestGateInvalid,
    evaluate_existing_manifest,
    manifest_gate_error_message,
)
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.init.models import InitTemplateManifest
from metagit.core.init.prompts import collect_answers, load_answers_file
from metagit.core.init.registry import InitTemplateRegistry
from metagit.core.init.renderer import InitTemplateRenderer, validate_metagit_yaml
from metagit.core.project.models import ProjectKind
from metagit.core.utils.yaml_class import yaml


@dataclass
class InitWriteResult:
    """Files written during init."""

    metagit_yml: Path
    extra_files: list[Path] = field(default_factory=list)
    already_exists: bool = False


@dataclass
class InitService:
    """Create .metagit.yml and optional companion files from templates or kinds."""

    registry: InitTemplateRegistry = field(default_factory=InitTemplateRegistry)
    renderer: InitTemplateRenderer = field(default_factory=InitTemplateRenderer)

    def list_templates(self) -> list[InitTemplateManifest]:
        return self.registry.list_templates()

    def resolve_template_id(self, template: Optional[str], kind: Optional[str]) -> str:
        """Map --template or --kind to a bundled template id when a bundle exists."""
        if template:
            return template
        if kind:
            candidate = kind.strip().lower()
            if self.registry.load_manifest(candidate) is not None:
                return candidate
        return "application"

    @staticmethod
    def _resolve_existing_manifest(
        metagit_path: Path,
        *,
        force: bool,
    ) -> InitWriteResult | None:
        """
        When a manifest already exists, validate it or allow overwrite.

        Returns an ``InitWriteResult`` with ``already_exists=True`` when the file
        is present, valid, and ``force`` is false. Returns ``None`` when init
        should proceed with a write.
        """
        gate = evaluate_existing_manifest(metagit_path, force=force)
        if gate is None:
            return None
        if isinstance(gate, ManifestGateInvalid):
            raise click.ClickException(manifest_gate_error_message(gate))
        return InitWriteResult(
            metagit_yml=gate.path,
            extra_files=[],
            already_exists=True,
        )

    def initialize(
        self,
        target_dir: Path,
        *,
        template_id: str,
        directory_name: str,
        git_remote_url: Optional[str],
        answers_file: Optional[Path] = None,
        answers: Optional[dict[str, str]] = None,
        overrides: Optional[dict[str, str]] = None,
        no_prompt: bool = False,
        force: bool = False,
        dry_run: bool = False,
    ) -> InitWriteResult:
        manifest = self.registry.load_manifest(template_id)
        if manifest is None:
            raise click.ClickException(f"Unknown init template: {template_id!r}")

        metagit_path = target_dir / ".metagit.yml"
        existing = self._resolve_existing_manifest(metagit_path, force=force)
        if existing is not None:
            return existing

        file_answers: dict[str, str] = {}
        if answers_file is not None:
            file_answers = load_answers_file(answers_file)

        context = collect_answers(
            manifest,
            target_dir=target_dir,
            directory_name=directory_name,
            git_remote_url=git_remote_url,
            answers={**file_answers, **(answers or {})},
            overrides=overrides,
            no_prompt=no_prompt,
        )
        context.setdefault("kind", manifest.kind)

        template_dir = self.registry.template_dir(template_id)
        rendered_files = self.renderer.render_manifest(template_dir, manifest, context)

        extra_paths: list[Path] = []
        metagit_content: Optional[str] = None

        for file_spec, content in rendered_files:
            destination = target_dir / file_spec.output
            if file_spec.output == ".metagit.yml":
                metagit_content = content
                if not dry_run:
                    destination.write_text(content, encoding="utf-8")
                continue
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
            extra_paths.append(destination)

        if metagit_content is None:
            raise click.ClickException("template did not produce .metagit.yml")

        return InitWriteResult(metagit_yml=metagit_path, extra_files=extra_paths)

    def initialize_minimal(
        self,
        target_dir: Path,
        *,
        kind: str,
        name: str,
        description: str,
        url: Optional[str],
        force: bool = False,
        dry_run: bool = False,
    ) -> InitWriteResult:
        """Create a minimal validated manifest without a bundled template directory."""
        metagit_path = target_dir / ".metagit.yml"
        existing = self._resolve_existing_manifest(metagit_path, force=force)
        if existing is not None:
            return existing

        try:
            kind_value = ProjectKind(kind)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ProjectKind)
            raise click.ClickException(
                f"Invalid kind {kind!r}; expected one of: {allowed}"
            ) from exc

        manager = MetagitConfigManager()
        config_result = manager.create_config(
            name=name,
            description=description,
            url=url,
            kind=kind_value.value,
        )
        if isinstance(config_result, Exception):
            raise click.ClickException(f"Failed to build config: {config_result}")

        payload = config_result.model_dump(
            mode="json",
            exclude_none=True,
        )
        content = yaml.safe_dump(
            payload,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            line_break=True,
        )
        validate_metagit_yaml(content)
        if not dry_run:
            metagit_path.write_text(content, encoding="utf-8")
        return InitWriteResult(metagit_yml=metagit_path)
