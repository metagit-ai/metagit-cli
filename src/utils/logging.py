#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import sys
from typing import Any, Dict, Literal, Optional

from loguru import logger
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme


class LoggerConfig(BaseModel):
    """
    Pydantic model for unified logger configuration.
    """

    # Logging configuration
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

    # Console output configuration
    minimal_console: bool = Field(
        default=False, description="Use minimal console output format."
    )
    use_rich_console: bool = Field(
        default=True, description="Whether to use rich console formatting."
    )
    terse: bool = Field(
        default=False, description="Use terse output format (no borders or titles)."
    )


class UnifiedLogger:
    """
    A unified logging system that combines structured logging with rich console output.
    """

    def __init__(self, config: LoggerConfig):
        """
        Initialize the unified logger using a LoggerConfig instance.
        Args:
            config (LoggerConfig): Logger configuration.
        """
        self.config = config
        self.debug_mode = config.log_level == "DEBUG" or config.log_level == "TRACE"

        # Initialize rich console if enabled
        if config.use_rich_console:
            custom_theme = Theme(
                {
                    "info": "cyan",
                    "success": "green",
                    "warning": "yellow",
                    "error": "red",
                    "debug": "dim cyan",
                    "agent": "magenta",
                    "task": "blue",
                    "crew": "bold green",
                    "input": "bold yellow",
                    "output": "bold white",
                    "json": "bold cyan",
                }
            )
            self.console = Console(theme=custom_theme)
        else:
            self.console = None

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
            enqueue=True,
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
        """Intercept standard logging module output to loguru."""

        class InterceptHandler(logging.Handler):
            def emit(self, record):
                level = logger.level(record.levelname).name
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )

        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    def get_logger(self):
        """Get the underlying loguru logger instance."""
        return logger

    def print_debug(self, message: str, title: str = "Debug Information") -> None:
        """Print debug messages with rich formatting."""
        if self.debug_mode:
            self._format_output(message, "debug", title)
            logger.debug(message)

    def print_agent_message(
        self, agent_name: str, message: str, style: str = "agent"
    ) -> None:
        """Print a message from an agent with rich formatting."""
        self._format_output(message, style, agent_name)
        logger.info(f"Agent {agent_name}: {message}")

    def print_task_status(
        self, task_name: str, status: str, details: Optional[str] = None
    ) -> None:
        """Print task status information with rich formatting."""
        content = f"{task_name}\nStatus: {status}"
        if details:
            content += f"\n\n{details}"
        self._format_output(content, "task", "Task Update")
        logger.info(
            f"Task {task_name} - Status: {status}"
            + (f" - {details}" if details else "")
        )

    def print_crew_status(self, message: str, status_type: str = "info") -> None:
        """Print crew status messages with rich formatting."""
        self._format_output(message, status_type, "Crew Status")
        logger.info(f"Crew Status: {message}")

    def print_input(self, input_data: Dict[str, Any]) -> None:
        """Print formatted input data with rich formatting."""
        if self.debug_mode:
            content = json.dumps(input_data, indent=2)
            self._format_output(content, "input", "Input Data")
            logger.debug(f"Input Data: {json.dumps(input_data)}")

    def print_output(self, output_data: Any) -> None:
        """Print formatted output data with rich formatting."""
        content = (
            json.dumps(output_data, indent=2)
            if isinstance(output_data, dict)
            else str(output_data)
        )
        self._format_output(content, "output", "Output")
        logger.info(f"Output: {output_data}")

    def print_error(self, error_message: str) -> None:
        """Print error messages with rich formatting."""
        self._format_output(error_message, "error", "Error")
        logger.error(error_message)

    def print_success(self, message: str) -> None:
        """Print success messages with rich formatting."""
        self._format_output(message, "success", "Success")
        logger.info(f"Success: {message}")

    def print_info(self, message: str) -> None:
        """Print general information messages with rich formatting."""
        self._format_output(message, "info", "Information")
        logger.info(message)

    def print_json(self, data: Dict[str, Any], title: str = "JSON Data") -> None:
        """Print formatted JSON data with rich formatting."""
        content = json.dumps(data, indent=2)
        self._format_output(content, "json", title)
        logger.debug(f"{title}: {json.dumps(data)}")

    def print_debug_json(
        self, data: Dict[str, Any], title: str = "Debug JSON Data"
    ) -> None:
        """
        Print JSON data with debug formatting, only showing output in debug mode.
        Uses print_json for the actual output formatting.

        Args:
            data: Dictionary containing the JSON data to print
            title: Optional title for the debug panel
        """
        if self.debug_mode:
            self.print_json(data, title)

    # Direct logging methods
    def debug(self, message: str) -> None:
        """Log a debug message."""
        logger.debug(message)

    def info(self, message: str) -> None:
        """Log an info message."""
        logger.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        logger.error(message)

    def critical(self, message: str) -> None:
        """Log a critical message."""
        logger.critical(message)

    def exception(self, message: str) -> None:
        """Log an exception message with traceback."""
        logger.exception(message)

    def _format_output(
        self, message: str, style: str, title: Optional[str] = None
    ) -> None:
        """
        Internal method to format output based on terse mode.

        Args:
            message: The message to display
            style: The style to use for formatting
            title: Optional title for the output
        """
        if not self.console:
            return

        if self.config.terse:
            # In terse mode, just print the message with style
            if title:
                self.console.print(f"[{style}]{title}:[/{style}] {message}")
            else:
                self.console.print(f"[{style}]{message}[/{style}]")
        else:
            # In normal mode, use panels with borders and titles
            if title:
                self.console.print(
                    Panel(
                        message,
                        title=f"[{style}]{title}[/{style}]",
                        border_style=style,
                    )
                )
            else:
                self.console.print(
                    Panel(
                        message,
                        border_style=style,
                    )
                )
