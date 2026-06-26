#!/usr/bin/env python
"""Load repomix context profiles and execute repomix with scoped include globs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

import yaml
from pydantic import BaseModel, Field

from metagit import DATA_PATH

CompletedBytes = subprocess.CompletedProcess[bytes]
InvokeRepomix = Callable[[list[str], bool], CompletedBytes]


class RepomixProfileSpec(BaseModel):
    """One named profile: globs are relative to the target repository root."""

    include: list[str] = Field(..., min_length=1)
    exclude: list[str] = Field(default_factory=list)


class RepomixProfilesDocument(BaseModel):
    """Top-level shape of ``context_profiles.yaml``."""

    profiles: dict[str, RepomixProfileSpec]


class RepomixProfileService:
    """Load ``context_profiles.yaml`` and run repomix with profile include/exclude globs."""

    def __init__(
        self,
        *,
        profiles_path: Optional[Path] = None,
        repomix_executable: str = "repomix",
        invoke_repomix: Optional[InvokeRepomix] = None,
    ) -> None:
        self._profiles_path = profiles_path or Path(DATA_PATH) / "context_profiles.yaml"
        self._repomix_exe = repomix_executable
        self._invoke_repomix = invoke_repomix
        self._document = self._load_document(self._profiles_path)

    def _load_document(self, path: Path) -> RepomixProfilesDocument:
        if not path.is_file():
            raise FileNotFoundError(f"context profiles not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        if not isinstance(raw, dict):
            raise ValueError(f"invalid context profiles YAML (expected mapping): {path}")
        return RepomixProfilesDocument.model_validate(raw)

    @property
    def profiles_path(self) -> Path:
        return self._profiles_path

    def profile_names(self) -> list[str]:
        return sorted(self._document.profiles.keys())

    def get_profile(self, profile_name: str) -> RepomixProfileSpec:
        if profile_name not in self._document.profiles:
            raise KeyError(f"unknown repomix profile: {profile_name!r}")
        return self._document.profiles[profile_name]

    def build_repomix_argv(
        self,
        repo_path: str | Path,
        profile_name: str,
        *,
        output_path: Optional[str | Path],
        stdout: bool,
        style: str = "markdown",
        compress: bool = False,
    ) -> list[str]:
        """Assemble a repomix CLI argv for ``profile_name`` scoped to ``repo_path``."""
        profile = self.get_profile(profile_name)
        repo = Path(repo_path).expanduser().resolve()
        include_csv = ",".join(profile.include)
        argv: list[str] = [
            self._repomix_exe,
            str(repo),
            "--quiet",
            f"--style={style}",
            "--include",
            include_csv,
        ]
        if compress:
            argv.append("--compress")
        if profile.exclude:
            argv.extend(["--ignore", ",".join(profile.exclude)])
        if stdout:
            if output_path is not None:
                raise ValueError("output_path must be None when stdout is True")
            argv.append("--stdout")
        else:
            if output_path is None:
                raise ValueError("output_path is required when stdout is False")
            argv.extend(["--output", str(Path(output_path).expanduser().resolve())])
        return argv

    def _invoke_repomix_raw(
        self,
        argv: list[str],
        capture_stdout: bool,
    ) -> CompletedBytes:
        return subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def _run_repomix_process(
        self,
        argv: list[str],
        *,
        capture_stdout: bool,
    ) -> CompletedBytes:
        inner = self._invoke_repomix or self._invoke_repomix_raw
        return inner(argv, capture_stdout)

    def run_repomix(
        self,
        repo_path: str | Path,
        profile_name: str,
        *,
        output_path: Optional[str | Path],
        stdout: bool,
        style: str = "markdown",
        compress: bool = False,
        check_repomix_installed: bool = True,
    ) -> str | Path:
        """Execute repomix for ``profile_name``.

        Returns packed content as ``str`` when ``stdout=True``, otherwise the resolved output path.
        """
        if check_repomix_installed and shutil.which(self._repomix_exe) is None:
            raise FileNotFoundError(f"{self._repomix_exe!r} not found on PATH")
        argv = self.build_repomix_argv(
            repo_path,
            profile_name,
            output_path=output_path,
            stdout=stdout,
            style=style,
            compress=compress,
        )
        proc = self._run_repomix_process(argv, capture_stdout=stdout)
        if proc.returncode != 0:
            err = getattr(proc, "stderr", b"") or b""
            detail = err.decode("utf-8", errors="replace").strip()
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"repomix failed (exit {proc.returncode}){suffix}")

        if stdout:
            out = getattr(proc, "stdout", b"") or b""
            return out.decode("utf-8", errors="replace")

        resolved_out = Path(output_path).expanduser().resolve()
        return resolved_out


def default_repomix_profiles_path() -> Path:
    """Bundled ``context_profiles.yaml`` path under package data."""
    return Path(DATA_PATH) / "context_profiles.yaml"


__all__ = [
    "CompletedBytes",
    "InvokeRepomix",
    "RepomixProfileService",
    "RepomixProfileSpec",
    "RepomixProfilesDocument",
    "default_repomix_profiles_path",
]
