#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.logging
"""

from loguru import logger as loguru_logger

from metagit.core.utils import logging as metagit_logging
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger


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


def test_console_sink_writes_to_stderr_not_stdout(capsys):
    """Regression: the console sink MUST target stderr, never stdout.

    When metagit runs as an MCP server over stdio (`metagit mcp serve`), stdout
    is reserved exclusively for JSON-RPC frames. A human-readable log line on
    stdout corrupts the transport and breaks the client handshake with
    `Invalid JSON: expected value at line 1 column 1`. This test guards against
    a regression to `logger.add(sys.stdout, ...)`.
    """
    ul = UnifiedLogger(LoggerConfig(log_level="INFO"))
    try:
        ul.info("mcp-stdio-canary")
        loguru_logger.complete()  # flush enqueue=True sink
    finally:
        # Tear the handler down so the loguru global logger is left clean for
        # other tests regardless of assertion outcome.
        loguru_logger.remove()

    captured = capsys.readouterr()
    assert "mcp-stdio-canary" not in captured.out, (
        "console log leaked to stdout — this breaks MCP stdio JSON-RPC"
    )
    assert "mcp-stdio-canary" in captured.err


def test_set_level_keeps_console_sink_on_stderr(capsys):
    """set_level() rebuilds the console handler; it must stay on stderr too."""
    ul = UnifiedLogger(LoggerConfig(log_level="INFO"))
    try:
        ul.set_level("DEBUG")
        ul.info("mcp-stdio-canary-2")
        loguru_logger.complete()
    finally:
        loguru_logger.remove()

    captured = capsys.readouterr()
    assert "mcp-stdio-canary-2" not in captured.out
    assert "mcp-stdio-canary-2" in captured.err
