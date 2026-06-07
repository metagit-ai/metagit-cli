#!/usr/bin/env python
"""Generate JSON Schema for agent template manifests."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.agent.models import AgentTemplateManifest


def agent_template_json_schema() -> dict[str, object]:
    """Return the JSON Schema dict for ``AgentTemplateManifest``."""
    return AgentTemplateManifest.model_json_schema()


def write_agent_template_schema(output_path: Path) -> Path:
    """Write agent template JSON Schema to disk."""
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = agent_template_json_schema()
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
