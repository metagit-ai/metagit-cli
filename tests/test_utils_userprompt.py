#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.userprompt
"""

from metagit.core.project.models import ProjectPath
from metagit.core.utils import userprompt
from metagit.core.utils.userprompt import UserPrompt


def test_yes_no_prompt_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert userprompt.yes_no_prompt("Continue?") is True


def test_yes_no_prompt_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert userprompt.yes_no_prompt("Continue?") is False


def test_yes_no_prompt_invalid(monkeypatch):
    responses = iter(["maybe", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    assert userprompt.yes_no_prompt("Continue?") is True


def test_prompt_for_model_project_path_url_only(monkeypatch) -> None:
    """Non-prompted default_factory fields (tags) must not become None."""

    def fake_prompt_field(_self, field_name, _field_info):
        if field_name == "name":
            return "terraform-ops"
        return None

    def fake_prompt_optional(_self, field_name, _field_info):
        if field_name == "url":
            return "git@gitlab.com:sram/hammerhead/terraform-ops.git"
        return None

    monkeypatch.setattr(UserPrompt, "_prompt_for_field", fake_prompt_field)
    monkeypatch.setattr(UserPrompt, "_prompt_for_optional_field", fake_prompt_optional)

    result = UserPrompt.prompt_for_model(
        ProjectPath,
        fields_to_prompt=["name", "path", "url", "description"],
    )

    assert not isinstance(result, Exception)
    assert result.name == "terraform-ops"
    assert result.url is not None
    assert str(result.url).endswith("terraform-ops.git")
    assert result.tags == {}
    assert result.path is None


def test_prompt_for_model_validation_retry_drops_failed_fields(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_prompt_field(_self, field_name, _field_info):
        calls["count"] += 1
        return "terraform-ops"

    class NoConsoleScreenBufferError(Exception):
        pass

    def raise_no_console(_text) -> None:
        raise NoConsoleScreenBufferError(
            "No Windows console found. Are you running cmd.exe?"
        )

    monkeypatch.setattr(UserPrompt, "_prompt_for_field", fake_prompt_field)
    monkeypatch.setattr(UserPrompt, "_prompt_for_optional_field", lambda *_: None)
    monkeypatch.setattr(
        userprompt._promptkit(),
        "print_formatted_text",
        raise_no_console,
    )

    result = UserPrompt.prompt_for_model(
        ProjectPath,
        existing_data={"name": "terraform-ops", "tags": None},
        fields_to_prompt=["name"],
        _retry_count=userprompt._MAX_VALIDATION_RETRIES,
    )

    assert isinstance(result, ValueError)
    assert "Validation failed after" in str(result)


def test_prompt_for_model_validation_retry_reprompts_failed_field(monkeypatch) -> None:
    responses = iter(["still-bad", "terraform-ops"])

    def fake_prompt_field(_self, field_name, _field_info):
        if field_name == "name":
            return next(responses)
        return None

    monkeypatch.setattr(UserPrompt, "_prompt_for_field", fake_prompt_field)
    monkeypatch.setattr(UserPrompt, "_prompt_for_optional_field", lambda *_: None)

    result = UserPrompt.prompt_for_model(
        ProjectPath,
        existing_data={
            "name": "terraform-ops",
            "tags": None,
            "url": "git@gitlab.com:sram/hammerhead/terraform-ops.git",
        },
        fields_to_prompt=["name", "url"],
    )

    assert not isinstance(result, Exception)
    assert result.name == "terraform-ops"
    assert result.tags == {}


