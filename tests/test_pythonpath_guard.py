#!/usr/bin/env python
"""Regression: hostile PYTHONPATH must not shadow metagit's bundled pydantic."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile


def test_import_survives_hostile_pythonpath() -> None:
  """Decoy pydantic on PYTHONPATH must not break metagit import."""
  junk = tempfile.mkdtemp()
  # a decoy 'pydantic' with no compiled core, to simulate the shadow
  os.makedirs(os.path.join(junk, "pydantic"))
  open(os.path.join(junk, "pydantic", "__init__.py"), "w").close()
  env = dict(os.environ, PYTHONPATH=junk)
  # Drop empty PYTHONPATH-style noise; keep caller env otherwise.
  r = subprocess.run(
    [
      sys.executable,
      "-c",
      "import metagit; from metagit.cli.main import main",
    ],
    env=env,
    capture_output=True,
    text=True,
    check=False,
  )
  assert r.returncode == 0, r.stderr
