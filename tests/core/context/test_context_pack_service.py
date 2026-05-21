#!/usr/bin/env python
"""
Unit tests for metagit.core.context.context_pack_service.ContextPackService.
"""

import json
from pathlib import Path

from git import Repo

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.context_pack_service import ContextPackService


def _fixture(tmp_path: Path):
    repo_dir = tmp_path / "demo" / "svc"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: pack-svc-test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manager = MetagitConfigManager(config_path=tmp_path / ".metagit.yml")
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    root = str(tmp_path.resolve())
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    return loaded, root, cfg_path


def _load_config(workspace_root: Path):
    manager = MetagitConfigManager(config_path=workspace_root / ".metagit.yml")
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    return loaded


def _write_two_project_workspace(tmp_path: Path) -> Path:
    """Two projects with one git repo each for filter assertions."""
    for rel in ("alpha/r1", "beta/r2"):
        repo_dir = tmp_path / rel
        repo_dir.mkdir(parents=True)
        Repo.init(repo_dir)

    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: ctx-pack-multi",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos:",
                "        - name: r1",
                "          path: alpha/r1",
                "          sync: true",
                "    - name: beta",
                "      repos:",
                "        - name: r2",
                "          path: beta/r2",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_tier_zero_returns_map_no_cards(tmp_path: Path) -> None:
    cfg, root, cfg_path = _fixture(tmp_path)
    pack = ContextPackService().pack(
        cfg,
        cfg_path,
        root,
        tier=0,
        active_project="demo",
    )
    assert pack.ok is True
    assert pack.tier == 0
    assert pack.workspace_name == cfg.name == "pack-svc-test"
    assert pack.map is not None
    assert pack.cards is None
    assert pack.map.repo_count >= 1
    assert pack.map.active_project == "demo"
    assert isinstance(pack.token_estimate, int)
    assert pack.token_estimate >= 0


def test_tier_one_returns_map_and_cards(tmp_path: Path) -> None:
    workspace_root = _write_two_project_workspace(tmp_path)
    config = _load_config(workspace_root)
    config_path = str(workspace_root / ".metagit.yml")
    root = str(workspace_root.resolve())

    pack = ContextPackService().pack(
        config,
        config_path,
        root,
        tier=1,
        max_cards=50,
    )
    assert pack.tier == 1
    assert pack.workspace_name == config.name == "ctx-pack-multi"
    assert pack.map is not None
    assert pack.cards is not None
    assert len(pack.cards) == 2
    projects = {c.project_name for c in pack.cards}
    assert projects == {"alpha", "beta"}
    assert isinstance(pack.token_estimate, int)
    assert pack.token_estimate >= 0


def test_tier_one_single_repo_filter(tmp_path: Path) -> None:
    cfg, root, cfg_path = _fixture(tmp_path)
    pack = ContextPackService().pack(
        cfg,
        cfg_path,
        root,
        tier=1,
        project_name="demo",
        repo_name="svc",
    )
    assert pack.tier == 1
    assert pack.map is not None
    assert pack.cards is not None
    assert len(pack.cards) == 1
    assert pack.cards[0].repo_name == "svc"


def test_tier_one_project_filter_limits_cards(tmp_path: Path) -> None:
    workspace_root = _write_two_project_workspace(tmp_path)
    config = _load_config(workspace_root)
    config_path = str(workspace_root / ".metagit.yml")
    root = str(workspace_root.resolve())

    pack = ContextPackService().pack(
        config,
        config_path,
        root,
        tier=1,
        project_name="alpha",
        max_cards=50,
    )
    assert pack.cards is not None
    assert len(pack.cards) == 1
    assert pack.cards[0].project_name == "alpha"
    assert pack.cards[0].repo_name == "r1"


def test_token_estimate_excludes_estimate_field(tmp_path: Path) -> None:
    cfg, root, cfg_path = _fixture(tmp_path)
    pack = ContextPackService().pack(cfg, cfg_path, root, tier=0)
    stripped = pack.model_copy(update={"token_estimate": None})
    data = stripped.model_dump(mode="python", exclude={"token_estimate"})
    expected = len(json.dumps(data, default=str)) // 4
    assert pack.token_estimate == expected
