#!/usr/bin/env python

import json
import os
from pathlib import Path
from typing import Union

import yaml as base_yaml

from metagit.core.appconfig.agent_mode import resolve_agent_mode
from metagit.core.appconfig.models import AppConfig

__all__ = [
    "AppConfig",
    "get_config",
    "load_config",
    "resolve_agent_mode",
    "save_config",
    "set_config",
]
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.utils.yaml_class import yaml


def load_config(config_path: str) -> Union[AppConfig, Exception]:
    """
    Load and validate the YAML configuration file.
    """
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            return FileNotFoundError(f"Configuration file {config_path} not found")

        with config_file.open("r") as file:
            config_data = yaml.safe_load(file)

        config = AppConfig(**config_data["config"])
        config = AppConfig._override_from_environment(config)
        # Keep session path discoverable for components that initialize without direct
        # access to AppConfig but honor METAGIT_WORKSPACE_SESSION_PATH overrides.
        os.environ.setdefault("METAGIT_WORKSPACE_SESSION_PATH", config.workspace.session_path)
        return config
    except Exception as e:
        return e


def save_config(
    config_path: str,
    config: AppConfig,
    *,
    auto_format: bool = True,
) -> Union[None, Exception]:
    """
    Save the AppConfig object to a YAML file.
    """
    try:
        if auto_format:
            from metagit.core.config.format_service import ConfigFormatService

            original_text = Path(config_path).read_text(encoding="utf-8") if Path(config_path).is_file() else ""
            formatted = ConfigFormatService().render_appconfig(
                config,
                original_text=original_text,
            )
            Path(config_path).write_text(formatted, encoding="utf-8")
            return None
        config_dict = {"config": config.model_dump(exclude_none=True, mode="json")}
        with open(config_path, "w") as f:
            base_yaml.dump(
                config_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                line_break=True,
            )
        return None
    except Exception as e:
        return e


def set_config(appconfig: AppConfig, name: str, value: str, logger=None) -> Union[AppConfig, Exception]:
    """Set appconfig values"""
    if logger is None:
        logger = UnifiedLogger(
            LoggerConfig(
                log_level="INFO",
                use_rich_console=True,
                minimal_console=False,
                terse=False,
            )
        )
    try:
        config_path = name.split(".")
        current_level = appconfig
        for element in config_path[:-1]:
            if hasattr(current_level, element):
                current_level = getattr(current_level, element)
            else:
                return ValueError(f"Invalid key: {name}")

        last_element = config_path[-1]
        if hasattr(current_level, last_element):
            field_type = type(getattr(current_level, last_element))
            if isinstance(field_type, bool):
                if value.lower() in ["true", "1", "yes"]:
                    converted_value = True
                elif value.lower() in ["false", "0", "no"]:
                    converted_value = False
                else:
                    return TypeError(f"Invalid value for boolean: {value}")
            else:
                try:
                    converted_value = field_type(value)
                except (ValueError, TypeError):
                    return TypeError(f"Invalid value type for '{name}'. Expected {field_type.__name__}.")
            setattr(current_level, last_element, converted_value)
        else:
            return ValueError(f"Invalid key: {name}")

        return appconfig
    except Exception as e:
        return e


def get_config(
    appconfig: AppConfig, name="", show_keys=False, output="json", logger=None
) -> Union[dict, None, Exception]:
    """Retrieve appconfig values"""
    if logger is None:
        # Map LOG_LEVELS[3] (which is logging.INFO) to the string 'INFO'
        logger = UnifiedLogger(
            LoggerConfig(
                log_level="INFO",
                use_rich_console=True,
                minimal_console=False,
                terse=False,
            )
        )
    try:
        appconfig_dict = appconfig.model_dump(exclude_none=True, exclude_unset=True, mode="json")
        output_value = {"config": appconfig_dict}
        config_path = name.split(".")
        if name != "":
            for element in config_path:
                element_value = output_value[element]
                if isinstance(element_value, AppConfig):
                    output_value = element_value.__dict__
                elif isinstance(element_value, dict):
                    output_value = element_value
                else:
                    output_value = element_value
                    break
        if show_keys and isinstance(output_value, dict):
            output_value = list(output_value.keys())
        elif show_keys and isinstance(output_value, list):
            output_result = []
            for output_name in output_value:
                output_result.append(output_name)
            output_value = output_result

        if output == "yml" or output == "yaml":
            base_yaml.Dumper.ignore_aliases = lambda *args: True  # noqa: ARG005
            logger.echo(
                base_yaml.dump(
                    output_value,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                    line_break=True,
                ),
                console=True,
            )
        elif output == "json":
            logger.echo(json.dumps(output_value, indent=2), console=True)
        elif output == "dict":
            return output_value
        elif isinstance(output_value, list):
            for result_item in output_value:
                logger.echo(result_item, console=True)
        elif isinstance(output_value, dict):
            logger.echo(output_value.__str__(), console=True)
        else:
            for result_item in output_value:
                logger.echo(result_item, console=True)
        return None
    except Exception as e:
        return e
