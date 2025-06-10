#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Metagit detection tool

.. currentmodule:: metagit_detect
.. moduleauthor:: Zachary Loeber <zloeber@gmail.com>
"""

import os
from os import path

here = path.abspath(path.dirname(__file__))
__version__ = "0.1.0"
SCRIPT_PATH = os.path.abspath(os.path.split(__file__)[0])
CONFIG_PATH = os.getenv(
    "METAGIT_CONFIG", os.path.join(SCRIPT_PATH, (".metagit.config.yml"))
)
DATA_PATH = os.getenv("METAGIT_DATA", os.path.join(SCRIPT_PATH, "data"))
DEFAULT_CONFIG = os.path.join(DATA_PATH, "metagit.config.yaml")
