#!/usr/bin/env python
"""Tests for ``RepomixProfileService``."""

from pathlib import Path
from subprocess import CompletedProcess

import pytest
import yaml

from metagit.core.context.repomix_profile_service import RepomixProfileService


_MINIMAL_PROFILES = {
    "profiles": {
        "bugfix-local": {
            "include": ["src/**"],
            "exclude": [],
        },
        "cross-repo-impact": {
            "include": [".metagit.yml"],
            "exclude": [],
        },
    }
}


def test_bundled_profiles_include_rewrite_profiles() -> None:
  from metagit import DATA_PATH

  profiles_path = Path(DATA_PATH) / "context_profiles.yaml"
  svc = RepomixProfileService(profiles_path=profiles_path)
  source_argv = svc.build_repomix_argv(
    repo_path=Path("/tmp/source"),
    profile_name="rewrite-source",
    output_path=None,
    stdout=True,
  )
  assert "src/**" in source_argv[source_argv.index("--include") + 1]
  target_argv = svc.build_repomix_argv(
    repo_path=Path("/tmp/target"),
    profile_name="rewrite-target",
    output_path=None,
    stdout=True,
  )
  assert "crates/**" in target_argv[target_argv.index("--include") + 1]


def test_unknown_profile_raises(tmp_path: Path) -> None:
    yaml_file = tmp_path / "context_profiles.yaml"
    yaml_file.write_text(yaml.safe_dump(_MINIMAL_PROFILES), encoding="utf-8")
    svc = RepomixProfileService(profiles_path=yaml_file)
    with pytest.raises(KeyError, match="no-such"):
        svc.build_repomix_argv(
            repo_path=tmp_path,
            profile_name="no-such",
            output_path=None,
            stdout=True,
        )


def test_build_argv_include_comma_join(tmp_path: Path) -> None:
    yaml_file = tmp_path / "context_profiles.yaml"
    yaml_file.write_text(yaml.safe_dump(_MINIMAL_PROFILES), encoding="utf-8")
    svc = RepomixProfileService(profiles_path=yaml_file)
    argv = svc.build_repomix_argv(
        repo_path=tmp_path / "repo",
        profile_name="cross-repo-impact",
        output_path=None,
        stdout=True,
    )
    assert argv[0] == "repomix"
    assert argv[1] == str(tmp_path / "repo")
    idx_include = argv.index("--include")
    assert argv[idx_include + 1] == ".metagit.yml"
    assert "--stdout" in argv


def test_build_argv_exclude_when_present(tmp_path: Path) -> None:
    data = {
        "profiles": {
            "z": {
                "include": ["a/**", "b.md"],
                "exclude": ["**/vendor/**"],
            },
        },
    }
    yaml_file = tmp_path / "context_profiles.yaml"
    yaml_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    svc = RepomixProfileService(profiles_path=yaml_file)
    argv = svc.build_repomix_argv(
        repo_path=tmp_path,
        profile_name="z",
        output_path=tmp_path / "out.md",
        stdout=False,
    )
    idx_ignore = argv.index("--ignore")
    assert argv[idx_ignore + 1] == "**/vendor/**"
    idx_o = argv.index("--output")
    assert argv[idx_o + 1] == str(tmp_path / "out.md")


def test_build_argv_writes_file_not_stdout(tmp_path: Path) -> None:
    yaml_file = tmp_path / "context_profiles.yaml"
    yaml_file.write_text(yaml.safe_dump(_MINIMAL_PROFILES), encoding="utf-8")
    svc = RepomixProfileService(profiles_path=yaml_file)
    out = tmp_path / "packed.md"
    argv = svc.build_repomix_argv(
        repo_path=tmp_path,
        profile_name="bugfix-local",
        output_path=out,
        stdout=False,
    )
    assert "--stdout" not in argv
    assert "--output" in argv
    assert str(out) in argv


def test_run_repomix_injects_runner(tmp_path: Path) -> None:
    yaml_file = tmp_path / "context_profiles.yaml"
    yaml_file.write_text(yaml.safe_dump(_MINIMAL_PROFILES), encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_run(argv: list[str], capture_stdout: bool) -> CompletedProcess[bytes]:
        captured["argv"] = argv
        captured["capture_stdout"] = capture_stdout
        return CompletedProcess(argv, returncode=0)

    svc = RepomixProfileService(profiles_path=yaml_file, invoke_repomix=fake_run)
    svc.run_repomix(
        repo_path=tmp_path,
        profile_name="bugfix-local",
        stdout=False,
        output_path=tmp_path / "out.xml",
        check_repomix_installed=False,
    )
    assert isinstance(captured["argv"], list)
    assert captured["capture_stdout"] is False


def test_run_stdout_returns_string(tmp_path: Path) -> None:
    yaml_file = tmp_path / "context_profiles.yaml"
    yaml_file.write_text(yaml.safe_dump(_MINIMAL_PROFILES), encoding="utf-8")

    def fake_run(argv: list[str], _: bool) -> CompletedProcess[bytes]:
        assert "--stdout" in argv
        return CompletedProcess(argv, returncode=0, stdout=b"packed")

    svc = RepomixProfileService(profiles_path=yaml_file, invoke_repomix=fake_run)
    assert svc.run_repomix(
        repo_path=tmp_path,
        profile_name="bugfix-local",
        stdout=True,
        output_path=None,
        check_repomix_installed=False,
    ) == "packed"


def test_run_failure_raises_runtime_error(tmp_path: Path) -> None:
    yaml_file = tmp_path / "context_profiles.yaml"
    yaml_file.write_text(yaml.safe_dump(_MINIMAL_PROFILES), encoding="utf-8")

    def fake_run(argv: list[str], _: bool) -> CompletedProcess[bytes]:
        return CompletedProcess(
            argv,
            returncode=1,
            stderr=b"bad",
        )

    svc = RepomixProfileService(profiles_path=yaml_file, invoke_repomix=fake_run)
    with pytest.raises(RuntimeError, match="repomix failed"):
        svc.run_repomix(
            repo_path=tmp_path,
            profile_name="bugfix-local",
            stdout=True,
            output_path=None,
            check_repomix_installed=False,
        )


def test_profiles_yaml_shipped_contains_bundled_profiles() -> None:
    svc = RepomixProfileService()
    names = sorted(svc.profile_names())
    assert names == [
        "bugfix-local",
        "config-edit",
        "cross-repo-impact",
        "rewrite-source",
        "rewrite-target",
    ]
