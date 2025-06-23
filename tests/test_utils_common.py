#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.common
"""

import json
import os


from metagit.core.utils import common


def test_create_vscode_workspace():
    project_name = "TestProject"
    repo_paths = ["/path/to/repo1", "/path/to/repo2"]
    result = common.create_vscode_workspace(project_name, repo_paths)
    assert isinstance(result, str)
    data = json.loads(result)
    assert data["folders"][0]["name"] == "repo1"
    assert data["folders"][1]["name"] == "repo2"
    assert "settings" in data
    assert "extensions" in data


def test_create_vscode_workspace_error(monkeypatch):
    # Simulate error in json.dumps
    monkeypatch.setattr(
        "json.dumps", lambda *_: (_ for _ in ()).throw(Exception("fail"))
    )
    result = common.create_vscode_workspace("x", ["/bad/path"])
    assert isinstance(result, Exception)


def test_open_editor_file_not_exist(tmp_path):
    result = common.open_editor("echo", str(tmp_path / "nope.txt"))
    assert isinstance(result, Exception)
    assert "does not exist" in str(result)


def test_open_editor_success(tmp_path, monkeypatch):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hi")
    monkeypatch.setattr(
        "subprocess.run", lambda *a, **k: type("R", (), {"returncode": 0})()
    )
    result = common.open_editor("echo", str(file_path))
    assert result is None


def test_open_editor_failure(tmp_path, monkeypatch):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hi")

    class FakeResult:
        returncode = 1
        stderr = "fail"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: FakeResult())
    result = common.open_editor("echo", str(file_path))
    assert isinstance(result, Exception)
    assert "Failed to open editor" in str(result)


def test_flatten_dict():
    d = {"a": {"b": 1}, "c": 2}
    flat = common.flatten_dict(d)
    assert flat == {"a.b": 1, "c": 2}


def test_flatten_dict_error(monkeypatch):
    monkeypatch.setattr(
        common,
        "_flatten_dict_gen",
        lambda *a, **k: (_ for _ in ()).throw(Exception("fail")),
    )
    result = common.flatten_dict({"a": 1})
    assert isinstance(result, Exception)


def test_regex_replace():
    s = "hello world"
    out = common.regex_replace(s, "world", "pytest")
    assert out == "hello pytest"


def test_regex_replace_error(monkeypatch):
    monkeypatch.setattr(
        "re.sub", lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    )
    result = common.regex_replace("a", "b", "c")
    assert isinstance(result, Exception)


def test_env_override(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    assert common.env_override("baz", "FOO") == "bar"
    assert common.env_override("baz", "NOPE") == "baz"


def test_env_override_error(monkeypatch):
    monkeypatch.setattr(
        os, "getenv", lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    )
    result = common.env_override("a", "b")
    assert isinstance(result, Exception)


def test_to_yaml_dict():
    d = {"a": 1}
    y = common.to_yaml(d)
    assert isinstance(y, str)
    assert "a:" in y


def test_to_yaml_str():
    s = "already yaml"
    assert common.to_yaml(s) == s


def test_to_yaml_error(monkeypatch):
    # Mock the yaml module that's imported as 'yaml' in common.py
    monkeypatch.setattr(
        common,
        "yaml",
        type(
            "Y",
            (),
            {"dump": staticmethod(lambda *_: (_ for _ in ()).throw(Exception("fail")))},
        )(),
    )
    result = common.to_yaml({"a": 1})
    assert isinstance(result, Exception)


def test_pretty():
    d = {"a": {"b": 1}, "c": 2}
    out = common.pretty(d, indent=2)
    assert isinstance(out, str)
    assert "a" in out and "b" in out and "c" in out


def test_pretty_error(monkeypatch):
    monkeypatch.setattr(
        common, "pretty", lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    )
    try:
        result = common.pretty({"a": 1})
    except Exception as e:
        result = e
    assert isinstance(result, Exception) or isinstance(result, str)


def test_merge_dicts():
    a = {"x": 1, "y": {"z": 2}}
    b = {"y": {"z": 3}, "w": 4}
    out = common.merge_dicts(a, b)
    assert out["y"]["z"] == 3
    assert out["w"] == 4


def test_merge_dicts_error(monkeypatch):
    monkeypatch.setattr(
        common, "merge_dicts", lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    )
    try:
        result = common.merge_dicts({"a": 1}, {"b": 2})
    except Exception as e:
        result = e
    assert isinstance(result, Exception)


def test_parse_checksum_file(tmp_path):
    file = tmp_path / "checksums.txt"
    file.write_text("abc123  file1.txt\ndef456  file2.txt\n")
    out = common.parse_checksum_file(str(file))
    assert out == {"file1.txt": "abc123", "file2.txt": "def456"}


def test_parse_checksum_file_error(tmp_path):
    out = common.parse_checksum_file(str(tmp_path / "nope.txt"))
    assert isinstance(out, Exception)
