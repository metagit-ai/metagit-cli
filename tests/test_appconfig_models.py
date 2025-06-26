#!/usr/bin/env python
"""
Unit tests for metagit.core.appconfig.models
"""

from metagit.core.appconfig.models import (
    LLM,
    AppConfig,
    Boundary,
    GitHubProvider,
    GitLabProvider,
    Profile,
    WorkspaceConfig,
)


def test_boundary_model():
    b = Boundary(name="internal", values=["foo", "bar"])
    assert b.name == "internal"
    assert b.values == ["foo", "bar"]


def test_profiles_model():
    p = Profile()
    assert p[0].name == "default"
    assert isinstance(p.boundaries, list)


def test_workspace_model():
    w = WorkspaceConfig()
    assert w.path == "./.metagit"
    assert w.default_project == "default"


def test_llm_model():
    llm = LLM()
    assert llm.provider == "openrouter"
    assert llm.api_key == ""


def test_github_provider_model():
    gh = GitHubProvider()
    assert gh.base_url.startswith("https://api.github")
    assert not gh.enabled


def test_gitlab_provider_model():
    gl = GitLabProvider()
    assert gl.base_url.startswith("https://gitlab")
    assert not gl.enabled


def test_providers_model():
    p = Providers()
    assert isinstance(p.github, GitHubProvider)
    assert isinstance(p.gitlab, GitLabProvider)


def test_appconfig_defaults():
    cfg = AppConfig()
    assert cfg.version
    assert cfg.llm.provider == "openrouter"
    assert isinstance(cfg.providers, Providers)


def test_appconfig_load_and_save(tmp_path):
    # Create a config file
    config_path = tmp_path / "testconfig.yaml"
    data = {"config": AppConfig().model_dump()}
    import yaml

    with open(config_path, "w") as f:
        yaml.dump(data, f)
    # Load config
    cfg = AppConfig.load(str(config_path))
    if isinstance(cfg, Exception):
        # Print debug info on failure
        print(f"Config load failed: {cfg}")
        with open(config_path, "r") as f:
            print(f"Written YAML content: {f.read()}")
        # Try to load the YAML directly to see what's in it
        with open(config_path, "r") as f:
            loaded_data = yaml.safe_load(f)
            print(f"Direct YAML load result: {loaded_data}")
    assert isinstance(cfg, AppConfig)
    # Save config
    save_path = tmp_path / "saved.yaml"
    result = cfg.save(str(save_path))
    assert result is True
    # Load saved config
    loaded = AppConfig.load(str(save_path))
    assert isinstance(loaded, AppConfig)


def test_appconfig_load_file_not_found(tmp_path):
    result = AppConfig.load(str(tmp_path / "nope.yaml"))
    assert isinstance(result, AppConfig)
