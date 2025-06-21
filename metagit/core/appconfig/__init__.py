#!/usr/bin/env python

import json
from pathlib import Path
from typing import Union

import click
import yaml as base_yaml

from metagit.core.appconfig.models import AppConfig
from metagit.core.utils.logging import LOG_LEVELS, LoggerConfig, UnifiedLogger
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

        # Validate and convert to Pydantic model
        return AppConfig(**config_data["config"])
    except Exception as e:
        return e


def get_config(
    appconfig: AppConfig, name="", show_keys=False, output="json", logger=None
) -> Union[dict, None, Exception]:
    """Retrieve appconfig values"""
    if logger is None:
        logger = UnifiedLogger(
            name="metagit_detect",
            level=LOG_LEVELS.INFO,
            config=LoggerConfig(console=True),
        )
    try:
        appconfig_dict = appconfig.model_dump()
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
            output_result = list()
            for output_name in output_value:
                output_result.append(output_name)
            output_value = output_result

        if output == "yml" or output == "yaml":
            base_yaml.Dumper.ignore_aliases = lambda *args: True
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
