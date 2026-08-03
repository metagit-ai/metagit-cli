#!/usr/bin/env python
"""Interactive FuzzyFinder selection for workspace project names."""

from __future__ import annotations

from typing import Union

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def select_project_name(
    project_names: list[str],
    *,
    menu_length: int = 10,
) -> Union[str, None, Exception]:
    """Run FuzzyFinder over project names.

    Returns selected name, None if cancelled, or Exception on error.
    """
    names = [n for n in project_names if n]
    if not names:
        return ValueError("No workspace projects are defined in .metagit.yml")
    config = FuzzyFinderConfig(
        items=sorted(names),
        prompt_text="Search projects: ",
        max_results=menu_length,
        total_count=len(names),
        query_mode_label="matches",
        score_threshold=60.0,
        highlight_color="bold white bg:#0066cc",
        normal_color="cyan",
        prompt_color="bold green",
        separator_color="gray",
        enable_preview=False,
    )
    selected = FuzzyFinder(config).run()
    if isinstance(selected, Exception):
        return selected
    if selected is None:
        return None
    if isinstance(selected, str):
        return selected
    return ValueError(f"Unexpected project selection type: {type(selected)!r}")
