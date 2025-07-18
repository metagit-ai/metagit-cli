#!/usr/bin/env python
"""
Record management module for metagit.

This module provides classes for managing metagit records with support for
multiple storage backends (OpenSearch and local files) and the ability to
create records from existing metagit configuration data.
"""

from .manager import (
    LocalFileStorageBackend,
    MetagitRecordManager,
    OpenSearchStorageBackend,
    RecordStorageBackend,
)
from .models import MetagitRecord

__all__ = [
    "MetagitRecord",
    "MetagitRecordManager",
    "RecordStorageBackend",
    "LocalFileStorageBackend",
    "OpenSearchStorageBackend",
]
