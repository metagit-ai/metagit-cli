#!/usr/bin/env python
"""Tests for JSON Schema generation with input-shape unions."""

from __future__ import annotations

import json

import jsonschema
import yaml

from metagit.core.config.models import MetagitConfig
from metagit.core.config.schema_generator import generate_json_schema


def test_documentation_accepts_string_shorthand_in_schema() -> None:
    schema = generate_json_schema(MetagitConfig)
    instance = {
        "name": "demo",
        "documentation": [
            "README.md",
            "https://example.com/docs",
            {
                "kind": "confluence",
                "url": "https://confluence.example.com/display/DOC",
                "tags": ["playbook", "tutorial"],
            },
        ],
        "workspace": {"projects": [{"name": "default", "repos": []}]},
    }
    jsonschema.validate(instance, schema)


def test_documentation_tags_accepts_list_or_map_in_schema() -> None:
    schema = generate_json_schema(MetagitConfig)
    map_instance = {
        "name": "demo",
        "documentation": [
            {"kind": "web", "url": "https://example.com", "tags": {"docker": "true"}},
        ],
        "workspace": {"projects": [{"name": "default", "repos": []}]},
    }
    list_instance = {
        "name": "demo",
        "documentation": [
            {
                "kind": "web",
                "url": "https://example.com",
                "tags": ["docker", "python"],
            },
        ],
        "workspace": {"projects": [{"name": "default", "repos": []}]},
    }
    jsonschema.validate(map_instance, schema)
    jsonschema.validate(list_instance, schema)


def test_agent_prompt_alias_accepted_in_schema() -> None:
    schema = generate_json_schema(MetagitConfig)
    instance = {
        "name": "demo",
        "agent_prompt": "Use tier-2 context packs",
        "workspace": {
            "agent_prompt": "Workspace scope",
            "projects": [
                {
                    "name": "default",
                    "agent_prompt": "Project scope",
                    "repos": [
                        {
                            "name": "api",
                            "url": "https://github.com/example/api.git",
                            "agent_prompt": "Repo scope",
                        }
                    ],
                }
            ],
        },
    }
    jsonschema.validate(instance, schema)


def test_repos_accepts_nested_anchor_lists_in_schema() -> None:
    schema = generate_json_schema(MetagitConfig)
    instance = {
        "name": "demo",
        "workspace": {
            "projects": [
                {
                    "name": "default",
                    "repos": [
                        [
                            {
                                "name": "a",
                                "url": "https://github.com/example/a.git",
                            },
                            {
                                "name": "b",
                                "url": "https://github.com/example/b.git",
                            },
                        ],
                        {
                            "name": "c",
                            "url": "https://github.com/example/c.git",
                        },
                    ],
                }
            ]
        },
    }
    jsonschema.validate(instance, schema)


def test_repo_metagit_yml_raw_documentation_block_validates() -> None:
    raw = """
name: metagit-cli
documentation:
  - README.md
  - https://metagit-ai.github.io/metagit-cli/
  - kind: confluence
    url: https://confluence.example.com/display/METAGIT/Docs
    tags:
      - playbook
workspace:
  projects:
    - name: default
      repos: []
"""
    instance = yaml.safe_load(raw)
    schema = generate_json_schema(MetagitConfig)
    jsonschema.validate(instance, schema)


def test_generated_schema_is_json_serializable() -> None:
    schema = generate_json_schema(MetagitConfig)
    json.dumps(schema)
