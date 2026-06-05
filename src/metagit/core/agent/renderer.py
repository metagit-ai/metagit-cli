#!/usr/bin/env python
"""Render agent templates with partial includes."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from metagit.core.init.models import InitTemplateFileSpec
from metagit.core.init.renderer import InitTemplateRenderer, render_placeholders

_INCLUDE = re.compile(r'\{\{\s*include\s+"([^"]+)"\s*\}\}')
_MAX_INCLUDE_DEPTH = 3


class AgentTemplateRenderer(InitTemplateRenderer):
    """Render agent templates with ``{{ include "name" }}`` partial expansion."""

    def __init__(
        self,
        *,
        resolve_source: Callable[[str], Path | None],
    ) -> None:
        self._resolve_source = resolve_source

    def render_file(
        self,
        template_dir: Path,
        file_spec: InitTemplateFileSpec,
        context: dict[str, str],
    ) -> str:
        source = self._resolve_source(file_spec.template)
        if source is None or not source.is_file():
            raise FileNotFoundError(f"template file not found: {file_spec.template}")
        raw = source.read_text(encoding="utf-8")
        return self._expand_includes(raw, context, chain=())

    def _expand_includes(
        self,
        content: str,
        context: dict[str, str],
        *,
        chain: tuple[str, ...],
        depth: int = 0,
    ) -> str:
        if depth > _MAX_INCLUDE_DEPTH:
            raise ValueError("agent template include depth exceeded")

        def _replace(match: re.Match[str]) -> str:
            partial_name = match.group(1)
            if partial_name in chain:
                cycle = " -> ".join((*chain, partial_name))
                raise ValueError(f"agent template include cycle detected: {cycle}")
            partial_path = self._resolve_source(partial_name)
            if partial_path is None or not partial_path.is_file():
                raise FileNotFoundError(f"partial not found: {partial_name}")
            partial_raw = partial_path.read_text(encoding="utf-8")
            expanded = self._expand_includes(
                partial_raw,
                context,
                chain=(*chain, partial_name),
                depth=depth + 1,
            )
            return render_placeholders(expanded, context)

        expanded = _INCLUDE.sub(_replace, content)
        return render_placeholders(expanded, context)
