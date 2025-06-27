#!/usr/bin/env python
"""
UserPrompt utility for dynamically prompting users for Pydantic object properties.
"""

import json
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import ValidationError as PTValidationError
from prompt_toolkit.validation import Validator
from pydantic import BaseModel, ValidationError

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
        fields_to_prompt: Optional[List[str]] = None,
    ) -> Union[T, Exception]:
        """
        Prompt the user for fields of a Pydantic model.

        Args:
            model_class: The Pydantic model class to prompt for
            existing_data: Optional existing data to pre-populate fields
            title: Optional title to display at the top of the prompt
            fields_to_prompt: Optional list of field names to prompt for.
                             If None, prompts for all fields. If specified,
                             only prompts for these fields and uses defaults/None for others.

        Returns:
            An instance of the specified Pydantic model

        Raises:
            ValueError: If the model_class is not a valid Pydantic model
        """
        try:
            if not issubclass(model_class, BaseModel):
                return ValueError(f"{model_class} is not a valid Pydantic model")

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
                            (
                                "class:prompt",
                                f"{existing_data[field_name]} (pre-filled)",
                            ),
                        ]
                    )
                    print_formatted_text(success_text)
                    continue

                # If fields_to_prompt is specified, only prompt for those fields
                if fields_to_prompt is not None and field_name not in fields_to_prompt:
                    # Use default value or None for non-prompted fields
                    try:
                        default_value = field_info.get_default()
                        if str(default_value) == "PydanticUndefined":
                            default_value = None
                        field_data[field_name] = default_value
                    except Exception:
                        field_data[field_name] = None
                    continue

                # Check if field is required
                is_required = field_info.is_required()

                if is_required:
                    value = prompt_instance._prompt_for_field(field_name, field_info)
                    if isinstance(value, Exception):
                        return value
                    field_data[field_name] = value
                else:
                    # For optional fields, prompt directly with [Optional] indicator
                    value = prompt_instance._prompt_for_optional_field(
                        field_name, field_info
                    )
                    if isinstance(value, Exception):
                        return value
                    # Only assign if a value was provided (not None)
                    if value is not None:
                        field_data[field_name] = value

            # Create and validate the model instance
            try:
                return model_class(**field_data)
            except ValidationError as e:
                error_text = FormattedText(
                    [("class:error", f"\n❌ Validation error: {e}\n")]
                )
                print_formatted_text(error_text)
                # Retry with corrected data
                return UserPrompt.prompt_for_model(
                    model_class, field_data, title, fields_to_prompt
                )
        except Exception as e:
            return e

    def _prompt_for_field(
        self, field_name: str, field_info: Any
    ) -> Union[Any, Exception]:
        """
        Prompt the user for a specific field value.

        Args:
            field_name: Name of the field
            field_info: Field information from Pydantic

        Returns:
            The user input value, converted to appropriate type
        """
        try:
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
            validator = self._create_field_validator(field_type, field_info)
            if isinstance(validator, Exception):
                return validator

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
                    if isinstance(converted_value, Exception):
                        # This should be caught by the validator, but as a fallback
                        error_text = FormattedText(
                            [("class:error", f"❌ {converted_value}\n")]
                        )
                        print_formatted_text(error_text)
                        continue
                    return converted_value

                except PTValidationError as e:
                    error_text = FormattedText([("class:error", f"❌ {e.message}\n")])
                    print_formatted_text(error_text)
                    continue
        except Exception as e:
            return e

    def _prompt_for_optional_field(
        self, field_name: str, field_info: Any
    ) -> Union[Any, Exception]:
        """
        Prompt the user for an optional field value.

        Args:
            field_name: Name of the field
            field_info: Field information from Pydantic

        Returns:
            The user input value (converted to appropriate type) or None if no value provided
        """
        try:
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

            # Build formatted prompt message with [Optional] indicator
            prompt_parts = [("class:field", f"\n{field_name}")]

            if description:
                prompt_parts.extend(
                    [
                        ("class:prompt", " ("),
                        ("class:description", description),
                        ("class:prompt", ")"),
                    ]
                )

            # Add [Optional] indicator
            prompt_parts.extend(
                [
                    ("class:prompt", " ["),
                    ("class:optional", "Optional"),
                    ("class:prompt", "]"),
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
            validator = self._create_field_validator(field_type, field_info)
            if isinstance(validator, Exception):
                return validator

            # Get user input with validation
            while True:
                try:
                    user_input = self.session.prompt(
                        prompt_text, validator=validator
                    ).strip()

                    # Handle empty input for optional fields - return None
                    if not user_input:
                        return None

                    # Handle default value
                    if (
                        not user_input
                        and default_value is not None
                        and default_value != ...
                    ):
                        return default_value

                    # Convert and return the input
                    converted_value = self._convert_input(user_input, field_type)
                    if isinstance(converted_value, Exception):
                        # This should be caught by the validator, but as a fallback
                        error_text = FormattedText(
                            [("class:error", f"❌ {converted_value}\n")]
                        )
                        print_formatted_text(error_text)
                        continue
                    return converted_value

                except PTValidationError as e:
                    error_text = FormattedText([("class:error", f"❌ {e.message}\n")])
                    print_formatted_text(error_text)
                    continue
        except Exception as e:
            return e

    def _create_field_validator(
        self, field_type: Any, field_info: Any = None
    ) -> Union[Optional[Validator], Exception]:
        """
        Create a validator for the given field type.

        Args:
            field_type: The type to validate against
            field_info: Field information from Pydantic (optional)
            field_name: Name of the field (optional)

        Returns:
            A prompt_toolkit Validator instance or None
        """
        try:

            def validate_type(text: str) -> bool:
                if not text:
                    return True  # Allow empty input for optional fields

                # Check if this is a boolean field
                is_bool_field = False

                # Method 1: Check if field_info.annotation is bool
                if field_info and hasattr(field_info, "annotation"):
                    if (
                        hasattr(field_info.annotation, "__origin__")
                        and field_info.annotation.__origin__ is Union
                    ):
                        # Handle Optional[bool], which is Union[bool, None]
                        if bool in field_info.annotation.__args__:
                            is_bool_field = True
                    elif field_info.annotation is bool:
                        is_bool_field = True

                if is_bool_field:
                    if text.strip().lower() in ["true", "false", "y", "n", "yes", "no"]:
                        return True
                    else:
                        raise PTValidationError(
                            message="Please enter 'true', 'false', 'y', or 'n'"
                        )

                # For other types, try to convert
                try:
                    self._convert_input(text, field_type)
                    return True
                except (ValueError, TypeError) as exc:
                    raise PTValidationError(message=f"Invalid value: {exc}") from exc

            return Validator.from_callable(validate_type)
        except Exception as e:
            return e

    @staticmethod
    def _convert_input(user_input: str, target_type: Any) -> Union[Any, Exception]:
        """
        Convert user input to the target type, handling various types like lists and JSON.

        Args:
            user_input: Raw user input string
            target_type: Target type to convert to

        Returns:
            The converted value
        """
        try:
            # Handle Optional types
            if hasattr(target_type, "__origin__") and target_type.__origin__ is Union:
                # Get the non-None type from Optional[T] or Union[T, None]
                args = [arg for arg in target_type.__args__ if arg is not type(None)]
                if len(args) == 1:
                    target_type = args[0]
                else:
                    # For complex unions, we can't reliably convert, so just return string
                    return user_input

            # Handle lists
            if hasattr(target_type, "__origin__") and target_type.__origin__ in (
                list,
                List,
            ):
                item_type = (
                    target_type.__args__[0] if target_type.__args__ else str
                )  # Default to list of strings
                # Split by comma and strip whitespace
                items = [item.strip() for item in user_input.split(",")]
                # Convert each item to the target type
                converted_list = [
                    UserPrompt._convert_input(item, item_type) for item in items
                ]
                exception_items = [
                    item for item in converted_list if isinstance(item, Exception)
                ]
                if exception_items:
                    return exception_items[0]
                return converted_list

            # Handle JSON/Dict
            if user_input.startswith("{") and user_input.endswith("}"):
                try:
                    return json.loads(user_input)
                except json.JSONDecodeError as exc:
                    raise ValueError("Invalid JSON format") from exc

            # Handle boolean conversion
            if target_type is bool:
                if user_input.lower() in ["true", "y", "yes"]:
                    return True
                elif user_input.lower() in ["false", "n", "no"]:
                    return False
                else:
                    raise ValueError(f"Cannot convert '{user_input}' to boolean")

            # Default conversion
            try:
                return target_type(user_input)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Cannot convert '{user_input}' to type {target_type.__name__}"
                ) from exc
        except Exception as e:
            return e

    @staticmethod
    def prompt_for_single_field(
        field_name: str,
        field_type: Type[Any],
        description: str = "",
        default: Any = None,
    ) -> Union[Any, Exception]:
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
        try:
            prompt_instance = UserPrompt()
            _ = {
                "annotation": field_type,
                "description": description,
                "default": default,
            }
            # Mock field_info object for _prompt_for_field
            from types import SimpleNamespace

            mock_field_info = SimpleNamespace(
                annotation=field_type,
                description=description,
                is_required=lambda: default is None,
                get_default=lambda: default,
            )
            return prompt_instance._prompt_for_field(field_name, mock_field_info)
        except Exception as e:
            return e

    @staticmethod
    def confirm_action(message: str = "Continue?") -> Union[bool, Exception]:
        """
        Prompt the user for a yes/no confirmation.

        Args:
            message: The confirmation message

        Returns:
            bool: True if user confirms, False otherwise
        """
        try:
            session = PromptSession(style=PROMPT_STYLE)
            prompt_text = FormattedText([("class:field", f"\n{message} (y/n): ")])

            while True:
                response = session.prompt(prompt_text).strip().lower()
                if response in ["y", "yes"]:
                    return True
                elif response in ["n", "no"]:
                    return False
                else:
                    error_text = FormattedText(
                        [("class:error", "❌ Please enter 'y' or 'n'.\n")]
                    )
                    print_formatted_text(error_text)
        except Exception as e:
            return e

    @staticmethod
    def prompt_for_model_fields(
        model_class: Type[T],
        fields_to_prompt: List[str],
        existing_data: Optional[Dict[str, Any]] = None,
        title: str = None,
    ) -> Union[T, Exception]:
        """
        Prompt the user for specific fields of a Pydantic model.

        Args:
            model_class: The Pydantic model class to prompt for
            fields_to_prompt: List of field names to prompt for
            existing_data: Optional existing data to pre-populate fields
            title: Optional title to display at the top of the prompt

        Returns:
            An instance of the specified Pydantic model
        """
        try:
            return UserPrompt.prompt_for_model(
                model_class, existing_data, title, fields_to_prompt
            )
        except Exception as e:
            return e


def yes_no_prompt(message: str = "Continue?") -> bool:
    """
    Simple yes/no prompt function.

    Args:
        message: The message to display

    Returns:
        True for 'y' or 'yes', False for 'n' or 'no'
    """
    try:
        while True:
            response = input(f"{message} (y/n): ").lower().strip()
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                print("Please enter 'y' or 'n'")
    except Exception:
        return False
