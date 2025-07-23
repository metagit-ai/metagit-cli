#!/usr/bin/env python

"""
logging class that does general logging via loguru and prints to the console via rich.
"""

import json
import logging
import sys
from typing import Any, Literal, Optional, Protocol, Union

from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme


class LoggerProtocol(Protocol):
    """
    Protocol for the logger interface.
    This includes:
        Standard log methods (info, debug, error, etc.)
        Rich printing methods (print_json, print_info, print_task_status, etc.)
        Optional console formatting methods (header, footer, etc.)
        Return type of Union[None, Exception]
    Notes:
        - All the ... are placeholders for the actual methods per the Protocol definition
        - This is a workaround to allow for the logger to be injected into classes that don't inherit from LoggingModel
    """

    # === Core logging methods ===
    def debug(self, message: str) -> Union[None, Exception]: ...
    def info(self, message: str) -> Union[None, Exception]: ...
    def warning(self, message: str) -> Union[None, Exception]: ...
    def error(self, message: str) -> Union[None, Exception]: ...
    def critical(self, message: str) -> Union[None, Exception]: ...
    def exception(self, message: str) -> Union[None, Exception]: ...

    # === Print helpers ===
    def print_info(self, message: str) -> Union[None, Exception]: ...
    def print_debug(
        self, message: str, title: str = "Debug Information"
    ) -> Union[None, Exception]: ...
    def print_debug_json(
        self, data: dict[str, Any], title: str = "Debug JSON Data"
    ) -> Union[None, Exception]: ...
    def print_json(
        self, data: dict[str, Any], title: str = "JSON Data"
    ) -> Union[None, Exception]: ...
    def print_error(self, error_message: str) -> Union[None, Exception]: ...
    def print_success(self, message: str) -> Union[None, Exception]: ...
    def print_input(self, input_data: dict[str, Any]) -> Union[None, Exception]: ...
    def print_output(self, output_data: Any) -> Union[None, Exception]: ...
    def print_agent_message(
        self, agent_name: str, message: str, style: str = "agent"
    ) -> Union[None, Exception]: ...
    def print_task_status(
        self, task_name: str, status: str, details: Optional[str] = None
    ) -> Union[None, Exception]: ...
    def print_crew_status(
        self, message: str, status_type: str = "info"
    ) -> Union[None, Exception]: ...

    # === Console formatting ===
    def header(
        self, text: str, console: Optional[bool] = None
    ) -> Union[None, Exception]: ...
    def footer(self, text: str, console: bool = True) -> Union[None, Exception]: ...
    def line(self, console: bool = True) -> Union[None, Exception]: ...
    def success(self, text: str, console: bool = True) -> Union[None, Exception]: ...
    def proc_out(self, text: str, console: bool = True) -> Union[None, Exception]: ...
    def echo(
        self, text: str, color: str = "", dim: bool = False, console: bool = True
    ) -> Union[None, Exception]: ...
    def param(
        self, text: str, value: str, status: str, console: bool = True
    ) -> Union[None, Exception]: ...
    def config_element(
        self,
        name: str = "",
        value: str = "",
        separator: str = ": ",
        console: bool = True,
    ) -> Union[None, Exception]: ...

    # Add any others you rely on via injection (e.g. print_json, print_info)


# Logger configuration
class LoggerConfig(BaseModel):
    """
    Pydantic model for unified logger configuration.
    """

    # Logging configuration
    name: Optional[str] = Field(default="metagit", description="Logger name.")
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

    class Config:
        env_prefix = "LOG_"


LOG_LEVEL_MAP: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

LOG_LEVELS: dict[int, int] = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG,
}  #: a mapping of `verbose` option counts to logging levels


