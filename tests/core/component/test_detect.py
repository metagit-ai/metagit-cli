#!/usr/bin/env python
"""Tests for ComponentDetector detect/init (RFC-0031)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from metagit.core.component.detect import ComponentDetector
from metagit.core.config.manager import MetagitConfigManager


def _write_umbrella(
    tmp_path: Path,
    *,
    repo_rel: str = "repo",
    components_yaml: str = "",
) -> Path:
    repo_dir = tmp_path / repo_rel
    repo_dir.mkdir(parents=True, exist_ok=True)
    extra = ""
    if components_yaml:
        extra = "\n" + components_yaml
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: umbrella",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: core",
                f"          path: ./{repo_rel}{extra}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return repo_dir


def _load(tmp_path: Path):
    manager = MetagitConfigManager(config_path=str(tmp_path / ".metagit.yml"))
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception), loaded
    return loaded


def _detect(tmp_path: Path, **kwargs):
    config = _load(tmp_path)
    return ComponentDetector().detect(config, definition_root=str(tmp_path), **kwargs)


def _by_name(payload: dict) -> dict[str, dict]:
    return {row["name"]: row for row in payload["candidates"]}


def test_apps_web_and_api_are_high_candidates(tmp_path: Path) -> None:
    repo = _write_umbrella(tmp_path)
    (repo / "apps" / "web").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "apps" / "api").mkdir(parents=True)
    (repo / "apps" / "api" / "pyproject.toml").write_text("[project]\nname='api'\n", encoding="utf-8")

    payload = _detect(tmp_path)
    names = _by_name(payload)
    assert set(names) == {"web", "api"}
    assert names["web"]["path"] == "apps/web"
    assert names["web"]["kind"] == "application"
    assert names["web"]["language"] == "typescript"
    assert names["web"]["confidence"] == "high"
    assert "package.json" in names["web"]["markers"]
    assert names["web"]["already_catalogued"] is False
    assert names["api"]["path"] == "apps/api"
    assert names["api"]["kind"] == "application"
    assert names["api"]["language"] == "python"
    assert names["api"]["confidence"] == "high"
    assert "pyproject.toml" in names["api"]["markers"]


def test_nested_src_package_json_is_not_a_candidate(tmp_path: Path) -> None:
    repo = _write_umbrella(tmp_path)
    web = repo / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}\n", encoding="utf-8")
    nested = web / "src"
    nested.mkdir()
    (nested / "package.json").write_text("{}\n", encoding="utf-8")

    payload = _detect(tmp_path)
    paths = {row["path"] for row in payload["candidates"]}
    assert paths == {"apps/web"}
    assert "apps/web/src" not in paths


def test_catalogued_path_marked_and_omitted_from_apply(tmp_path: Path) -> None:
    repo = _write_umbrella(
        tmp_path,
        components_yaml=(
            "          components:\n"
            "            - name: web\n"
            "              path: apps/web\n"
            "              kind: application"
        ),
    )
    (repo / "apps" / "web").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "apps" / "api").mkdir(parents=True)
    (repo / "apps" / "api" / "pyproject.toml").write_text("[project]\nname='api'\n", encoding="utf-8")

    detector = ComponentDetector()
    config = _load(tmp_path)
    payload = detector.detect(config, definition_root=str(tmp_path))
    names = _by_name(payload)
    assert names["web"]["already_catalogued"] is True
    assert names["api"]["already_catalogued"] is False

    manifest = tmp_path / ".metagit.yml"
    before = manifest.read_text(encoding="utf-8")
    saved = detector.apply_candidates(
        config,
        payload["candidates"],
        config_path=str(manifest),
    )
    assert not isinstance(saved, Exception), saved
    after = manifest.read_text(encoding="utf-8")
    reloaded = _load(tmp_path)
    repo_entry = reloaded.workspace.projects[0].repos[0]
    names_written = [item.name for item in repo_entry.components]
    assert names_written.count("web") == 1
    assert "api" in names_written
    assert "path: apps/web" in before
    assert after.count("name: web") == before.count("name: web")


def test_init_apply_writes_components(tmp_path: Path) -> None:
    repo = _write_umbrella(tmp_path)
    (repo / "apps" / "web").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")

    detector = ComponentDetector()
    config = _load(tmp_path)
    created = detector.init_component(
        config,
        "apps/web",
        name=None,
        kind="application",
        project="platform",
        repo="core",
    )
    assert not isinstance(created, Exception)
    assert created.name == "web"
    assert created.path == "apps/web"
    assert created.kind == "application"

    saved = detector.apply_candidates(
        config,
        [
            {
                "name": created.name,
                "path": created.path,
                "kind": created.kind,
                "language": created.language,
                "project": "platform",
                "repo": "core",
                "already_catalogued": False,
            }
        ],
        config_path=str(tmp_path / ".metagit.yml"),
    )
    assert not isinstance(saved, Exception), saved
    reloaded = _load(tmp_path)
    specs = reloaded.workspace.projects[0].repos[0].components
    assert len(specs) == 1
    assert specs[0].name == "web"
    assert specs[0].path == "apps/web"
    assert specs[0].kind == "application"


def test_empty_repo_has_empty_candidates(tmp_path: Path) -> None:
    _write_umbrella(tmp_path)
    payload = _detect(tmp_path)
    assert payload["candidates"] == []


def test_detect_without_apply_does_not_write(tmp_path: Path) -> None:
    repo = _write_umbrella(tmp_path)
    (repo / "apps" / "web").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / ".metagit.yml"
    before = manifest.read_text(encoding="utf-8")
    _detect(tmp_path)
    assert manifest.read_text(encoding="utf-8") == before
    reloaded = _load(tmp_path)
    assert reloaded.workspace.projects[0].repos[0].components == []


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "metagit.cli.main", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_detect_json_two_high_candidates(tmp_path: Path) -> None:
    repo = _write_umbrella(tmp_path)
    (repo / "apps" / "web").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "apps" / "api").mkdir(parents=True)
    (repo / "apps" / "api" / "pyproject.toml").write_text("[project]\nname='api'\n", encoding="utf-8")

    result = _run(
        "component",
        "detect",
        "-c",
        str(tmp_path / ".metagit.yml"),
        "--json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    names = {row["name"] for row in payload["candidates"]}
    assert names == {"web", "api"}
    assert "components:" not in (tmp_path / ".metagit.yml").read_text(encoding="utf-8")


def test_cli_init_apply_writes_components(tmp_path: Path) -> None:
    repo = _write_umbrella(tmp_path)
    (repo / "apps" / "web").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")

    result = _run(
        "component",
        "init",
        "apps/web",
        "--project",
        "platform",
        "--repo",
        "core",
        "--kind",
        "application",
        "--apply",
        "--json",
        "-c",
        str(tmp_path / ".metagit.yml"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["name"] == "web"
    reloaded = _load(tmp_path)
    specs = reloaded.workspace.projects[0].repos[0].components
    assert [item.name for item in specs] == ["web"]


def test_cli_empty_repo_exits_zero(tmp_path: Path) -> None:
    _write_umbrella(tmp_path)
    result = _run(
        "component",
        "detect",
        "-c",
        str(tmp_path / ".metagit.yml"),
        "--json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["candidates"] == []
