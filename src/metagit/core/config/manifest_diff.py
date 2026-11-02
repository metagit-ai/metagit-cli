#!/usr/bin/env python
"""Compare two manifests and hash the composed document."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.yaml_roundtrip import build_roundtrip_yaml
from metagit.manifest import load_composed

DiffKind = Literal["value", "added", "removed", "type", "whitespace-only"]
DiffMode = Literal["raw", "model"]


@dataclass(frozen=True)
class ManifestDifference:
    """One path that is not the same on both sides."""

    path: str
    kind: DiffKind

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "kind": self.kind}


def content_sha256(path: str | Path) -> str:
    """SHA-256 of the canonical JSON of :func:`metagit.manifest.load_composed`."""
    payload = json.dumps(
        load_composed(path),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def diff_manifests(
    left: str,
    right: str,
    *,
    mode: DiffMode = "raw",
    cwd: Path | None = None,
) -> list[ManifestDifference]:
    """Return differing paths between two manifests or ``rev:path`` git specs."""
    base = cwd or _infer_cwd(left, right)
    return diff_values(load_manifest_spec(left, mode=mode, cwd=base), load_manifest_spec(right, mode=mode, cwd=base))


def load_manifest_spec(spec: str, *, mode: DiffMode, cwd: Path) -> dict[str, Any]:
    """Load one side of a diff. A missing path that contains ``:`` is a git spec."""
    materialized = materialize_manifest_spec(spec, cwd=cwd)
    if isinstance(materialized, Exception):
        raise materialized
    if mode == "model":
        loaded = MetagitConfigManager(config_path=materialized).load_config()
        if isinstance(loaded, Exception):
            raise loaded
        dumped = loaded.model_dump(mode="json", by_alias=True, exclude_none=True)
        return dumped if isinstance(dumped, dict) else {}
    return load_composed(materialized)


def materialize_manifest_spec(spec: str, *, cwd: Path) -> Path | Exception:
    """Return a filesystem path for a manifest path or ``rev:path`` git spec."""
    direct = _existing_file(spec, cwd)
    if direct is not None:
        return direct
    if ":" not in spec:
        return FileNotFoundError(f"manifest not found: {spec}")
    rev, _, git_path = spec.partition(":")
    if not rev or not git_path:
        return FileNotFoundError(f"manifest not found: {spec}")
    try:
        return _materialize_git(rev, git_path, cwd)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f" ({detail})" if detail else ""
        return FileNotFoundError(f"could not read git spec {spec}{suffix}")


def diff_values(left: Any, right: Any, prefix: str = "") -> list[ManifestDifference]:
    """Walk two JSON-like trees and classify each difference."""
    if _missing_pair(left, right):
        return []
    if left is None and right is not None:
        return [ManifestDifference(prefix or "$", "added")]
    if right is None and left is not None:
        return [ManifestDifference(prefix or "$", "removed")]
    if type(left) is not type(right):
        if _whitespace_only(left, right):
            return [ManifestDifference(prefix or "$", "whitespace-only")]
        return [ManifestDifference(prefix or "$", "type")]
    if isinstance(left, dict):
        found: list[ManifestDifference] = []
        keys = list(dict.fromkeys([*left.keys(), *right.keys()]))
        for key in keys:
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in left:
                found.append(ManifestDifference(child, "added"))
            elif key not in right:
                found.append(ManifestDifference(child, "removed"))
            else:
                found.extend(diff_values(left[key], right[key], child))
        return found
    if isinstance(left, list):
        found = []
        shared = min(len(left), len(right))
        for index in range(shared):
            found.extend(diff_values(left[index], right[index], f"{prefix}[{index}]"))
        for index in range(shared, len(left)):
            found.append(ManifestDifference(f"{prefix}[{index}]", "removed"))
        for index in range(shared, len(right)):
            found.append(ManifestDifference(f"{prefix}[{index}]", "added"))
        return found
    if left == right:
        return []
    if _whitespace_only(left, right):
        return [ManifestDifference(prefix or "$", "whitespace-only")]
    return [ManifestDifference(prefix or "$", "value")]


def _missing_pair(left: Any, right: Any) -> bool:
    return left is None and right is None


def _whitespace_only(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str) or left == right:
        return False
    return "".join(left.split()) == "".join(right.split())


def _infer_cwd(left: str, right: str) -> Path:
    """Use the directory of a concrete manifest path so git specs resolve there."""
    for spec in (left, right):
        found = _existing_file(spec, Path.cwd())
        if found is not None:
            return found.parent
    return Path.cwd()


def _existing_file(spec: str, cwd: Path) -> Path | None:
    candidates = [Path(spec)]
    if not Path(spec).is_absolute():
        candidates.append(cwd / spec)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _materialize_git(rev: str, git_path: str, cwd: Path) -> Path:
    destination = Path(tempfile.mkdtemp(prefix="metagit-diff-"))
    root_text = _git_show(cwd, rev, git_path)
    manifest_path = destination / Path(git_path).name
    manifest_path.write_text(root_text, encoding="utf-8")
    loaded = build_roundtrip_yaml().load(root_text)
    includes = loaded.get("includes") if isinstance(loaded, dict) else None
    if not isinstance(includes, list):
        return manifest_path
    manifest_dir = Path(git_path).parent
    for pattern in includes:
        _fetch_include(cwd, rev, manifest_dir, str(pattern), destination)
    return manifest_path


def _fetch_include(cwd: Path, rev: str, manifest_dir: Path, pattern: str, destination: Path) -> None:
    git_pattern = (manifest_dir / pattern).as_posix() if str(manifest_dir) not in {"", "."} else pattern
    if any(token in pattern for token in ("*", "?", "[")):
        listing = _git_lines(cwd, ["ls-tree", "-r", "--name-only", rev])
        prefix = "" if str(manifest_dir) in {"", "."} else f"{manifest_dir.as_posix()}/"
        for name in listing:
            if not name.startswith(prefix):
                continue
            relative = name[len(prefix) :]
            if Path(relative).match(pattern) or Path(relative).match(Path(pattern).name):
                text = _git_show(cwd, rev, name)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
        return
    text = _git_show(cwd, rev, git_pattern)
    target = destination / pattern
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _git_show(cwd: Path, rev: str, git_path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), "show", f"{rev}:{git_path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _git_lines(cwd: Path, args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def composed_diff(left: Path, right: Path) -> list[ManifestDifference] | Exception:
    """Diff two on-disk manifests in raw mode."""
    try:
        return diff_values(load_composed(left), load_composed(right))
    except Exception as exc:
        return exc
