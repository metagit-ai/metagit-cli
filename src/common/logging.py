#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
from typing import Literal

from loguru import logger
from pydantic import BaseModel, Field


class LoggerConfig(BaseModel):
    """
    Pydantic model for logger configuration.
    """

    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"] = (
        Field(default="INFO", description="Logging level.")
    )
    log_to_file: bool = Field(default=False, description="Whether to log to a file.")
    log_file_path: str = Field(default="app.log", description="Path to the log file.")
    json_logs: bool = Field(
        default=False, description="Whether to output logs in JSON format."
    )
    rotation: str = Field(default="10 MB", description="Log file rotation policy.")
    retention: str = Field(default="7 days", description="Log file retention policy.")
    backtrace: bool = Field(default=False, description="Enable backtrace in logs.")
    diagnose: bool = Field(default=False, description="Enable diagnose in logs.")
    minimal_console: bool = Field(
        default=False, description="Use minimal console output format."
    )


class AppLogger:
    def __init__(
        self,
        config: LoggerConfig,
    ):
        """
        Initialize the application logger using a LoggerConfig instance.
        Args:
            config (LoggerConfig): Logger configuration.
        """
        # Remove default logger to avoid duplicate logs
        logger.remove()

        # Format config
        if config.json_logs:
            log_format = "{message}"
            serialize = True
        elif config.minimal_console:
            log_format = "{message}"
            serialize = False
        else:
            log_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            )
            serialize = False
        # Console sink
        logger.add(
            sys.stdout,
            level=config.log_level,
            format=log_format,
            backtrace=config.backtrace,
            diagnose=config.diagnose,
            serialize=serialize,
            enqueue=True,  # Use queue for async/threaded safety
        )

        # File sink (optional)
        if config.log_to_file:
            logger.add(
                config.log_file_path,
                level=config.log_level,
                format=log_format,
                rotation=config.rotation,
                retention=config.retention,
                backtrace=config.backtrace,
                diagnose=config.diagnose,
                serialize=serialize,
                enqueue=True,
            )

        self._intercept_std_logging()

    def _intercept_std_logging(self):
        """
        Intercept standard logging module output to loguru.
        """

        class InterceptHandler(logging.Handler):
            def emit(self, record):
                level = logger.level(
                    record.levelname
                ).name  # if record.levelname in logger._levels else record.levelno
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )

        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    def get_logger(self):
        return logger
