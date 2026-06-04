#!/usr/bin/env python
"""Generate JSON Schema with YAML input unions matching Pydantic before-validators."""

from __future__ import annotations

import copy
from typing import Any, Type

from pydantic import BaseModel

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig

TAGS_OBJECT_OR_STRING_LIST: dict[str, Any] = {
    "anyOf": [
        {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Flat string tags keyed by name",
        },
        {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tag names (legacy maps normalized to lists at load time)",
        },
    ],
    "description": "Flat metadata tags as a map or list of tag names",
    "title": "Tags",
}

DOCUMENTATION_ENTRY: dict[str, Any] = {
    "anyOf": [
        {
            "type": "string",
            "description": "Markdown path or http(s) URL shorthand",
        },
        {"$ref": "#/$defs/DocumentationSource"},
    ]
}

REPOS_ARRAY_ITEM: dict[str, Any] = {
    "anyOf": [
        {"$ref": "#/$defs/ProjectPath"},
        {
            "type": "array",
            "items": {"$ref": "#/$defs/ProjectPath"},
            "description": "Nested repo list (flattened when YAML anchors expand)",
        },
    ]
}

AGENT_PROMPT_PROPERTY: dict[str, Any] = {
    "anyOf": [{"type": "string"}, {"type": "null"}],
    "default": None,
    "description": "Alias for agent_instructions (legacy/agent host compatibility)",
    "title": "Agent Prompt",
}

_AGENT_PROMPT_DEFS = (
    "MetagitConfig",
    "Workspace",
    "WorkspaceProject",
    "ProjectPath",
)


def generate_json_schema(model: Type[BaseModel]) -> dict[str, Any]:
    """Return JSON Schema for ``model`` with input-shape unions applied."""
    schema = model.model_json_schema()
    if model is MetagitConfig:
        return patch_metagit_config_schema(schema)
    if model is AppConfig:
        return patch_appconfig_schema(schema)
    return schema


def patch_metagit_config_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Apply Metagit manifest input unions for yaml-language-server."""
    patched = copy.deepcopy(schema)
    defs = patched.setdefault("$defs", {})

    if "DocumentationSource" in defs:
        props = defs["DocumentationSource"].setdefault("properties", {})
        props["tags"] = copy.deepcopy(TAGS_OBJECT_OR_STRING_LIST)

    _patch_documentation_property(patched.get("properties", {}))
    _patch_repos_items(defs.get("WorkspaceProject", {}))

    for def_name in _AGENT_PROMPT_DEFS:
        if def_name == "MetagitConfig":
            _add_agent_prompt_alias(patched.get("properties", {}))
        elif def_name in defs:
            _add_agent_prompt_alias(defs[def_name].get("properties", {}))

    return patched


def patch_appconfig_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Apply AppConfig schema patches (none today; hook for future coercions)."""
    return copy.deepcopy(schema)


def _patch_documentation_property(properties: dict[str, Any]) -> None:
    documentation = properties.get("documentation")
    if not isinstance(documentation, dict):
        return
    for variant in documentation.get("anyOf", []):
        if variant.get("type") == "array":
            variant["items"] = copy.deepcopy(DOCUMENTATION_ENTRY)
            return
    if documentation.get("type") == "array":
        documentation["items"] = copy.deepcopy(DOCUMENTATION_ENTRY)


def _patch_repos_items(workspace_project: dict[str, Any]) -> None:
    repos = workspace_project.get("properties", {}).get("repos")
    if not isinstance(repos, dict) or repos.get("type") != "array":
        return
    repos["items"] = copy.deepcopy(REPOS_ARRAY_ITEM)


def _add_agent_prompt_alias(properties: dict[str, Any]) -> None:
    if "agent_instructions" in properties and "agent_prompt" not in properties:
        properties["agent_prompt"] = copy.deepcopy(AGENT_PROMPT_PROPERTY)
