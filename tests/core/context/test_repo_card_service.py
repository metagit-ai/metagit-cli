#!/usr/bin/env python
"""
Unit tests for metagit.core.context.repo_card_service.RepoCardService.
"""

import os
from pathlib import Path
from unittest.mock import patch

from git import Repo

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.repo_card_service import RepoCardService


def _load_config(workspace_root: Path):
  manager = MetagitConfigManager(config_path=workspace_root / ".metagit.yml")
  loaded = manager.load_config()
  assert not isinstance(loaded, Exception)
  return loaded


def test_build_one_git_repo_detects_pyproject_and_branch(tmp_path: Path) -> None:
  """Real git repo with pyproject.toml: stack_hints and branch populated."""
  repo_dir = tmp_path / "svc" / "tiny"
  repo_dir.mkdir(parents=True)
  Repo.init(repo_dir)
  pyproject = repo_dir / "pyproject.toml"
  pyproject.write_text('[project]\nname = "tiny"\nversion = "0.1.0"\n', encoding="utf-8")

  (tmp_path / ".metagit.yml").write_text(
      "\n".join(
          [
              "name: cards-test",
              "kind: application",
              "workspace:",
              "  projects:",
              "    - name: demo",
              "      repos:",
              "        - name: tiny",
              "          path: svc/tiny",
              "          sync: true",
          ]
      )
      + "\n",
      encoding="utf-8",
  )

  cfg = _load_config(tmp_path)
  svc = RepoCardService()
  card = svc.build_one(
      cfg,
      str(tmp_path.resolve()),
      "demo",
      "tiny",
  )

  assert card.exists is True
  assert card.is_git_repo is True
  assert "pyproject.toml" in card.stack_hints
  assert card.branch in ("master", "main")


def test_build_one_missing_clone_sets_missing_clone_flag(tmp_path: Path) -> None:
  """Configured path absent: exists False and health_flags include missing_clone."""
  (tmp_path / ".metagit.yml").write_text(
      "\n".join(
          [
              "name: missing-clone-test",
              "kind: application",
              "workspace:",
              "  projects:",
              "    - name: demo",
              "      repos:",
              "        - name: phantom",
              "          path: no-such-mount/phantom",
          ]
      )
      + "\n",
      encoding="utf-8",
  )

  cfg = _load_config(tmp_path)
  svc = RepoCardService()
  card = svc.build_one(
      cfg,
      str(tmp_path.resolve()),
      "demo",
      "phantom",
  )

  assert card.exists is False
  assert "missing_clone" in card.health_flags


def test_health_flags_stale_head_via_mock(tmp_path: Path) -> None:
  """Optional: mocked inspect reports old HEAD → stale_head_30d."""
  repo_dir = tmp_path / "svc" / "aged"
  repo_dir.mkdir(parents=True)
  Repo.init(repo_dir)

  (tmp_path / ".metagit.yml").write_text(
      "\n".join(
          [
              "name: stale-test",
              "kind: application",
              "workspace:",
              "  projects:",
              "    - name: demo",
              "      repos:",
              "        - name: aged",
              "          path: svc/aged",
          ]
      )
      + "\n",
      encoding="utf-8",
  )

  cfg = _load_config(tmp_path)
  fake = {
      "ok": True,
      "branch": "main",
      "dirty": False,
      "ahead": 0,
      "behind": 0,
      "uncommitted_count": 0,
      "head_commit_age_days": 45.5,
      "merge_base_age_days": None,
  }
  svc = RepoCardService()
  with patch(
      "metagit.core.context.repo_card_service.inspect_repo_state",
      return_value=fake,
  ):
    card = svc.build_one(
        cfg,
        str(tmp_path.resolve()),
        "demo",
        "aged",
    )

  assert card.exists is True
  assert "stale_head_30d" in card.health_flags


def test_build_many_respects_max_cards(tmp_path: Path) -> None:
  """build_many honors max_cards when listing all repos."""
  lines = [
      "name: multi",
      "kind: application",
      "workspace:",
      "  projects:",
      "    - name: p",
      "      repos:",
  ]
  for idx in range(5):
    d = tmp_path / f"r{idx}"
    d.mkdir(parents=True)
    Repo.init(d)
    lines.append(f"        - name: repo{idx}")
    lines.append(f"          path: r{idx}")
  (tmp_path / ".metagit.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")

  cfg = _load_config(tmp_path)
  svc = RepoCardService()
  cards = svc.build_many(cfg, str(tmp_path.resolve()), max_cards=3)
  assert len(cards) == 3
