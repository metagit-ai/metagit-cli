#!/usr/bin/env python
"""Unit tests for SchemaTreeService."""

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.web.models import ConfigOpKind, ConfigOperation
from metagit.core.web.schema_tree import SchemaTreeService


def test_build_metagit_tree_marks_present_fields() -> None:
    service = SchemaTreeService()
    config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
    root = service.build_tree(config, MetagitConfig)

    name_node = service.find_node(root, "name")
    kind_node = service.find_node(root, "kind")

    assert name_node is not None
    assert name_node.enabled is True
    assert kind_node is not None
    assert kind_node.enabled is True
    assert kind_node.type == "enum"
    assert "application" in kind_node.enum_options


def test_enum_field_exposes_all_options() -> None:
    service = SchemaTreeService()
    config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
    root = service.build_tree(config, MetagitConfig)
    kind_node = service.find_node(root, "kind")

    assert kind_node is not None
    assert len(kind_node.enum_options) >= 3


def test_disable_optional_field_removes_key() -> None:
    service = SchemaTreeService()
    config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
    updated, errors = service.apply_operations(
        config,
        MetagitConfig,
        [ConfigOperation(op=ConfigOpKind.DISABLE, path="description")],
    )

    assert errors == []
    assert "description" not in updated.model_dump(exclude_none=True)


def test_enable_optional_field_adds_default() -> None:
    service = SchemaTreeService()
    config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
    disabled, _ = service.apply_operations(
        config,
        MetagitConfig,
        [ConfigOperation(op=ConfigOpKind.DISABLE, path="description")],
    )
    enabled, errors = service.apply_operations(
        disabled,
        MetagitConfig,
        [ConfigOperation(op=ConfigOpKind.ENABLE, path="description")],
    )

    assert errors == []
    assert enabled.description == "No description"
    assert "description" in enabled.model_dump(exclude_none=True)


def test_set_field_updates_value() -> None:
    service = SchemaTreeService()
    config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
    updated, errors = service.apply_operations(
        config,
        MetagitConfig,
        [ConfigOperation(op=ConfigOpKind.SET, path="name", value="new-name")],
    )

    assert errors == []
    assert updated.name == "new-name"


def test_appconfig_sensitive_field_masked_in_tree() -> None:
    service = SchemaTreeService()
    raw = {
        "workspace": {"path": "./sync"},
        "providers": {
            "github": {"enabled": True, "api_token": "ghp_abcdefghijklmnop"},
        },
    }
    config = AppConfig(**raw)
    root = service.build_tree(config, AppConfig, mask_secrets=True)
    token_node = service.find_node(root, "providers.github.api_token")

    assert token_node is not None
    assert token_node.sensitive is True
    assert token_node.value == "***mnop"


def test_apply_operations_returns_original_instance_on_validation_error() -> None:
    service = SchemaTreeService()
    config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
    updated, errors = service.apply_operations(
        config,
        MetagitConfig,
        [ConfigOperation(op=ConfigOpKind.SET, path="kind", value="not-a-valid-kind")],
    )

    assert errors != []
    assert updated is config
    assert updated.name == "demo"
    assert updated.kind == "application"


def test_sensitive_token_unchanged_after_masked_set() -> None:
    service = SchemaTreeService()
    raw = {
        "workspace": {"path": "./sync"},
        "providers": {
            "github": {"enabled": True, "api_token": "ghp_abcdefghijklmnop"},
        },
    }
    config = AppConfig(**raw)
    updated, errors = service.apply_operations(
        config,
        AppConfig,
        [
            ConfigOperation(
                op=ConfigOpKind.SET,
                path="providers.github.api_token",
                value="***mnop",
            )
        ],
    )

    assert errors == []
    assert updated.providers.github.api_token == "ghp_abcdefghijklmnop"
