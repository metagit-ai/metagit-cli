#!/usr/bin/env python3
"""
Detection module for metagit.

This module provides comprehensive repository detection and analysis capabilities,
including language detection, project classification, branch analysis, CI/CD detection,
and metrics collection.
"""

from .manager import DetectionManager
from .models import (
    BranchInfo,
    CIConfigAnalysis,
    DetectionManagerConfig,
    GitBranchAnalysis,
    LanguageDetection,
    ProjectTypeDetection,
)

__all__ = [
    "DetectionManager",
    "DetectionManagerConfig",
    "LanguageDetection",
    "ProjectTypeDetection",
    "GitBranchAnalysis",
    "CIConfigAnalysis",
    "BranchInfo",
]
