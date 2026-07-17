#!/usr/bin/env python
"""
Skills installation helpers.
"""

from metagit.core.skills.installer import (
    SUPPORTED_TARGETS,
    autodetect_targets,
    install_mcp_for_targets,
    install_skills_for_targets,
    list_bundled_skills,
    resolve_hermes_home,
    resolve_metagit_launch,
    resolve_project_install_root,
    resolve_skill_names,
    resolve_targets,
    skill_markdown,
    target_paths_for,
)

__all__ = [
    "SUPPORTED_TARGETS",
    "autodetect_targets",
    "install_mcp_for_targets",
    "install_skills_for_targets",
    "list_bundled_skills",
    "resolve_hermes_home",
    "resolve_metagit_launch",
    "resolve_project_install_root",
    "resolve_skill_names",
    "resolve_targets",
    "skill_markdown",
    "target_paths_for",
]
