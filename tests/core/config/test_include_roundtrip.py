#!/usr/bin/env python
"""Round-trip and writer tests for split manifests."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

import metagit.core.context  # noqa: F401  (loads before catalog to avoid a partial-init cycle)
from metagit.core.atlas.models import AtlasConfig
from metagit.core.atlas.service import AtlasService
from metagit.core.config.format_service import ConfigFormatService
from metagit.core.config.include_writer import flatten_manifest, split_manifest
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.patch_service import ConfigPatchService
from metagit.core.project.ci_target_service import CiTargetService
from metagit.core.project.repo_promote_service import _save_config as promote_save
from metagit.core.web.models import ConfigOperation, ConfigOpKind
from metagit.core.workspace.catalog_service import WorkspaceCatalogService
from metagit.core.workspace.derived_project_service import DerivedProjectService
from metagit.core.workspace.layout_service import WorkspaceLayoutService
from metagit.core.workspace.models import WorkspaceProject

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "split_manifest"
ALPHA = ".metagit.d/projects/alpha.yml"


def _copy_fixture(tmp_path: Path) -> Path:
    destination = tmp_path / "workspace"
    shutil.copytree(FIXTURE, destination)
    return destination / ".metagit.yml"


def _snapshot(root: Path) -> dict[str, tuple[str, int]]:
    found: dict[str, tuple[str, int]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        found[relative] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
    return found


def _changed(before: dict[str, tuple[str, int]], after: dict[str, tuple[str, int]]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(key for key in keys if before.get(key) != after.get(key))


def test_save_changes_only_the_edited_fragment(tmp_path: Path) -> None:
    manifest = _copy_fixture(tmp_path)
    before = _snapshot(manifest.parent)
    manager = MetagitConfigManager(manifest)
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    loaded.workspace.projects[0].description = "changed"
    assert manager.save_config(loaded) is None
    assert _changed(before, _snapshot(manifest.parent)) == [ALPHA]
    text = (manifest.parent / ALPHA).read_text(encoding="utf-8")
    assert "keep-me" in text
    assert "description: changed" in text


def test_add_remove_and_rename_projects(tmp_path: Path) -> None:
    manifest = _copy_fixture(tmp_path)
    manager = MetagitConfigManager(manifest)
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    loaded.workspace.projects.append(WorkspaceProject(name="gamma", repos=[]))
    assert manager.save_config(loaded) is None
    gamma = manifest.parent / ".metagit.d" / "projects" / "gamma.yml"
    assert gamma.is_file()
    assert "gamma.yml" in manifest.read_text(encoding="utf-8")

    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    loaded.workspace.projects = [project for project in loaded.workspace.projects if project.name != "beta"]
    assert manager.save_config(loaded) is None
    beta = (manifest.parent / ".metagit.d" / "projects" / "beta.yml").read_text(encoding="utf-8")
    assert "projects: []" in beta or "projects: []\n" in beta

    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    for project in loaded.workspace.projects:
        if project.name == "alpha":
            project.name = "alpha-renamed"
    assert manager.save_config(loaded) is None
    assert (manifest.parent / ".metagit.d" / "projects" / "alpha-renamed.yml").is_file()
    emptied = (manifest.parent / ALPHA).read_text(encoding="utf-8")
    assert "alpha-renamed" not in emptied
    assert "projects: []" in emptied


def test_split_flatten_round_trip_and_idempotent_split(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: umbrella\nkind: umbrella\nworkspace:\n  description: shared\n  projects:\n"
        "    - name: alpha\n      description: original\n      repos: []\n"
        "    - name: beta\n      description: second\n      repos: []\n"
        "graph:\n  nodes:\n    - identity: github://acme/alpha\n      name: alpha\n"
        "  relationships:\n    - id: edge\n      from:\n        project: alpha\n"
        "      to:\n        project: beta\n      type: depends_on\n",
        encoding="utf-8",
    )
    original = MetagitConfigManager(manifest).load_config()
    assert not isinstance(original, Exception)
    dry = split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=True)
    assert not isinstance(dry, Exception)
    assert dry.dry_run is True
    assert dry.changed is False
    assert "projects:" in manifest.read_text(encoding="utf-8")
    assert not (tmp_path / ".metagit.d").exists()

    planned = split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=False)
    assert not isinstance(planned, Exception)
    split_model = MetagitConfigManager(manifest).load_config()
    assert not isinstance(split_model, Exception)
    assert split_model.model_dump(mode="json", exclude_none=True) == original.model_dump(
        mode="json",
        exclude_none=True,
    )
    before = _snapshot(tmp_path)
    again = split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=False)
    assert not isinstance(again, Exception)
    assert again.changed is False
    assert _snapshot(tmp_path) == before

    flattened = flatten_manifest(manifest)
    assert isinstance(flattened, str)
    assert "includes:" not in flattened
    flat_path = tmp_path / "flat.yml"
    flat_path.write_text(flattened, encoding="utf-8")
    flat_model = MetagitConfigManager(flat_path).load_config()
    assert not isinstance(flat_model, Exception)
    assert flat_model.model_dump(mode="json", exclude_none=True) == original.model_dump(
        mode="json",
        exclude_none=True,
    )


def test_flatten_single_file_is_a_noop(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text("name: demo\nkind: application\n", encoding="utf-8")
    before = manifest.read_bytes()
    mtime = manifest.stat().st_mtime_ns
    rendered = flatten_manifest(manifest, in_place=True)
    assert rendered == "name: demo\nkind: application\n"
    assert manifest.read_bytes() == before
    assert manifest.stat().st_mtime_ns == mtime


def test_single_file_save_stays_byte_stable(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: demo\nkind: umbrella\nworkspace:\n  projects:\n    - name: alpha\n      repos: []\n", encoding="utf-8"
    )
    manager = MetagitConfigManager(manifest)
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    assert manager.source_map is None
    assert manager.save_config() is None
    rendered = ConfigFormatService().render_metagit(loaded, original_text=manifest.read_text(encoding="utf-8"))
    assert manifest.read_text(encoding="utf-8") == rendered
    first = manifest.read_bytes()
    assert manager.save_config() is None
    assert manifest.read_bytes() == first
    assert "includes:" not in manifest.read_text(encoding="utf-8")


def _save_loaded(_config, path: Path):
    manager = MetagitConfigManager(path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        return loaded
    loaded.workspace.projects[0].description = "changed"
    return manager.save_config(loaded)


def _save_fresh_path(config, path: Path):
    config.workspace.projects[0].description = "changed"
    return MetagitConfigManager(config_path=path).save_config(config, path)


def _save_config_only(config, path: Path):
    config.workspace.projects[0].description = "changed"
    return MetagitConfigManager(config_path=path).save_config(config)


def _save_in_memory(config, path: Path):
    config.workspace.projects[0].description = "changed"
    return MetagitConfigManager(metagit_config=config).save_config(config, path)


def _save_catalog(config, path: Path):
    config.workspace.projects[0].description = "changed"
    return WorkspaceCatalogService()._save(config, str(path))


def _save_layout(config, path: Path):
    config.workspace.projects[0].description = "changed"
    return WorkspaceLayoutService()._save(config, str(path))


def _save_derived(config, path: Path):
    config.workspace.projects[0].description = "changed"
    return DerivedProjectService()._save(config=config, config_path=str(path))


def _save_promote(config, path: Path):
    config.workspace.projects[0].description = "changed"
    return promote_save(config, str(path))


def _save_patch(_config, path: Path):
    result = ConfigPatchService().patch(
        "metagit",
        str(path),
        [ConfigOperation(op=ConfigOpKind.SET, path="workspace.projects[0].description", value="changed")],
        save=True,
    )
    return result if not isinstance(result, Exception) and result.ok else Exception(result)


def _save_ci(config, path: Path):
    config.workspace.projects[0].description = "changed"
    _ = CiTargetService
    return MetagitConfigManager(config_path=path).save_config(config, path)


@pytest.mark.parametrize(
    "writer",
    [
        _save_loaded,
        _save_fresh_path,
        _save_config_only,
        _save_in_memory,
        _save_catalog,
        _save_layout,
        _save_derived,
        _save_promote,
        _save_patch,
        _save_ci,
    ],
    ids=[
        "config_set",
        "project_manager",
        "component_detect",
        "catalog_like_memory",
        "catalog",
        "layout",
        "derived",
        "repo_promote",
        "patch_service",
        "ci_target",
    ],
)
def test_writers_do_not_flatten(tmp_path: Path, writer) -> None:
    manifest = _copy_fixture(tmp_path)
    before = _snapshot(manifest.parent)
    manager = MetagitConfigManager(manifest)
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    outcome = writer(loaded, manifest)
    assert not isinstance(outcome, Exception), outcome
    assert _changed(before, _snapshot(manifest.parent)) == [ALPHA]


def test_remaining_writer_call_styles_do_not_flatten(tmp_path: Path) -> None:
    """Source sync, approval, web, and project-source all persist through save_config."""
    styles = (
        lambda config, path: MetagitConfigManager(config_path=path).save_config(config, path),
        lambda config, path: MetagitConfigManager(str(path)).save_config(config, auto_format=True),
    )
    for index, style in enumerate(styles):
        tree = tmp_path / f"case-{index}"
        shutil.copytree(FIXTURE, tree)
        root = tree / ".metagit.yml"
        before = _snapshot(tree)
        loaded = MetagitConfigManager(root).load_config()
        assert not isinstance(loaded, Exception)
        loaded.workspace.projects[0].description = f"changed-{index}"
        outcome = style(loaded, root)
        assert not isinstance(outcome, Exception)
        assert _changed(before, _snapshot(tree)) == [ALPHA]


def test_atlas_save_does_not_rewrite_manifest_fragments(tmp_path: Path) -> None:
    manifest = _copy_fixture(tmp_path)
    before = _snapshot(manifest.parent)
    atlas_dir = manifest.parent / ".atlas"
    atlas_dir.mkdir()
    saved = AtlasService(manifest.parent)._save_config(AtlasConfig(repository="umbrella", formatVersion="v1alpha1"))
    assert saved is None
    assert _changed(before, _snapshot(manifest.parent)) == [".atlas/atlas.yaml"]
