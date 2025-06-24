#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.logging
"""

from metagit.core.utils import logging as metagit_logging


def test_get_logger_returns_logger():
    logger = metagit_logging.get_logger("test_logger")
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "debug")


def test_logger_log_levels(monkeypatch):
    logger = metagit_logging.get_logger("test_logger2")
    # Test that the logger has the expected methods
    assert hasattr(logger, "set_level")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")

    # Test setting log level
    result = logger.set_level("DEBUG")
    assert result is None

    # Test logging methods (they should not raise exceptions)
    debug_result = logger.debug("debug message")
    info_result = logger.info("info message")
    error_result = logger.error("error message")

    assert debug_result is None
    assert info_result is None
    assert error_result is None
