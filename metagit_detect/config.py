#!/usr/bin/env python

import json
from pathlib import Path

import click
import yaml as base_yaml
from pydantic import BaseModel, Field

from utils.logging import LOG_LEVELS, LoggerConfig, UnifiedLogger
from utils.yaml_class import yaml

success_blurb: str = "Success! ✅"
failure_blurb: str = "Failed! ❌"


class Boundary(BaseModel):
    name: str
    values: list[str]


class Profiles(BaseModel):
    profile_config_path: str
    default_profile: str
    boundaries: list[Boundary]


class Workspace(BaseModel):
    path: str
    default: str
    auto_sync: bool
    sync_on_start: bool


class LLM(BaseModel):
    provider: str
    provider_model: str
    embedder: str
    embedder_model: str
    api_key: str


class GlobalConfig(BaseModel):
    debug: bool
    verbose: bool
    strict: bool
    override: str
    metagit_api_url: str
    metagit_api_version: str
    metagit_api_key: str
    cicd_file_data: str
    file_type_data: str
    package_manager_data: str


class Config(BaseModel):
    version: str
    description: str
    global_config: GlobalConfig = Field(..., alias="global")
    llm: LLM
    workspace: Workspace
    profiles: Profiles

    class Config:
        # Allow alias (e.g., 'global' in YAML) to map to global_config
        validate_by_name = True


def load_config(config_path: str) -> Config:
    """
    Load and validate the YAML configuration file.
    """
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file {config_path} not found")

        with config_file.open("r") as file:
            config_data = yaml.safe_load(file)

        # Validate and convert to Pydantic model
        return Config(**config_data["config"])
    except Exception as e:
        raise click.ClickException(f"Error loading configuration: {e!s}")


def get_config(appconfig: Config, name="", show_keys=False, output="json", logger=None):
    """Retrieve appconfig values"""
    if logger is None:
        logger = UnifiedLogger(
            name="metagit_detect",
            level=LOG_LEVELS.INFO,
            config=LoggerConfig(console=True),
        )
    appconfig_dict = appconfig.model_dump()
    output_value = {"config": appconfig_dict}
    config_path = name.split(".")
    if name != "":
        for element in config_path:
            element_value = output_value[element]
            if isinstance(element_value, Config):
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


# def validate(
#     appconfig: Config,
#     jsonschema_path: str,
#     return_results=False,
#     strict=True,
#     logger=None,
# ):
#     """Validate an individual manifest"""
#     if logger is None:
#         logger = UnifiedLogger(
#             name="metagit_detect",
#             level=LOG_LEVELS.INFO,
#             config=LoggerConfig(console=True),
#         )
#     results = list()

#     if exists(jsonschema_path):
#         logger.config_element("jsonschema_path", jsonschema_path)
#         try:
#             with open(jsonschema_path, "r") as stream:
#                 jsonschema_data = json.load(stream)
#         except Exception as err:
#             logger.config_element(
#                 "JSON schema is not able to be loaded ({0})".format(jsonschema_path),
#                 "AppConfig file is not valid JSON ❌",
#                 console=True,
#             )
#             logger.error(err)
#             sys.exit(1)

#         # Load configfile via our custom yaml loader to ensure that embedded includes are
#         #  evaluated and that the yaml is sane as well
#         test_result = {
#             "appconfig": appconfig,
#             "success": True,
#             "test": "Is valid YAML",
#             "details": "",
#         }
#         try:
#             with open(appconfig, "r") as stream:
#                 appconfig_data = yaml.load(stream)
#         except Exception as err:
#             test_result["success"] = False
#             test_result["details"] = f"Manifest file is not valid YAML: {err}"
#         results.append(test_result)

#         # Validate data against the schema. Throws a ValueError if data is invalid.
#         test_result = {
#             "appconfig": appconfig,
#             "success": True,
#             "test": "Is valid schema",
#             "details": "",
#         }
#         validator = jsonschema.Draft7Validator(jsonschema_data)
#         errors = list(validator.iter_errors(appconfig_data))
#         schema_failed = False
#         if errors:
#             schema_failed = True
#             results.append(
#                 {
#                     "appconfig": appconfig,
#                     "success": False,
#                     "test": "Is valid schema",
#                     "details": "\n".join(e.message for e in errors[:1]),
#                 }
#             )
#         if not schema_failed:
#             results.append(test_result)
#     else:
#         logger.error(
#             "JSON schema file does not exist: {0}".format(jsonschema),
#             console=True,
#         )
#     if return_results:
#         return results
#     else:
#         failed = False
#         for result in results:
#             if not result["success"]:
#                 failed = True
#                 logger.config_element(
#                     result["test"],
#                     failure_blurb,
#                     console=True,
#                 )
#                 logger.error(
#                     f"Validation failed for {result['test']} in {appconfig}",
#                     console=True,
#                 )
#                 logger.error(result["details"], console=True)
#             else:
#                 logger.config_element(
#                     result["test"],
#                     success_blurb,
#                     console=True,
#                 )
#         if failed:
#             sys.exit(1)
#         else:
#             logger.config_element("Validation Status", success_blurb, console=True)
