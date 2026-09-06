#!/usr/bin/env python
"""First-class component catalog types and services."""

from metagit.core.component.identity import ComponentId, component_id, parse_component_id
from metagit.core.component.models import Component, ComponentCommand, ComponentRef
from metagit.core.component.paths import normalize_repo_relative_path

__all__ = [
    "Component",
    "ComponentCommand",
    "ComponentId",
    "ComponentRef",
    "component_id",
    "normalize_repo_relative_path",
    "parse_component_id",
]
