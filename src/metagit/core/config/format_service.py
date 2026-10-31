#!/usr/bin/env python
"""Format metagit and appconfig YAML files for readable, schema-ordered output."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.documentation_models import compact_documentation_list
from metagit.core.config.graph_models import graph_relationships_payload
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.config.payload_compact import prepare_format_payload
from metagit.core.config.schema_urls import (
    METAGIT_APPCONFIG_SCHEMA_URL,
    METAGIT_CONFIG_SCHEMA_URL,
)
from metagit.core.config.yaml_order import order_payload
from metagit.core.config.yaml_roundtrip import format_yaml_document

FormatTarget = Literal["metagit", "appconfig"]


class FormatFileResult(BaseModel):
    """Outcome of formatting one config file."""

    target: FormatTarget
    path: str
    changed: bool
    formatted: str
    error: str | None = None


def build_metagit_payload(config: MetagitConfig, *, include_defaults: bool = False) -> dict[str, Any]:
    """Serialize a manifest the same way ``render_metagit`` does, before key ordering."""
    payload = config.model_dump(
        exclude_none=True,
        exclude_defaults=not include_defaults,
        mode="json",
        by_alias=True,
    )
    if config.documentation:
        payload["documentation"] = compact_documentation_list(config.documentation)
    if config.graph is not None and config.graph.relationships:
        payload.setdefault("graph", {})["relationships"] = graph_relationships_payload(
            config.graph.relationships,
            include_defaults=include_defaults,
        )
    prepared = prepare_format_payload(
        payload,
        MetagitConfig,
        include_defaults=include_defaults,
    )
    return prepared if isinstance(prepared, dict) else payload


class ConfigFormatService:
    """Load, normalize, and serialize configuration files."""

    def format_metagit(
        self,
        config_path: str | Path,
        *,
        include_defaults: bool = False,
    ) -> FormatFileResult | Exception:
        """Format a ``.metagit.yml`` manifest. Split manifests format the root file only."""
        results = self.format_manifest_files(config_path, include_defaults=include_defaults)
        if isinstance(results, Exception):
            return results
        return results[0]

    def format_manifest_files(
        self,
        config_path: str | Path,
        *,
        include_defaults: bool = False,
    ) -> list[FormatFileResult] | Exception:
        """Format the root manifest and every included fragment."""
        from metagit.core.config.include_loader import manifest_declares_includes
        from metagit.core.config.include_writer import partition_payload, render_partition

        resolved = Path(config_path).expanduser().resolve()
        if not manifest_declares_includes(resolved):
            single = self._format_single(resolved, include_defaults=include_defaults)
            if isinstance(single, Exception):
                return single
            return [single]
        manager = MetagitConfigManager(config_path=str(resolved))
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            return loaded
        if manager.source_map is None:
            single = self._format_single(resolved, include_defaults=include_defaults)
            if isinstance(single, Exception):
                return single
            return [single]
        payload = build_metagit_payload(loaded, include_defaults=include_defaults)
        parts = partition_payload(payload, manager.source_map)
        if isinstance(parts, Exception):
            return parts
        results: list[FormatFileResult] = []
        for path, part in parts.items():
            target = Path(path)
            original = self._read_text(target)
            formatted = render_partition(
                target,
                part,
                manager.source_map,
                include_defaults=include_defaults,
            )
            results.append(
                self._build_result(
                    target="metagit",
                    path=str(target),
                    original_text=original,
                    formatted=formatted,
                )
            )
        return results

    def _format_single(self, resolved: Path, *, include_defaults: bool) -> FormatFileResult | Exception:
        """Format one manifest that does not use includes."""
        original_text = self._read_text(resolved)
        manager = MetagitConfigManager(config_path=str(resolved))
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            return loaded
        return self._build_result(
            target="metagit",
            path=str(resolved),
            original_text=original_text,
            formatted=self.render_metagit(
                loaded,
                include_defaults=include_defaults,
                original_text=original_text,
            ),
        )

    def format_appconfig(
        self,
        config_path: str | Path,
        *,
        include_defaults: bool = False,
    ) -> FormatFileResult | Exception:
        """Format ``metagit.config.yaml`` application config."""
        resolved = Path(config_path).expanduser().resolve()
        original_text = self._read_text(resolved)
        loaded = load_appconfig(str(resolved))
        if isinstance(loaded, Exception):
            return loaded
        return self._build_result(
            target="appconfig",
            path=str(resolved),
            original_text=original_text,
            formatted=self.render_appconfig(
                loaded,
                include_defaults=include_defaults,
                original_text=original_text,
            ),
        )

    def render_metagit(
        self,
        config: MetagitConfig,
        *,
        include_defaults: bool = False,
        original_text: str = "",
    ) -> str:
        """Render a metagit manifest using schema field order."""
        payload = build_metagit_payload(config, include_defaults=include_defaults)
        ordered = order_payload(payload, MetagitConfig)
        return format_yaml_document(
            original_text,
            ordered,
            MetagitConfig,
            schema_url=METAGIT_CONFIG_SCHEMA_URL,
            strip_absent_model_fields=not include_defaults,
        )

    def render_appconfig(
        self,
        config: AppConfig,
        *,
        include_defaults: bool = False,
        original_text: str = "",
    ) -> str:
        """Render application config using schema field order."""
        body = config.model_dump(
            exclude_none=True,
            exclude_defaults=not include_defaults,
            mode="json",
        )
        body = prepare_format_payload(body, AppConfig, include_defaults=include_defaults)
        ordered_body = order_payload(body, AppConfig)
        return format_yaml_document(
            original_text,
            ordered_body,
            AppConfig,
            schema_url=METAGIT_APPCONFIG_SCHEMA_URL,
            wrapper_key="config",
            strip_absent_model_fields=not include_defaults,
        )

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _build_result(
        *,
        target: FormatTarget,
        path: str,
        original_text: str,
        formatted: str,
    ) -> FormatFileResult:
        normalized_original = (
            original_text if original_text.endswith("\n") or not original_text else f"{original_text}\n"
        )
        return FormatFileResult(
            target=target,
            path=path,
            changed=normalized_original != formatted,
            formatted=formatted,
        )
