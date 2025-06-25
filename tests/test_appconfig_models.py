#!/usr/bin/env python
"""
Unit tests for metagit.core.appconfig.models
"""

from metagit.core.appconfig import models
from metagit.core.config.models import GitHubProvider, GitLabProvider


def test_boundary_model():
    b = models.Boundary(name="internal", values=["foo", "bar"])
    assert b.name == "internal"
    assert b.values == ["foo", "bar"]


def test_profiles_model():
    p = models.Profiles()
    assert p.default_profile == "default"
    assert isinstance(p.boundaries, list)


def test_workspace_model():
    w = models.WorkspaceConfig()
    assert w.path == "./.metagit"
    assert w.default_project == "default"


def test_llm_model():
    llm = models.LLM()
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
    p = models.Providers()
    assert isinstance(p.github, GitHubProvider)
    assert isinstance(p.gitlab, GitLabProvider)


def test_appconfig_defaults():
    cfg = models.AppConfig()
    assert cfg.version
    assert cfg.llm.provider == "openrouter"
    assert isinstance(cfg.providers, models.Providers)


def test_appconfig_env_override(monkeypatch):
    # Unset any real tokens that might override our test
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    monkeypatch.setenv("METAGIT_LLM_API_KEY", "llmkey")
    monkeypatch.setenv("METAGIT_GITHUB_API_TOKEN", "ghtoken")
    monkeypatch.setenv("METAGIT_GITHUB_BASE_URL", "https://api.github.test.com")
    monkeypatch.setenv("METAGIT_GITLAB_API_TOKEN", "gltoken")
    monkeypatch.setenv("METAGIT_GITLAB_BASE_URL", "https://gitlab.test.com/api/v4")
    monkeypatch.setenv("METAGIT_API_KEY", "apikey")
    monkeypatch.setenv("METAGIT_API_URL", "https://api.test.com")
    monkeypatch.setenv("METAGIT_API_VERSION", "v2")
    cfg = models.AppConfig()
    cfg = models.AppConfig._override_from_environment(cfg)
    assert cfg.llm.api_key == "llmkey"
    assert cfg.providers.github.api_token == "ghtoken"
    assert cfg.providers.github.base_url == "https://api.github.test.com"
    assert cfg.providers.gitlab.api_token == "gltoken"
    assert cfg.providers.gitlab.base_url == "https://gitlab.test.com/api/v4"
    assert cfg.api_key == "apikey"
    assert cfg.api_url == "https://api.test.com"
    assert cfg.api_version == "v2"


def test_appconfig_load_and_save(tmp_path):
    # Create a config file
    config_path = tmp_path / "testconfig.yaml"
    data = {"config": models.AppConfig().model_dump()}
    import yaml

    with open(config_path, "w") as f:
        yaml.dump(data, f)
    # Load config
    cfg = models.AppConfig.load(str(config_path))
    if isinstance(cfg, Exception):
        # Print debug info on failure
        print(f"Config load failed: {cfg}")
        with open(config_path, "r") as f:
            print(f"Written YAML content: {f.read()}")
        # Try to load the YAML directly to see what's in it
        with open(config_path, "r") as f:
            loaded_data = yaml.safe_load(f)
            print(f"Direct YAML load result: {loaded_data}")
    assert isinstance(cfg, models.AppConfig)
    # Save config
    save_path = tmp_path / "saved.yaml"
    result = cfg.save(str(save_path))
    assert result is True
    # Load saved config
    loaded = models.AppConfig.load(str(save_path))
    assert isinstance(loaded, models.AppConfig)


def test_appconfig_load_file_not_found(tmp_path):
    result = models.AppConfig.load(str(tmp_path / "nope.yaml"))
    assert isinstance(result, models.AppConfig)
