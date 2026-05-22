#!/usr/bin/env python
"""
Unit tests for metagit.core.context.session_digest_service.SessionDigestService.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git import Repo
from git.exc import GitCommandError

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.session_digest_service import SessionDigestService


def _load_cfg(tmp_path: Path):
    manager = MetagitConfigManager(config_path=tmp_path / ".metagit.yml")
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    return loaded


def test_build_first_session_empty_repos(tmp_path: Path) -> None:
    """When since is omitted, treat as first session with no repo rows."""
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: digest-first",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = _load_cfg(tmp_path)
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    root = str(tmp_path.resolve())

    out = SessionDigestService.build(
        cfg,
        cfg_path,
        root,
        active_objective_id="obj-1",
    )

    assert out.first_session is True
    assert out.since is None
    assert out.repo_changes == []
    assert out.manifest_changed is False
    assert out.active_objective_id == "obj-1"


def test_manifest_changed_false_when_mtime_not_after_since(tmp_path: Path) -> None:
    """Manifest mtime before 'since' → manifest_changed False."""
    repo_dir = tmp_path / "demo" / "svc"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: digest-manifest",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = _load_cfg(tmp_path)
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    root = str(tmp_path.resolve())
    future = (datetime.now(timezone.utc) + timedelta(days=2)).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00"
    )

    out = SessionDigestService.build(cfg, cfg_path, root, since=future)

    assert out.first_session is False
    assert out.manifest_changed is False


def test_manifest_changed_true_when_mtime_after_since(tmp_path: Path) -> None:
    """Manifest touched after boundary → manifest_changed True."""
    repo_dir = tmp_path / "demo" / "svc"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: digest-manifest-old",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = _load_cfg(tmp_path)
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    root = str(tmp_path.resolve())
    old_since = "2000-01-01T00:00:00+00:00"

    out = SessionDigestService.build(cfg, cfg_path, root, since=old_since)

    assert out.manifest_changed is True


def test_git_activity_populates_count_and_subjects(tmp_path: Path) -> None:
    """Commits after since produce commit_count and up to 3 oneline subjects."""
    repo_dir = tmp_path / "demo" / "svc"
    repo_dir.mkdir(parents=True)
    repo = Repo.init(repo_dir)
    f1 = repo_dir / "a.txt"
    f1.write_text("a", encoding="utf-8")
    repo.index.add([str(f1.relative_to(repo_dir))])
    repo.index.commit("alpha subject")
    f2 = repo_dir / "b.txt"
    f2.write_text("b", encoding="utf-8")
    repo.index.add([str(f2.relative_to(repo_dir))])
    repo.index.commit("beta subject")
    f3 = repo_dir / "c.txt"
    f3.write_text("c", encoding="utf-8")
    repo.index.add([str(f3.relative_to(repo_dir))])
    repo.index.commit("gamma subject")
    f4 = repo_dir / "d.txt"
    f4.write_text("d", encoding="utf-8")
    repo.index.add([str(f4.relative_to(repo_dir))])
    repo.index.commit("delta subject")

    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: digest-git",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = _load_cfg(tmp_path)
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    root = str(tmp_path.resolve())
    since = "2000-01-01T00:00:00+00:00"

    out = SessionDigestService.build(cfg, cfg_path, root, since=since)

    assert len(out.repo_changes) == 1
    row = out.repo_changes[0]
    assert row.project_name == "demo"
    assert row.repo_name == "svc"
    assert row.error is None
    assert row.commit_count >= 4
    assert len(row.recent_subjects) <= 3
    combined = " ".join(row.recent_subjects)
    assert "delta" in combined or "gamma" in combined or "beta" in combined


def test_skips_missing_repo_rows(tmp_path: Path) -> None:
    """Missing clone (exists False) does not produce a digest row."""
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: digest-missing",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: ghost",
                "          path: no/where",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = _load_cfg(tmp_path)
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    root = str(tmp_path.resolve())

    out = SessionDigestService.build(cfg, cfg_path, root, since="2000-01-01T00:00:00+00:00")

    assert out.repo_changes == []


@patch("metagit.core.context.session_digest_service.Repo")
def test_git_command_error_sets_row_error(MockRepo, tmp_path: Path) -> None:
    """Git failures surface on SessionDigestRepoChange.error."""
    repo_dir = tmp_path / "demo" / "svc"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)

    fake = MagicMock()
    fake.git.log.side_effect = GitCommandError("git-log", 128, "stderr", "")
    fake.git.rev_list.side_effect = GitCommandError("git-rev-list", 128, "stderr", "")
    MockRepo.return_value = fake

    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: digest-err",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = _load_cfg(tmp_path)
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    root = str(tmp_path.resolve())

    out = SessionDigestService.build(cfg, cfg_path, root, since="2000-01-01T00:00:00+00:00")

    assert len(out.repo_changes) == 1
    assert out.repo_changes[0].error is not None
    assert out.repo_changes[0].commit_count == 0


def test_invalid_since_raises() -> None:
    """Malformed ISO timestamps raise ValueError."""
    cfg_path = "/tmp/no-such-metagi.yml-for-invalid-since-test"
    with pytest.raises(ValueError):
        SessionDigestService.build(
            MagicMock(),
            cfg_path,
            "/tmp",
            since="not-an-iso-timestamp",
        )


def test_since_accepts_zulu_suffix(tmp_path: Path) -> None:
    """Z suffix normalizes like fromisoformat replacement."""
    repo_dir = tmp_path / "demo" / "svc"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)

    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: digest-z",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = _load_cfg(tmp_path)
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    root = str(tmp_path.resolve())

    out = SessionDigestService.build(cfg, cfg_path, root, since="2000-01-01T00:00:00Z")

    assert out.first_session is False
    assert len(out.repo_changes) == 1
