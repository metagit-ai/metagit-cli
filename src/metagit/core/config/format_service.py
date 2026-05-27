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
from metagit.core.config.yaml_display import dump_config_dict
from metagit.core.config.yaml_order import order_payload

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
        minimal: bool = False,
    ) -> FormatFileResult | Exception:
        """Format a ``.metagit.yml`` manifest."""
        resolved = Path(config_path).expanduser().resolve()
        manager = MetagitConfigManager(config_path=str(resolved))
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            return loaded
        return self._build_result(
            target="metagit",
            path=str(resolved),
            original_text=self._read_text(resolved),
            formatted=self.render_metagit(loaded, minimal=minimal),
        )

    def format_appconfig(
        self,
        config_path: str | Path,
        *,
        minimal: bool = False,
    ) -> FormatFileResult | Exception:
        """Format ``metagit.config.yaml`` application config."""
        resolved = Path(config_path).expanduser().resolve()
        loaded = load_appconfig(str(resolved))
        if isinstance(loaded, Exception):
            return loaded
        return self._build_result(
            target="appconfig",
            path=str(resolved),
            original_text=self._read_text(resolved),
            formatted=self.render_appconfig(loaded, minimal=minimal),
        )

    def render_metagit(
        self,
        config: MetagitConfig,
        *,
        minimal: bool = False,
    ) -> str:
        """Render a metagit manifest using schema field order."""
        payload = config.model_dump(
            exclude_none=True,
            exclude_defaults=minimal,
            mode="json",
        )
        ordered = order_payload(payload, MetagitConfig)
        return self._ensure_trailing_newline(dump_config_dict(ordered))

    def render_appconfig(
        self,
        config: AppConfig,
        *,
        minimal: bool = False,
    ) -> str:
        """Render application config using schema field order."""
        body = config.model_dump(
            exclude_none=True,
            exclude_defaults=minimal,
            mode="json",
        )
        ordered_body = order_payload(body, AppConfig)
        payload = {"config": ordered_body}
        return self._ensure_trailing_newline(dump_config_dict(payload))

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _ensure_trailing_newline(text: str) -> str:
        return text if text.endswith("\n") else f"{text}\n"

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
