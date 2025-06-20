#!/usr/bin/env python
"""
UserPrompt utility for dynamically prompting users for Pydantic object properties.
"""

import json
import re
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import ValidationError as PTValidationError
from prompt_toolkit.validation import Validator
from pydantic import BaseModel, ValidationError, field_validator

T = TypeVar("T", bound=BaseModel)

# Define styles for different prompt elements
PROMPT_STYLE = Style.from_dict(
    {
        "title": "bold cyan",
        "field": "bold green",
        "description": "italic yellow",
        "default": "blue",
        "error": "bold red",
        "success": "bold green",
        "optional": "white",
        "prompt": "white",
    }
)


class UserPrompt:
    """
    A utility class for prompting users to input values for Pydantic model properties.

    This class provides methods to interactively collect user input for required
    fields of any Pydantic model, with validation and type conversion using prompt_toolkit.
    """

    def __init__(self):
        self.session = PromptSession(style=PROMPT_STYLE)

    @staticmethod
    def prompt_for_model(
        model_class: Type[T],
        existing_data: Optional[Dict[str, Any]] = None,
        title: str = None,
    ) -> T:
        """
        Prompt the user for all required fields of a Pydantic model.

        Args:
            model_class: The Pydantic model class to prompt for
            existing_data: Optional existing data to pre-populate fields

        Returns:
            An instance of the specified Pydantic model

        Raises:
            ValueError: If the model_class is not a valid Pydantic model
        """
        if not issubclass(model_class, BaseModel):
            raise ValueError(f"{model_class} is not a valid Pydantic model")

        existing_data = existing_data or {}
        field_data = {}
        prompt_instance = UserPrompt()

        # Get model fields
        model_fields = model_class.model_fields

        if title:
            # Print title
            title_text = FormattedText([("class:title", f"\n=== {title} ===\n")])
            print_formatted_text(title_text)

        for field_name, field_info in model_fields.items():
            # Skip if field already has a value
            if field_name in existing_data:
                field_data[field_name] = existing_data[field_name]
                success_text = FormattedText(
                    [
                        ("class:success", f"✓ {field_name}: "),
                        ("class:prompt", f"{existing_data[field_name]} (pre-filled)"),
                    ]
                )
                print_formatted_text(success_text)
                continue

            # Check if field is required
            is_required = field_info.is_required()

            if is_required:
                value = prompt_instance._prompt_for_field(field_name, field_info)
                field_data[field_name] = value
            else:
                # For optional fields, ask if user wants to provide a value
                while True:
                    optional_text = FormattedText(
                        [
                            (
                                "class:optional",
                                f"\n{field_name} (optional) - Would you like to provide a value? (y/n): ",
                            )
                        ]
                    )
                    response = (
                        prompt_instance.session.prompt(optional_text).strip().lower()
                    )
                    if response in ["y", "yes"]:
                        value = prompt_instance._prompt_for_field(
                            field_name, field_info
                        )
                        field_data[field_name] = value
                        break
                    elif response in ["n", "no"]:
                        break
                    else:
                        print_formatted_text(
                            FormattedText(
                                [("class:error", "Please enter 'y' or 'n'\n")]
                            )
                        )

        # Create and validate the model instance
        try:
            return model_class(**field_data)
        except ValidationError as e:
            error_text = FormattedText(
                [("class:error", f"\n❌ Validation error: {e}\n")]
            )
            print_formatted_text(error_text)
            # Retry with corrected data
            return UserPrompt.prompt_for_model(model_class, field_data)

    def _prompt_for_field(self, field_name: str, field_info: Any) -> Any:
        """
        Prompt the user for a specific field value.

        Args:
            field_name: Name of the field
            field_info: Field information from Pydantic

        Returns:
            The user input value, converted to appropriate type
        """
        field_type = field_info.annotation
        description = field_info.description or ""

        # Get the actual default value for Pydantic v2
        try:
            default_value = field_info.get_default()
            # Filter out PydanticUndefined
            if str(default_value) == "PydanticUndefined":
                default_value = None
        except Exception:
            default_value = None

        # Build formatted prompt message
        prompt_parts = [("class:field", f"\n{field_name}")]

        if description:
            prompt_parts.extend(
                [
                    ("class:prompt", " ("),
                    ("class:description", description),
                    ("class:prompt", ")"),
                ]
            )

        if default_value is not None and default_value != ...:
            prompt_parts.extend(
                [
                    ("class:prompt", " [default: "),
                    ("class:default", str(default_value)),
                    ("class:prompt", ")"),
                ]
            )

        prompt_parts.append(("class:prompt", ": "))

        prompt_text = FormattedText(prompt_parts)

        # Create validator for the field type
        validator = self._create_field_validator(field_type, field_info, field_name)

        # Get user input with validation
        while True:
            try:
                user_input = self.session.prompt(
                    prompt_text, validator=validator
                ).strip()

                # Handle default value
                if (
                    not user_input
                    and default_value is not None
                    and default_value != ...
                ):
                    return default_value

                # Handle empty input for required fields
                if not user_input and field_info.is_required():
                    error_text = FormattedText(
                        [
                            (
                                "class:error",
                                "❌ This field is required. Please provide a value.\n",
                            )
                        ]
                    )
                    print_formatted_text(error_text)
                    continue

                # Convert and return the input
                converted_value = self._convert_input(user_input, field_type)
                return converted_value

            except PTValidationError as e:
                error_text = FormattedText([("class:error", f"❌ {e.message}\n")])
                print_formatted_text(error_text)
                continue

    def _create_field_validator(
        self, field_type: Any, field_info: Any = None, field_name: str = None
    ) -> Optional[Validator]:
        """
        Create a validator for the given field type.

        Args:
            field_type: The type to validate against
            field_info: Field information from Pydantic (optional)
            field_name: Name of the field (optional)

        Returns:
            A prompt_toolkit Validator instance or None
        """

        def validate_type(text: str) -> bool:
            if not text:
                return True  # Allow empty input for optional fields

            # Check if this is a boolean field
            is_bool_field = False

            # Method 1: Check if field_info.annotation is bool
            if field_info and hasattr(field_info, "annotation"):
                is_bool_field = field_info.annotation == bool

            # Method 2: Check if field_type is bool
            elif field_type == bool:
                is_bool_field = True

            # Method 3: Check if field name suggests boolean
            elif field_name and field_name.startswith(
                ("is_", "has_", "can_", "should_", "will_")
            ):
                is_bool_field = True

            if is_bool_field:
                return text.lower() in [
                    "true",
                    "false",
                    "yes",
                    "no",
                    "y",
                    "n",
                    "1",
                    "0",
                ]
            try:
                self._convert_input(text, field_type)
                return True
            except (ValueError, TypeError):
                return False

        return Validator.from_callable(
            validate_type,
            error_message=f"Invalid input for type {field_type}",
            move_cursor_to_end=True,
        )

    @staticmethod
    def _convert_input(user_input: str, target_type: Any) -> Any:
        """
        Convert user input string to the target type.

        Args:
            user_input: Raw user input string
            target_type: Target type to convert to

        Returns:
            Converted value of the target type
        """
        if not user_input:
            return None

        # Handle common types
        if target_type == str:
            return user_input

        elif target_type == int:
            return int(user_input)

        elif target_type == float:
            return float(user_input)

        elif target_type == bool:
            return user_input.lower() in ["true", "yes", "y", "1"]

        elif target_type == list:
            # Try to parse as JSON list, otherwise split by comma
            try:
                return json.loads(user_input)
            except json.JSONDecodeError:
                return [item.strip() for item in user_input.split(",") if item.strip()]

        elif target_type == dict:
            # Try to parse as JSON dict
            return json.loads(user_input)

        elif hasattr(target_type, "__origin__") and target_type.__origin__ is Union:
            # Handle Union types (e.g., Optional[str])
            # Try each type in the union
            for union_type in target_type.__args__:
                if union_type == type(None):  # NoneType
                    continue
                try:
                    return UserPrompt._convert_input(user_input, union_type)
                except (ValueError, TypeError):
                    continue
            raise ValueError(
                f"Could not convert '{user_input}' to any of the union types"
            )

        elif hasattr(target_type, "__origin__") and target_type.__origin__ is list:
            # Handle List[T] types
            item_type = target_type.__args__[0]
            try:
                parsed_list = json.loads(user_input)
                return [
                    UserPrompt._convert_input(str(item), item_type)
                    for item in parsed_list
                ]
            except json.JSONDecodeError:
                # Split by comma and convert each item
                items = [item.strip() for item in user_input.split(",") if item.strip()]
                return [UserPrompt._convert_input(item, item_type) for item in items]

        else:
            # For custom types, try to construct directly
            try:
                return target_type(user_input)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot convert '{user_input}' to type {target_type}")

    @staticmethod
    def prompt_for_single_field(
        field_name: str,
        field_type: Type[Any],
        description: str = "",
        default: Any = None,
    ) -> Any:
        """
        Prompt the user for a single field value.

        Args:
            field_name: Name of the field
            field_type: Type of the field
            description: Optional description of the field
            default: Optional default value

        Returns:
            The user input value, converted to the specified type
        """
        prompt_instance = UserPrompt()

        # Build formatted prompt message
        prompt_parts = [("class:field", f"\n{field_name}")]

        if description:
            prompt_parts.extend(
                [
                    ("class:prompt", " ("),
                    ("class:description", description),
                    ("class:prompt", ")"),
                ]
            )

        if default is not None and default != ...:
            prompt_parts.extend(
                [
                    ("class:prompt", " [default: "),
                    ("class:default", str(default)),
                    ("class:prompt", ")"),
                ]
            )

        prompt_parts.append(("class:prompt", ": "))

        prompt_text = FormattedText(prompt_parts)
        validator = prompt_instance._create_field_validator(
            field_type, None, field_name
        )

        while True:
            try:
                user_input = prompt_instance.session.prompt(
                    prompt_text, validator=validator
                ).strip()

                if not user_input and default is not None and default != ...:
                    return default

                return prompt_instance._convert_input(user_input, field_type)

            except PTValidationError as e:
                error_text = FormattedText([("class:error", f"❌ {e.message}\n")])
                print_formatted_text(error_text)
                continue

    @staticmethod
    def confirm_action(message: str = "Continue?") -> bool:
        """
        Prompt the user for a yes/no confirmation.

        Args:
            message: The confirmation message

        Returns:
            True if user confirms, False otherwise
        """
        prompt_instance = UserPrompt()

        while True:
            confirm_text = FormattedText([("class:prompt", f"\n{message} (y/n): ")])
            response = prompt_instance.session.prompt(confirm_text).strip().lower()

            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                error_text = FormattedText(
                    [("class:error", "Please enter 'y' or 'n'\n")]
                )
                print_formatted_text(error_text)