class UnifiedLogger(LoggerProtocol):
    def __init__(self, config: LoggerConfig):
        self.config = config
        self.debug_mode = config.log_level in ("DEBUG", "TRACE")
        self._stdout_handler_id = None
        self._file_handler_id = None

        # Initialize rich console if enabled
        self.console = None
        if config.use_rich_console:
            theme = Theme(
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
            self.console = Console(theme=theme)

        # Remove default loguru handler
        logger.remove()

        # Choose formatting
        if config.json_logs or config.minimal_console:
            log_format = "{message}"
            serialize = config.json_logs
        else:
            log_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<dim>{file}:{module}</dim> - "
                "<level>{message}</level>"
            )
            serialize = False

        # Console sink
        self._stdout_handler_id = logger.add(
            sys.stdout,
            level=config.log_level,
            format=log_format,
            backtrace=config.backtrace,
            diagnose=config.diagnose,
            serialize=serialize,
            enqueue=True,
        )

        # Optional file sink
        if config.log_to_file:
            self._file_handler_id = logger.add(
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

    def set_level(
        self, level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]
    ) -> Union[None, Exception]:
        """
        Set the logging level for all handlers.
        Args:
            level: The new logging level to set
        """
        try:
            self.config.log_level = level
            self.debug_mode = level == "DEBUG" or level == "TRACE"

            # Update stdout handler
            if self._stdout_handler_id is not None:
                logger.remove(self._stdout_handler_id)
                self._stdout_handler_id = logger.add(
                    sys.stdout,
                    level=level,
                    format=(
                        "{message}"
                        if self.config.json_logs or self.config.minimal_console
                        else (
                            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                            "<level>{level: <8}</level> | "
                            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                            "<dim>{file}:{module}</dim> - "
                            "<level>{message}</level>"
                        )
                    ),
                    backtrace=self.config.backtrace,
                    diagnose=self.config.diagnose,
                    serialize=self.config.json_logs,
                    enqueue=True,
                )

            # Update file handler if it exists
            if self._file_handler_id is not None and self.config.log_to_file:
                logger.remove(self._file_handler_id)
                self._file_handler_id = logger.add(
                    self.config.log_file_path,
                    level=level,
                    format=(
                        "{message}"
                        if self.config.json_logs or self.config.minimal_console
                        else (
                            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                            "<level>{level: <8}</level> | "
                            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                            "<dim>{file}:{module}</dim> - "
                            "<level>{message}</level>"
                        )
                    ),
                    rotation=self.config.rotation,
                    retention=self.config.retention,
                    backtrace=self.config.backtrace,
                    diagnose=self.config.diagnose,
                    serialize=self.config.json_logs,
                    enqueue=True,
                )
            return None
        except Exception as e:
            return e

    def _intercept_std_logging(self) -> Union[None, Exception]:
        """Intercept standard logging module output to loguru."""
        try:

            class InterceptHandler(logging.Handler):
                def emit(self, record: logging.LogRecord) -> None:
                    try:
                        level = logger.level(record.levelname).name
                    except ValueError:
                        level = record.levelno
                    frame, depth = logging.currentframe(), 2
                    while frame and frame.f_code.co_filename == logging.__file__:
                        frame = frame.f_back
                        depth += 1
                    logger.opt(depth=depth, exception=record.exc_info).log(
                        level, record.getMessage()
                    )

            logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
            return None
        except Exception as e:
            return e

    def get_logger(self) -> Union[Any, Exception]:
        """Get the underlying loguru logger instance."""
        try:
            return logger
        except Exception as e:
            return e

    def print_debug(
        self, message: str, title: str = "Debug Information"
    ) -> Union[None, Exception]:
        """Print debug messages with rich formatting."""
        try:
            if self.debug_mode:
                self._format_output(message, "debug", title)
                logger.debug(message)
            return None
        except Exception as e:
            return e

    def print_agent_message(
        self, agent_name: str, message: str, style: str = "agent"
    ) -> Union[None, Exception]:
        """Print a message from an agent with rich formatting."""
        try:
            self._format_output(message, style, agent_name)
            logger.info(f"Agent {agent_name}: {message}")
            return None
        except Exception as e:
            return e

    def print_task_status(
        self, task_name: str, status: str, details: Union[str, None] = None
    ) -> Union[None, Exception]:
        """Print task status information with rich formatting."""
        try:
            content = f"{task_name}\nStatus: {status}"
            if details:
                content += f"\n\n{details}"
            self._format_output(content, "task", "Task Update")
            logger.info(
                f"Task {task_name} - Status: {status}"
                + (f" - {details}" if details else "")
            )
            return None
        except Exception as e:
            return e

    def print_crew_status(
        self, message: str, status_type: str = "info"
    ) -> Union[None, Exception]:
        """Print crew status messages with rich formatting."""
        try:
            self._format_output(message, status_type, "Crew Status")
            logger.info(f"Crew Status: {message}")
            return None
        except Exception as e:
            return e

    def print_input(self, input_data: dict[str, Any]) -> Union[None, Exception]:
        """Print input data with rich formatting."""
        try:
            self._format_output(str(input_data), "input", "Input Data")
            logger.info(f"Input: {input_data}")
            return None
        except Exception as e:
            return e

    def print_output(self, output_data: Any) -> Union[None, Exception]:
        """Print output data with rich formatting."""
        try:
            self._format_output(str(output_data), "output", "Output Data")
            logger.info(f"Output: {output_data}")
            return None
        except Exception as e:
            return e

    def print_error(self, error_message: str) -> Union[None, Exception]:
        """Print error messages with rich formatting."""
        try:
            self._format_output(error_message, "error", "Error")
            logger.error(error_message)
            return None
        except Exception as e:
            return e

    def print_success(self, message: str) -> Union[None, Exception]:
        """Print success messages with rich formatting."""
        try:
            self._format_output(message, "success", "Success")
            logger.info(message)
            return None
        except Exception as e:
            return e

    def print_info(self, message: str) -> Union[None, Exception]:
        """Print informational messages with rich formatting."""
        try:
            self._format_output(message, "info", "Info")
            logger.info(message)
            return None
        except Exception as e:
            return e

    def print_json(
        self, data: dict[str, Any], title: str = "JSON Data"
    ) -> Union[None, Exception]:
        """Print JSON data with rich formatting and syntax highlighting."""
        try:
            json_str = json.dumps(data, indent=2)
            self._format_output(json_str, "json", title)
            logger.info(json_str)
            return None
        except Exception as e:
            return e

    def print_debug_json(
        self, data: dict[str, Any], title: str = "Debug JSON Data"
    ) -> Union[None, Exception]:
        """Print JSON data only if in debug mode."""
        try:
            if self.debug_mode:
                self.print_json(data, title)
            return None
        except Exception as e:
            return e

    # Direct loguru methods
    def debug(self, message: str) -> Union[None, Exception]:
        """Log a debug message."""
        try:
            logger.opt(depth=2).debug(message)
            return None
        except Exception as e:
            return e

    def info(self, message: str) -> Union[None, Exception]:
        """Log an info message."""
        try:
            logger.opt(depth=2).info(message)
            return None
        except Exception as e:
            return e

    def warning(self, message: str) -> Union[None, Exception]:
        """Log a warning message."""
        try:
            logger.opt(depth=2).warning(message)
            return None
        except Exception as e:
            return e

    def error(self, message: str) -> Union[None, Exception]:
        """Log an error message."""
        try:
            logger.opt(depth=2).error(message)
            return None
        except Exception as e:
            return e

    def critical(self, message: str) -> Union[None, Exception]:
        """Log a critical message."""
        try:
            logger.opt(depth=2).critical(message)
            return None
        except Exception as e:
            return e

    def exception(self, message: str) -> Union[None, Exception]:
        """Log an exception with traceback."""
        try:
            logger.opt(depth=2).exception(message)
            return None
        except Exception as e:
            return e

    def _format_output(
        self, message: str, style: str, title: Union[str, None] = None
    ) -> Union[None, Exception]:
        """
        Helper to format and print output using rich console.
        Args:
            message (str): The message to print.
            style (str): The rich style to use.
            title (str, optional): The panel title. Defaults to None.
        """
        try:
            if self.console and not self.config.minimal_console:
                if self.config.terse:
                    self.console.print(f"[{style}]{message}[/{style}]")
                else:
                    panel_title = f"[{style}]{title}[/{style}]" if title else None
                    self.console.print(
                        Panel(
                            f"[{style}]{message}[/{style}]",
                            title=panel_title,
                            expand=False,
                        )
                    )
            elif not self.config.json_logs:
                # Fallback for non-rich, non-json logging
                print(f"{title}: {message}" if title else message)
            return None
        except Exception as e:
            return e

    def header(self, text: str, console: bool = None) -> Union[None, Exception]:
        """Prints a header"""
        try:
            if console is None:
                console = self.config.use_rich_console
            if console:
                self.console.rule(f"[bold green]{text}")
            else:
                print(f"### {text} ###")
            return None
        except Exception as e:
            return e

    def param(
        self, text: str, value: str, status: str, console: bool = True
    ) -> Union[None, Exception]:
        """Prints a parameter line"""
        try:
            if console:
                self.console.print(
                    f"[dim] {text} [/dim][bold cyan]{value}[/bold cyan] [bold green]({status})[/bold green]"
                )
            else:
                print(f"{text} {value} ({status})")
            return None
        except Exception as e:
            return e

    def config_element(
        self,
        name: str = "",
        value: str = "",
        separator: str = ": ",
        console: bool = True,
    ) -> Union[None, Exception]:
        """Prints a config element"""
        try:
            if console:
                self.console.print(
                    f"[bold white]  {name}[/bold white]{separator}{value}"
                )
            else:
                print(f"  {name}{separator}{value}")
            return None
        except Exception as e:
            return e

    def footer(self, text: str, console: bool = True) -> Union[None, Exception]:
        """Prints a footer"""
        try:
            if console:
                self.console.rule(f"[bold green]{text}")
            else:
                print(f"### {text} ###")
            return None
        except Exception as e:
            return e

    def proc_out(self, text: str, console: bool = True) -> Union[None, Exception]:
        """Prints a process output"""
        try:
            if console:
                self.console.print(f"[dim]{text}[/dim]")
            else:
                print(text)
            return None
        except Exception as e:
            return e

    def line(self, console: bool = True) -> Union[None, Exception]:
        """Prints a line"""
        try:
            if console:
                self.console.print("")
            else:
                print("")
            return None
        except Exception as e:
            return e

    def success(self, text: str, console: bool = True) -> Union[None, Exception]:
        """Prints a success message"""
        try:
            if console:
                self.console.print(f"[bold green]{text}[/bold green]")
            return None
        except Exception as e:
            return e

    def echo(
        self, text: str, color: str = "", dim: bool = False, console: bool = True
    ) -> Union[None, Exception]:
        """
        Echo text to console with optional color and dimming.
        Args:
            text: Text to echo
            color: Color to use
            dim: Whether to dim the text
            console: Whether to output to console
        """
        try:
            if console and self.console:
                style = f"{color} dim" if dim else color
                self.console.print(text, style=style)
            return None
        except Exception as e:
            return e


def get_logger(name: str = "metagit") -> Any:
    """
    Get a logger instance with default configuration.

    Args:
        name: Logger name

    Returns:
        UnifiedLogger instance
    """
    config = LoggerConfig(name=name)
    return UnifiedLogger(config)


class LoggingModel(BaseModel):
    _logger: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = getattr(self, "logger", None) or logger

    @property
    def logger(self):
        return self._logger

    def set_logger(self, logger):
        self._logger = logger
