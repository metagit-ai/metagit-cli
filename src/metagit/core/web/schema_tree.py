#!/usr/bin/env python
"""Build and mutate Pydantic config schema trees for the web UI."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo

from metagit.core.web.models import ConfigOpKind, ConfigOperation, SchemaFieldNode

_PATH_SEGMENT_RE = re.compile(r"([^.\[\]]+)|\[(\d+|\*)\]")


class SchemaTreeService:
    """Walk Pydantic models into editable schema trees and apply config operations."""

    SENSITIVE_KEYS = frozenset({"api_token", "token", "password", "secret"})

    def build_tree(
        self,
        model_instance: BaseModel,
        model_class: type[BaseModel],
        *,
        mask_secrets: bool = False,
    ) -> SchemaFieldNode:
        """Build schema tree rooted at synthetic node key='root', path=''."""
        dump = model_instance.model_dump(exclude_none=True, mode="python")
        return SchemaFieldNode(
            path="",
            key="root",
            type="object",
            enabled=True,
            editable=False,
            children=self._build_children(
                model_instance,
                model_class,
                dump,
                parent_path="",
                mask_secrets=mask_secrets,
            ),
        )

    def find_node(self, root: SchemaFieldNode, path: str) -> SchemaFieldNode | None:
        """Find node by dot/bracket path like name, workspace.projects[0].name."""
        if not path:
            return root
        segments = self._parse_path(path)
        return self._find_by_segments(root, segments)

    def apply_operations(
        self,
        instance: BaseModel,
        model_class: type[BaseModel],
        ops: list[ConfigOperation],
    ) -> tuple[BaseModel, list[dict[str, str]]]:
        """Apply enable/disable/set ops; return (updated_instance, validation_errors)."""
        data = instance.model_dump(mode="python")
        for operation in ops:
            if operation.op == ConfigOpKind.DISABLE:
                self._disable_at_path(data, model_class, operation.path)
            elif operation.op == ConfigOpKind.ENABLE:
                self._enable_at_path(data, model_class, operation.path)
            elif operation.op == ConfigOpKind.SET:
                self._set_at_path(data, operation.path, operation.value)
        return self._validate(model_class, data, original=instance)

    def _build_children(
        self,
        model_instance: BaseModel,
        model_class: type[BaseModel],
        dump: dict[str, Any] | list[Any] | Any,
        *,
        parent_path: str,
        mask_secrets: bool,
    ) -> list[SchemaFieldNode]:
        children: list[SchemaFieldNode] = []
        for field_name, field_info in model_class.model_fields.items():
            child_path = self._join_path(parent_path, field_name)
            value = getattr(model_instance, field_name, None)
            field_dump = dump.get(field_name) if isinstance(dump, dict) else None
            enabled = self._field_enabled(field_info, value, field_dump)
            annotation = self._unwrap_optional(field_info.annotation)
            node_type = self._type_name(annotation)
            sensitive = self._is_sensitive(field_name)
            display_value = self._display_value(
                value,
                sensitive=sensitive,
                mask_secrets=mask_secrets,
            )
            default_value = self._default_for_field(field_info, annotation)
            enum_options = self._enum_options(annotation) if node_type == "enum" else []
            node = SchemaFieldNode(
                path=child_path,
                key=field_name,
                type=node_type,
                description=field_info.description,
                required=field_info.is_required(),
                enabled=enabled,
                editable=enabled,
                sensitive=sensitive,
                default_value=default_value,
                value=display_value if node_type not in {"object", "array"} else None,
                enum_options=enum_options,
                children=[],
            )
            node.children = self._build_field_children(
                value,
                annotation,
                field_dump,
                parent_path=child_path,
                mask_secrets=mask_secrets,
                enabled=enabled,
            )
            children.append(node)
        return children

    def _build_field_children(
        self,
        value: Any,
        annotation: Any,
        field_dump: Any,
        *,
        parent_path: str,
        mask_secrets: bool,
        enabled: bool,
    ) -> list[SchemaFieldNode]:
        if not enabled:
            return []
        origin = get_origin(annotation)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if not isinstance(value, BaseModel):
                return []
            nested_dump = (
                field_dump
                if isinstance(field_dump, dict)
                else value.model_dump(
                    exclude_none=True,
                    mode="python",
                )
            )
            return self._build_children(
                value,
                annotation,
                nested_dump,
                parent_path=parent_path,
                mask_secrets=mask_secrets,
            )
        if origin is list:
            args = get_args(annotation)
            item_annotation = args[0] if args else Any
            if not isinstance(item_annotation, type) or not issubclass(
                item_annotation, BaseModel
            ):
                return []
            item_type = item_annotation
            items = value if isinstance(value, list) else []
            if items:
                children: list[SchemaFieldNode] = []
                for index, item in enumerate(items):
                    item_dump = (
                        field_dump[index]
                        if isinstance(field_dump, list) and index < len(field_dump)
                        else item.model_dump(exclude_none=True, mode="python")
                    )
                    item_path = self._join_path(parent_path, f"[{index}]")
                    children.append(
                        SchemaFieldNode(
                            path=item_path,
                            key=f"[{index}]",
                            type="object",
                            enabled=True,
                            editable=True,
                            children=self._build_children(
                                item,
                                item_type,
                                item_dump,
                                parent_path=item_path,
                                mask_secrets=mask_secrets,
                            ),
                        )
                    )
                return children
            template_path = self._join_path(parent_path, "[*]")
            return [
                SchemaFieldNode(
                    path=template_path,
                    key="[*]",
                    type="object",
                    enabled=False,
                    editable=False,
                    children=self._build_children(
                        item_type.model_construct(),
                        item_type,
                        {},
                        parent_path=template_path,
                        mask_secrets=mask_secrets,
                    ),
                )
            ]
        return []

    def _field_enabled(
        self,
        field_info: FieldInfo,
        value: Any,
        field_dump: Any,
    ) -> bool:
        if field_dump is not None:
            return True
        if field_info.is_required() and value is not None:
            return True
        return False

    def _disable_at_path(
        self,
        data: dict[str, Any],
        model_class: type[BaseModel],
        path: str,
    ) -> None:
        segments = self._parse_path(path)
        parent, leaf = self._navigate_parent(data, model_class, segments)
        field_info = model_class.model_fields[leaf]
        if self._accepts_none(field_info.annotation):
            parent[leaf] = None
        else:
            parent.pop(leaf, None)

    def _enable_at_path(
        self,
        data: dict[str, Any],
        model_class: type[BaseModel],
        path: str,
    ) -> None:
        segments = self._parse_path(path)
        parent, leaf = self._navigate_parent(data, model_class, segments)
        field_info = model_class.model_fields[leaf]
        annotation = self._unwrap_optional(field_info.annotation)
        parent[leaf] = self._default_for_field(field_info, annotation)

    def _set_at_path(self, data: dict[str, Any], path: str, value: Any) -> None:
        segments = self._parse_path(path)
        parent: Any = data
        for segment in segments[:-1]:
            if isinstance(segment, int):
                if not isinstance(parent, list):
                    raise KeyError(path)
                parent = parent[segment]
            else:
                if segment not in parent:
                    parent[segment] = {} if not isinstance(segments[-1], int) else []
                parent = parent[segment]
        leaf = segments[-1]
        if isinstance(leaf, str) and self._is_sensitive(leaf):
            if isinstance(value, str) and (value.startswith("***") or value == ""):
                return
        if isinstance(leaf, int):
            parent[leaf] = value
        else:
            parent[leaf] = value

    def _navigate_parent(
        self,
        data: dict[str, Any],
        model_class: type[BaseModel],
        segments: list[str | int],
    ) -> tuple[Any, str | int]:
        parent: Any = data
        current_class: type[BaseModel] = model_class
        for segment in segments[:-1]:
            if isinstance(segment, int):
                origin = get_origin(current_class.model_fields)
                _ = origin
                field_name = self._list_field_name(current_class)
                items = parent[field_name]
                parent = items[segment]
                current_class = self._list_item_type(
                    current_class.model_fields[field_name].annotation
                )
            else:
                parent = parent[segment]
                field_info = current_class.model_fields[segment]
                annotation = self._unwrap_optional(field_info.annotation)
                origin = get_origin(annotation)
                if origin is list:
                    current_class = self._list_item_type(annotation)
                elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    current_class = annotation
        return parent, segments[-1]

    def _list_field_name(self, model_class: type[BaseModel]) -> str:
        for field_name, field_info in model_class.model_fields.items():
            annotation = self._unwrap_optional(field_info.annotation)
            if get_origin(annotation) is list:
                return field_name
        raise KeyError("list field not found")

    def _validate(
        self,
        model_class: type[BaseModel],
        data: dict[str, Any],
        *,
        original: BaseModel,
    ) -> tuple[BaseModel, list[dict[str, str]]]:
        try:
            return model_class.model_validate(data), []
        except ValidationError as exc:
            errors = [
                {
                    "path": self._format_error_path(err.get("loc", ())),
                    "message": err.get("msg", "validation error"),
                }
                for err in exc.errors()
            ]
            return original, errors

    def _format_error_path(self, loc: tuple[Any, ...]) -> str:
        parts: list[str] = []
        for item in loc:
            if isinstance(item, int):
                parts.append(f"[{item}]")
            else:
                if parts:
                    parts.append(f".{item}")
                else:
                    parts.append(str(item))
        return "".join(parts)

    def _find_by_segments(
        self,
        node: SchemaFieldNode,
        segments: list[str | int],
    ) -> SchemaFieldNode | None:
        if not segments:
            return node
        head, *tail = segments
        for child in node.children:
            if child.key == head or child.key == f"[{head}]":
                return self._find_by_segments(child, tail)
        return None

    def _parse_path(self, path: str) -> list[str | int]:
        segments: list[str | int] = []
        for match in _PATH_SEGMENT_RE.finditer(path):
            name, index = match.groups()
            if name:
                segments.append(name)
            elif index == "*":
                segments.append("*")
            else:
                segments.append(int(index))
        return segments

    def _join_path(self, parent: str, segment: str) -> str:
        if parent:
            if segment.startswith("["):
                return f"{parent}{segment}"
            return f"{parent}.{segment}"
        return segment.lstrip(".")

    def _unwrap_optional(self, annotation: Any) -> Any:
        origin = get_origin(annotation)
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]
            if len(args) == 1:
                return args[0]
        return annotation

    def _list_item_type(self, annotation: Any) -> type[BaseModel]:
        annotation = self._unwrap_optional(annotation)
        args = get_args(annotation)
        item = args[0] if args else Any
        if isinstance(item, type) and issubclass(item, BaseModel):
            return item
        raise TypeError("list item is not a BaseModel")

    def _enum_options(self, annotation: Any) -> list[str]:
        annotation = self._unwrap_optional(annotation)
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return [str(member.value) for member in annotation]
        return []

    def _type_name(self, annotation: Any) -> str:
        if annotation is None:
            return "unknown"
        annotation = self._unwrap_optional(annotation)
        origin = get_origin(annotation)
        if origin is list:
            return "array"
        if isinstance(annotation, type):
            if issubclass(annotation, Enum):
                return "enum"
            if issubclass(annotation, bool):
                return "boolean"
            if issubclass(annotation, int):
                return "integer"
            if issubclass(annotation, float):
                return "number"
            if issubclass(annotation, str):
                return "string"
            if issubclass(annotation, BaseModel):
                return "object"
        return "unknown"

    def _is_sensitive(self, key: str) -> bool:
        return key in self.SENSITIVE_KEYS or key.endswith("_token")

    def _display_value(
        self,
        value: Any,
        *,
        sensitive: bool,
        mask_secrets: bool,
    ) -> Any:
        if not mask_secrets or not sensitive or not isinstance(value, str):
            return value
        if len(value) > 4:
            return f"***{value[-4:]}"
        return "***"

    def _default_for_field(self, field_info: FieldInfo, annotation: Any) -> Any:
        if not field_info.is_required():
            default = field_info.get_default(call_default_factory=True)
            if default is not None:
                return default
        annotation = self._unwrap_optional(annotation)
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return next(iter(annotation))
        if annotation is bool:
            return False
        if annotation is int:
            return 0
        if annotation is float:
            return 0.0
        if annotation is str:
            return ""
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation.model_construct().model_dump(mode="python")
        return None

    def _accepts_none(self, annotation: Any) -> bool:
        origin = get_origin(annotation)
        if origin is Union:
            return type(None) in get_args(annotation)
        return False
