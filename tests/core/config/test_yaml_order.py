#!/usr/bin/env python
"""Tests for config YAML ordering helpers."""

from metagit.core.config.models import MetagitConfig
from metagit.core.config.yaml_order import order_payload
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import WorkspaceProject


def test_order_payload_puts_name_first_in_repo_entry() -> None:
    messy = {
        "description": "AWS account repos",
        "name": "billing",
        "url": "https://github.com/org/billing.git",
    }
    ordered = order_payload(messy, ProjectPath)
    assert list(ordered.keys())[:2] == ["name", "description"]


def test_order_payload_orders_workspace_project_fields() -> None:
    messy = {
        "repos": [{"description": "svc", "name": "api"}],
        "description": "platform",
        "name": "default",
    }
    ordered = order_payload(messy, WorkspaceProject)
    assert list(ordered.keys())[:2] == ["name", "description"]
    repo_keys = list(ordered["repos"][0].keys())
    assert repo_keys[0] == "name"


def test_order_payload_normalizes_agent_prompt_alias_to_field_order() -> None:
    payload = {
        "name": "demo",
        "workspace": {
            "projects": [
                {
                    "name": "default",
                    "agent_prompt": "Use tier-2 packs",
                    "repos": [],
                }
            ]
        },
    }
    ordered = order_payload(payload, MetagitConfig)
    project = ordered["workspace"]["projects"][0]
    assert "agent_instructions" in project
    assert list(project.keys()).index("name") < list(project.keys()).index(
        "agent_instructions"
    )
