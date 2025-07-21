#!/usr/bin/env python
"""
Metagit detection tool

.. currentmodule:: metagit
.. moduleauthor:: Metagit <zloeber@gmail.com>
"""

import os
from os import path

here = path.abspath(path.dirname(__file__))

try:
    from ._version import version as __version__
except ImportError:
    from setuptools_scm import get_version

    __version__ = get_version(root="../../", relative_to=__file__)


SCRIPT_PATH = os.path.abspath(os.path.split(__file__)[0])
CONFIG_PATH = os.getenv(
    "METAGIT_CONFIG", os.path.join(SCRIPT_PATH, (".metagit.config.yml"))
)
DATA_PATH = os.getenv("METAGIT_DATA", os.path.join(SCRIPT_PATH, "data"))
DEFAULT_CONFIG = os.path.join(DATA_PATH, "metagit.config.yaml")
