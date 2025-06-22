#!/usr/bin/env python

from pydantic import BaseModel
from metagit import __version__

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
    default_project: str


class LLM(BaseModel):
    provider: str
    provider_model: str
    embedder: str
    embedder_model: str
    api_key: str


class AppConfig(BaseModel):
    version: str = __version__
    description: str = "Metagit configuration"
    editor: str = "code"
    # Reserved for future use
    api_url: str
    # Reserved for future use
    api_version: str
    # Reserved for future use
    api_key: str
    # Reserved for future use
    cicd_file_data: str
    file_type_data: str
    package_manager_data: str
    default_project: str
    llm: LLM
    workspace: Workspace
    profiles: Profiles
