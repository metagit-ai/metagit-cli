#!/usr/bin/env python
"""
Unit tests for metagit.core.appconfig.__init__
"""

import yaml

from metagit.core.appconfig import get_config, load_config, models


def test_load_config_success(tmp_path):
    config_path = tmp_path / "testconfig.yaml"
    data = {"config": models.AppConfig().model_dump()}
    with open(config_path, "w") as f:
        yaml.dump(data, f)
    cfg = load_config(str(config_path))
    assert isinstance(cfg, models.AppConfig)


def test_load_config_file_not_found(tmp_path):
    result = load_config(str(tmp_path / "nope.yaml"))
    assert isinstance(result, Exception)


def test_get_config_dict(capsys):
    cfg = models.AppConfig()
    result = get_config(cfg, output="dict")
    assert isinstance(result, dict)


def test_get_config_json(capsys):
    cfg = models.AppConfig()
    get_config(cfg, output="json")
    captured = capsys.readouterr()
    assert "config" in captured.out or "config" in captured.err


def test_get_config_yaml(capsys):
    cfg = models.AppConfig()
    get_config(cfg, output="yaml")
    captured = capsys.readouterr()
    assert "config" in captured.out or "config" in captured.err
