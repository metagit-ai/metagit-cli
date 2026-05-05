#!/usr/bin/env python
"""
Metagit detection tool

.. currentmodule:: metagit
.. moduleauthor:: Metagit <zloeber@gmail.com>
"""

import os
from os import path
from importlib.metadata import PackageNotFoundError, version

here = path.abspath(path.dirname(__file__))

try:
    from ._version import version as __version__
except ImportError:
    try:
        __version__ = version("metagit-cli")
    except PackageNotFoundError:
        __version__ = "0.0.0"


SCRIPT_PATH = os.path.abspath(os.path.split(__file__)[0])
CONFIG_PATH = os.getenv(
    "METAGIT_CONFIG", os.path.join(SCRIPT_PATH, (".metagit.config.yml"))
)
DATA_PATH = os.getenv("METAGIT_DATA", os.path.join(SCRIPT_PATH, "data"))
DEFAULT_CONFIG = os.path.join(DATA_PATH, "metagit.config.yaml")
