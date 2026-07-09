#!/usr/bin/env python
"""
Metagit detection tool

.. currentmodule:: metagit
.. moduleauthor:: Metagit <zloeber@gmail.com>
"""

# Guard: a caller-injected PYTHONPATH (e.g. an embedding app) can shadow our
# bundled deps and crash import (ModuleNotFoundError pydantic_core._pydantic_core).
# Force our own site-packages ahead of any env-injected path.
import sys as _sys
import sysconfig as _sc

_own = _sc.get_paths()["purelib"]
if _own in _sys.path:
    _sys.path.remove(_own)
_sys.path.insert(0, _own)
del _sys, _sc, _own

import os  # noqa: E402
from importlib.metadata import PackageNotFoundError, version  # noqa: E402
from os import path  # noqa: E402

here = path.abspath(path.dirname(__file__))

try:
    from ._version import version as __version__
except ImportError:
    try:
        __version__ = version("metagit-cli")
    except PackageNotFoundError:
        __version__ = "0.0.0"


SCRIPT_PATH = os.path.abspath(os.path.split(__file__)[0])
CONFIG_PATH = os.getenv("METAGIT_CONFIG", os.path.join(SCRIPT_PATH, (".metagit.config.yml")))
DATA_PATH = os.getenv("METAGIT_DATA", os.path.join(SCRIPT_PATH, "data"))
DEFAULT_CONFIG = os.path.join(DATA_PATH, "metagit.config.yaml")
