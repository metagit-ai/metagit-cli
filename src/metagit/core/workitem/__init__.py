#!/usr/bin/env python
"""External work-item / board references for campaigns and objectives."""

from metagit.core.workitem.models import ExternalWorkRef, WorkItemProvider
from metagit.core.workitem.refs import parse_work_item_ref

__all__ = [
    "ExternalWorkRef",
    "WorkItemProvider",
    "parse_work_item_ref",
]
