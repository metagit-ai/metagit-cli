#!/usr/bin/env python
"""Unit tests for Atlas secret path exclusions."""

from __future__ import annotations

from pathlib import Path

from metagit.core.atlas.extractors.secrets import is_excluded_path


def test_env_files_excluded(tmp_path: Path) -> None:
  assert is_excluded_path(tmp_path / ".env")
  assert is_excluded_path(tmp_path / "secrets" / "token.json")
  assert not is_excluded_path(tmp_path / "src" / "toy" / "refunds.py")


def test_env_variants_and_key_material_excluded(tmp_path: Path) -> None:
  assert is_excluded_path(tmp_path / ".env.local")
  assert is_excluded_path(tmp_path / "certs" / "server.pem")
  assert is_excluded_path(tmp_path / "private" / "id_rsa.key")
