#!/usr/bin/env python
"""Format metagit and appconfig YAML files for readable, schema-ordered output."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.config.schema_urls import (
    METAGIT_APPCONFIG_SCHEMA_URL,
    METAGIT_CONFIG_SCHEMA_URL,
)
from metagit.core.config.documentation_models import compact_documentation_list
from metagit.core.config.payload_compact import prepare_format_payload
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


class ConfigFormatService:
    """Load, normalize, and serialize configuration files."""

    def format_metagit(
        self,
        config_path: str | Path,
        *,
        include_defaults: bool = False,
    ) -> FormatFileResult | Exception:
        """Format a ``.metagit.yml`` manifest."""
        resolved = Path(config_path).expanduser().resolve()
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
        payload = config.model_dump(
            exclude_none=True,
            exclude_defaults=not include_defaults,
            mode="json",
        )
        if config.documentation:
            payload["documentation"] = compact_documentation_list(config.documentation)
        payload = prepare_format_payload(
            payload,
            MetagitConfig,
            include_defaults=include_defaults,
        )
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
        body = prepare_format_payload(
            body, AppConfig, include_defaults=include_defaults
        )
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
            original_text
            if original_text.endswith("\n") or not original_text
            else f"{original_text}\n"
        )
        return FormatFileResult(
            target=target,
            path=path,
            changed=normalized_original != formatted,
            formatted=formatted,
        )
