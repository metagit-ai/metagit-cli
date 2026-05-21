#!/usr/bin/env python
"""
Materialize symlinked project mounts into full directory trees.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from tqdm import tqdm


def collect_file_copy_jobs(source: Path) -> list[tuple[Path, Path]]:
    """Return (source_file, destination_file) pairs for a recursive copy."""
    root = source.resolve()
    if not root.is_dir():
        if root.is_file():
            return [(root, root)]
        return []
    jobs: list[tuple[Path, Path]] = []
    for dirpath, _, filenames in os.walk(root, followlinks=True):
        base = Path(dirpath)
        rel = base.relative_to(root)
        for name in filenames:
            src = base / name
            jobs.append((src, rel / name))
    return jobs


def materialize_symlink_mount(
    mount: Path,
    *,
    position: int = 0,
    repo_label: str = "",
) -> tuple[bool, Optional[str]]:
    """
    Replace a symlink mount with a full copy of its resolved target.

    Returns (changed, error_message). ``changed`` is False when the mount is not
    a symlink (already material or missing).
    """
    if not mount.is_symlink():
        return False, None

    source = mount.resolve()
    if not source.exists():
        return False, f"hydrate target does not exist: {source}"

    label = repo_label or mount.name
    mount.unlink()

    if source.is_dir():
        mount.mkdir(parents=True, exist_ok=True)
        jobs = collect_file_copy_jobs(source)
        if not jobs:
            tqdm.write(f"  💧 {label}: empty directory (materialized)")
            return True, None
        desc = f"  💧 {label}"
        bar_format = (
            "{l_bar}{bar}| {n_fmt}/{total_fmt} files [{elapsed}<{remaining}]{r_bar}"
        )
        with tqdm(
            total=len(jobs),
            desc=desc,
            position=position,
            unit="file",
            bar_format=bar_format,
            leave=True,
        ) as pbar:
            for src_file, rel in jobs:
                dest = mount / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest, follow_symlinks=True)
                name = rel.name if len(str(rel)) <= 48 else f"…{rel.name}"
                pbar.set_postfix_str(name, refresh=False)
                pbar.update(1)
        return True, None

    mount.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, mount, follow_symlinks=True)
    with tqdm(
        total=1,
        desc=f"  💧 {label}",
        position=position,
        bar_format="{l_bar}Copied{r_bar}",
    ) as pbar:
        pbar.update(1)
    return True, None
