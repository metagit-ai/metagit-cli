#!/usr/bin/env python
"""Apply schema-tree config operations for CLI and web consumers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.appconfig import save_config as save_appconfig
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.web.config_preview import (
    PreviewStyle,
    read_disk_text,
    render_appconfig_yaml,
    render_metagit_yaml,
)
from metagit.core.web.models import ConfigOperation, SchemaFieldNode
from metagit.core.web.schema_tree import SchemaTreeService

ConfigTarget = Literal["metagit", "appconfig"]


class PatchResult(BaseModel):
    """Outcome of applying config patch operations."""

    ok: bool
    target: ConfigTarget
    config_path: str
    validation_errors: list[dict[str, str]] = Field(default_factory=list)
    saved: bool = False
    tree: SchemaFieldNode | None = None


class PreviewResult(BaseModel):
    """YAML preview after optional draft operations."""

    ok: bool
    target: ConfigTarget
    config_path: str
    style: PreviewStyle
    yaml: str
    draft: bool = False
    validation_errors: list[dict[str, str]] = Field(default_factory=list)


class TreeResult(BaseModel):
    """Schema tree for a loaded config."""

    ok: bool
    target: ConfigTarget
    config_path: str
    tree: SchemaFieldNode
    validation_errors: list[dict[str, str]] = Field(default_factory=list)


class ConfigPatchService:
    """Load, mutate, preview, and save metagit and appconfig via schema operations."""

    def __init__(self) -> None:
        self._schema = SchemaTreeService()

    def build_tree(
        self,
        target: ConfigTarget,
        config_path: str,
        *,
        mask_secrets: bool = False,
    ) -> TreeResult | Exception:
        """Build schema tree for the config at config_path."""
        resolved = str(Path(config_path).resolve())
        loaded = self._load_metagit(resolved) if target == "metagit" else self._load_appconfig(resolved)
        if isinstance(loaded, Exception):
            return loaded
        model_class = MetagitConfig if target == "metagit" else AppConfig
        tree = self._schema.build_tree(
            loaded,
            model_class,
            mask_secrets=mask_secrets or target == "appconfig",
        )
        return TreeResult(
            ok=True,
            target=target,
            config_path=resolved,
            tree=tree,
        )

    def preview(
        self,
        target: ConfigTarget,
        config_path: str,
        operations: list[ConfigOperation],
        *,
        style: PreviewStyle = "normalized",
    ) -> PreviewResult | Exception:
        """Render YAML preview with optional draft operations."""
        resolved = str(Path(config_path).resolve())
        if style == "disk" and operations:
            return ValueError("disk preview cannot include draft operations")
        if target == "metagit":
            loaded = self._load_metagit(resolved)
            model_class = MetagitConfig
        else:
            loaded = self._load_appconfig(resolved)
            model_class = AppConfig
        if isinstance(loaded, Exception):
            return loaded
        config = loaded
        validation_errors: list[dict[str, str]] = []
        draft = bool(operations)
        if draft:
            config, validation_errors = self._schema.apply_operations(
                loaded,
                model_class,
                operations,
            )
        if style == "disk":
            yaml_text = read_disk_text(resolved)
        elif target == "metagit":
            yaml_text = render_metagit_yaml(config, style=style)
        else:
            yaml_text = render_appconfig_yaml(
                config,
                config_path=resolved,
                style=style,
                mask_secrets=True,
            )
        return PreviewResult(
            ok=len(validation_errors) == 0,
            target=target,
            config_path=resolved,
            style=style,
            yaml=yaml_text,
            draft=draft,
            validation_errors=validation_errors,
        )

    def patch(
        self,
        target: ConfigTarget,
        config_path: str,
        operations: list[ConfigOperation],
        *,
        save: bool = False,
        auto_format: bool = True,
        include_tree: bool = False,
        mask_secrets: bool = False,
    ) -> PatchResult | Exception:
        """Apply operations; optionally persist when save=True and validation passes."""
        resolved = str(Path(config_path).resolve())
        if target == "metagit":
            loaded = self._load_metagit(resolved)
            model_class = MetagitConfig
        else:
            loaded = self._load_appconfig(resolved)
            model_class = AppConfig
        if isinstance(loaded, Exception):
            return loaded
        updated, validation_errors = self._schema.apply_operations(
            loaded,
            model_class,
            operations,
        )
        saved = False
        if save and not validation_errors:
            if target == "metagit":
                save_result = MetagitConfigManager(resolved).save_config(
                    updated,
                    auto_format=auto_format,
                )
            else:
                save_result = save_appconfig(
                    resolved,
                    updated,
                    auto_format=auto_format,
                )
            if isinstance(save_result, Exception):
                return save_result
            saved = True
        tree = None
        if include_tree:
            tree = self._schema.build_tree(
                updated,
                model_class,
                mask_secrets=mask_secrets or target == "appconfig",
            )
        return PatchResult(
            ok=len(validation_errors) == 0,
            target=target,
            config_path=resolved,
            validation_errors=validation_errors,
            saved=saved,
            tree=tree,
        )

    def _load_metagit(self, config_path: str) -> MetagitConfig | Exception:
        manager = MetagitConfigManager(config_path=config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            return loaded
        return loaded

    def _load_appconfig(self, config_path: str) -> AppConfig | Exception:
        loaded = load_appconfig(config_path)
        if isinstance(loaded, Exception):
            return loaded
        return loaded
