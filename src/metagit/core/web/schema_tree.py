#!/usr/bin/env python
"""Build and mutate Pydantic config schema trees for the web UI."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo

from metagit.core.config.example_generator import ConfigExampleGenerator
from metagit.core.web.models import ConfigOpKind, ConfigOperation, SchemaFieldNode

_PATH_SEGMENT_RE = re.compile(r"([^.\[\]]+)|\[(\d+|\*)\]")


class SchemaTreeService:
    """Walk Pydantic models into editable schema trees and apply config operations."""

    SENSITIVE_KEYS = frozenset({"api_token", "token", "password", "secret"})

    def __init__(self) -> None:
        self._example_generator = ConfigExampleGenerator()

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
            type_label=model_class.__name__,
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
            elif operation.op == ConfigOpKind.APPEND:
                self._append_at_path(data, model_class, operation.path)
            elif operation.op == ConfigOpKind.REMOVE:
                self._remove_at_path(data, model_class, operation.path)
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
            type_label = self._type_label(annotation)
            sensitive = self._is_sensitive(field_name)
            display_value = self._display_value(
                value,
                sensitive=sensitive,
                mask_secrets=mask_secrets,
            )
            default_value = self._default_for_field(field_info, annotation)
            enum_options = self._enum_options(annotation) if node_type == "enum" else []
            list_meta = self._list_node_meta(annotation, field_dump, enabled)
            node = SchemaFieldNode(
                path=child_path,
                key=field_name,
                type=node_type,
                type_label=type_label,
                description=field_info.description,
                required=field_info.is_required(),
                enabled=enabled,
                editable=enabled,
                sensitive=sensitive,
                default_value=default_value,
                value=display_value if node_type not in {"object", "array"} else None,
                enum_options=enum_options,
                item_count=list_meta.get("item_count"),
                can_append=list_meta.get("can_append", False),
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
            item_unwrapped = self._unwrap_optional(item_annotation)
            is_model = isinstance(item_unwrapped, type) and issubclass(
                item_unwrapped,
                BaseModel,
            )
            items = value if isinstance(value, list) else []
            if not is_model:
                if not items:
                    return []
                scalar_label = self._type_label(item_unwrapped)
                return [
                    SchemaFieldNode(
                        path=self._join_path(parent_path, f"[{index}]"),
                        key=f"[{index}]",
                        type=self._type_name(item_unwrapped),
                        type_label=scalar_label,
                        enabled=True,
                        editable=True,
                        value=item,
                        children=[],
                    )
                    for index, item in enumerate(items)
                ]
            item_type = item_unwrapped
            items = value if isinstance(value, list) else []
            if items:
                children: list[SchemaFieldNode] = []
                item_label = self._type_label(item_type)
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
                            type_label=item_label,
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
            return []
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
        parent, model_at_parent, leaf = self._navigate_parent(
            data,
            model_class,
            segments,
        )
        if isinstance(leaf, int):
            if isinstance(parent, list):
                parent.pop(leaf)
            return
        field_info = model_at_parent.model_fields[str(leaf)]
        if self._accepts_none(field_info.annotation):
            parent[str(leaf)] = None
        else:
            parent.pop(str(leaf), None)

    def _enable_at_path(
        self,
        data: dict[str, Any],
        model_class: type[BaseModel],
        path: str,
    ) -> None:
        segments = self._parse_path(path)
        parent, model_at_parent, leaf = self._navigate_parent(
            data,
            model_class,
            segments,
        )
        field_info = model_at_parent.model_fields[str(leaf)]
        annotation = self._unwrap_optional(field_info.annotation)
        parent[str(leaf)] = self._default_for_field(field_info, annotation)

    def _append_at_path(
        self,
        data: dict[str, Any],
        model_class: type[BaseModel],
        path: str,
    ) -> None:
        segments = self._parse_path(path)
        parent, model_at_parent, leaf = self._navigate_parent(
            data,
            model_class,
            segments,
        )
        field_name = str(leaf)
        field_info = model_at_parent.model_fields[field_name]
        annotation = self._unwrap_optional(field_info.annotation)
        if get_origin(annotation) is not list:
            raise KeyError(f"{path} is not a list field")
        current = parent.get(field_name)
        if current is None:
            current = []
            parent[field_name] = current
        current.append(self._default_list_item(annotation))

    def _remove_at_path(
        self,
        data: dict[str, Any],
        model_class: type[BaseModel],
        path: str,
    ) -> None:
        segments = self._parse_path(path)
        if not segments or not isinstance(segments[-1], int):
            raise KeyError(f"{path} must end with a list index")
        parent, _, leaf = self._navigate_parent(data, model_class, segments)
        if not isinstance(parent, list) or not isinstance(leaf, int):
            raise KeyError(f"{path} is not a list item")
        parent.pop(leaf)

    def _set_at_path(self, data: dict[str, Any], path: str, value: Any) -> None:
        segments = self._parse_path(path)
        parent: Any = data
        for index, segment in enumerate(segments[:-1]):
            if isinstance(segment, int):
                if not isinstance(parent, list):
                    raise KeyError(path)
                parent = parent[segment]
                continue
            next_segment = segments[index + 1]
            if isinstance(next_segment, int):
                if segment not in parent:
                    parent[segment] = []
                parent = parent[segment][next_segment]
                continue
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
    ) -> tuple[Any, type[BaseModel], str | int]:
        """Return parent container, model class at leaf field, and leaf key/index."""
        parent: Any = data
        current_class: type[BaseModel] = model_class
        index = 0
        while index < len(segments) - 1:
            segment = segments[index]
            if isinstance(segment, int):
                if not isinstance(parent, list):
                    raise KeyError("invalid list index in path")
                parent = parent[segment]
                index += 1
                continue
            field_info = current_class.model_fields[segment]
            annotation = self._unwrap_optional(field_info.annotation)
            next_segment = segments[index + 1]
            if isinstance(next_segment, int) and get_origin(annotation) is list:
                if index == len(segments) - 2:
                    parent = parent[segment]
                    current_class = self._list_item_type(annotation)
                    index += 1
                else:
                    parent = parent[segment][next_segment]
                    current_class = self._list_item_type(annotation)
                    index += 2
                continue
            parent = parent[segment]
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                current_class = annotation
            index += 1
        leaf = segments[-1]
        if isinstance(leaf, int):
            return parent, current_class, leaf
        return parent, current_class, leaf

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

    def _type_label(self, annotation: Any) -> str:
        if annotation is None:
            return "unknown"
        annotation = self._unwrap_optional(annotation)
        origin = get_origin(annotation)
        if origin is list:
            args = get_args(annotation)
            inner = args[0] if args else Any
            inner_label = self._type_label(inner)
            return f"{inner_label}[]"
        if isinstance(annotation, type):
            if issubclass(annotation, Enum):
                return annotation.__name__
            if issubclass(annotation, BaseModel):
                return annotation.__name__
            if issubclass(annotation, bool):
                return "boolean"
            if issubclass(annotation, int):
                return "integer"
            if issubclass(annotation, float):
                return "number"
            if issubclass(annotation, str):
                return "string"
        return "unknown"

    def _list_node_meta(
        self,
        annotation: Any,
        field_dump: Any,
        enabled: bool,
    ) -> dict[str, Any]:
        annotation = self._unwrap_optional(annotation)
        if get_origin(annotation) is not list:
            return {}
        count = len(field_dump) if isinstance(field_dump, list) else 0
        return {"item_count": count, "can_append": enabled}

    def _default_list_item(self, annotation: Any) -> Any:
        annotation = self._unwrap_optional(annotation)
        args = get_args(annotation) if get_origin(annotation) is list else (annotation,)
        item = args[0] if args else Any
        item = self._unwrap_optional(item)
        if isinstance(item, type) and issubclass(item, BaseModel):
            return self._default_model_dict(item)
        if isinstance(item, type) and issubclass(item, Enum):
            return next(iter(item)).value
        if item is bool:
            return False
        if item is int:
            return 0
        if item is float:
            return 0.0
        if item is str:
            return ""
        return None

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
        if get_origin(annotation) is list:
            return []
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
            return self._default_model_dict(annotation)
        return None

    def _default_model_dict(self, model_class: type[BaseModel]) -> dict[str, Any]:
        """Build a valid sample dict for a nested model."""
        return self._example_generator._sample_model(model_class)

    def _accepts_none(self, annotation: Any) -> bool:
        origin = get_origin(annotation)
        if origin is Union:
            return type(None) in get_args(annotation)
        return False
