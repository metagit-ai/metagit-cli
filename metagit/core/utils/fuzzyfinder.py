import os
import sys
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, List, Optional, Union

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.styles import Style
from pydantic import BaseModel, Field, field_validator
from rapidfuzz import fuzz, process

"""
This is a fuzzy finder that uses prompt_toolkit and rapidfuzz to find items in a list.
I'm only doing this because I don't want to have to wrap the fzf binary in a python script.
"""


class FuzzyFinderTarget(BaseModel):
    """A target for a fuzzy finder."""

    name: str
    description: str


class FuzzyFinderConfig(BaseModel):
    """Configuration for a fuzzy finder using prompt_toolkit and rapidfuzz."""

    items: List[Union[str, Any]] = Field(
        ..., description="List of items to search. Can be strings or objects."
    )
    display_field: Optional[str] = Field(
        None, description="Field name to use for display/search if items are objects."
    )
    score_threshold: float = Field(
        70.0,
        ge=0.0,
        le=100.0,
        description="Minimum score (0-100) for a match to be included.",
    )
    max_results: int = Field(
        10, ge=1, description="Maximum number of results to display."
    )
    scorer: str = Field(
        "partial_ratio",
        description="Fuzzy matching scorer: 'partial_ratio', 'ratio', or 'token_sort_ratio'.",
    )
    prompt_text: str = Field(
        "> ", description="Prompt text displayed in the input field."
    )
    case_sensitive: bool = Field(
        False, description="Whether matching is case-sensitive."
    )
    multi_select: bool = Field(False, description="Allow selecting multiple items.")
    enable_preview: bool = Field(
        False, description="Enable preview pane for selected item."
    )
    preview_field: Optional[str] = Field(
        None, description="Field name to use for preview if items are objects."
    )
    preview_header: Optional[str] = Field(
        "Preview:", description="Header for preview pane."
    )
    sort_items: bool = Field(True, description="Whether to sort the items.")
    # Styling options
    highlight_color: str = Field(
        "bold white bg:#4444aa", description="Color/style for highlighted items."
    )
    normal_color: str = Field("white", description="Color/style for normal items.")
    prompt_color: str = Field("bold cyan", description="Color/style for prompt text.")
    separator_color: str = Field("gray", description="Color/style for separator line.")

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[Any], info: Any) -> List[Any]:
        """Ensure items are valid and consistent with display_field."""
        if not v:
            raise ValueError("Items list cannot be empty.")
        if (
            info.data.get("display_field")
            and not isinstance(v[0], str)
            and not hasattr(v[0], info.data["display_field"])
        ):
            raise ValueError(f"Objects must have field '{info.data['display_field']}'.")
        return v

    @field_validator("scorer")
    @classmethod
    def validate_scorer(cls, v: str) -> str:
        """Ensure scorer is valid."""
        valid_scorers = ["partial_ratio", "ratio", "token_sort_ratio"]
        if v not in valid_scorers:
            raise ValueError(f"Scorer must be one of {valid_scorers}.")
        return v

    @field_validator("preview_field")
    @classmethod
    def validate_preview_field(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Ensure preview_field is valid if enable_preview is True."""
        if info.data.get("enable_preview") and not v:
            raise ValueError(
                "preview_field must be specified when enable_preview is True."
            )
        if (
            v
            and info.data.get("items")
            and not isinstance(info.data["items"][0], str)
            and not hasattr(info.data["items"][0], v)
        ):
            raise ValueError(f"Objects must have field '{v}' for preview.")
        return v

    def get_scorer_function(self) -> Union[Callable[..., float], Exception]:
        """Return the rapidfuzz scorer function based on configuration."""
        try:
            scorer_map: Dict[str, Callable[..., float]] = {
                "partial_ratio": fuzz.partial_ratio,
                "ratio": fuzz.ratio,
                "token_sort_ratio": fuzz.token_sort_ratio,
            }
            return scorer_map[self.scorer]
        except Exception as e:
            return e

    def get_display_value(self, item: Any) -> Union[str, Exception]:
        """Extract the display value from an item."""
        try:
            if isinstance(item, str):
                return item
            if self.display_field:
                return str(getattr(item, self.display_field))
            return ValueError("display_field must be specified for non-string items.")
        except Exception as e:
            return e

    def get_preview_value(self, item: Any) -> Union[Optional[str], Exception]:
        """Extract the preview value from an item if preview is enabled."""
        try:
            if not self.enable_preview or not self.preview_field:
                return None
            if isinstance(item, str):
                return item
            return str(getattr(item, self.preview_field))
        except Exception as e:
            return e


class FuzzyFinder:
    """A reusable fuzzy finder using prompt_toolkit and rapidfuzz with navigation support."""

    def __init__(self, config: FuzzyFinderConfig):
        """Initialize the fuzzy finder with a configuration."""
        self.config = config
        self.input_buffer = Buffer()
        self.selected_items = []
        self.highlighted_index = 0  # Track the highlighted item
        self.current_results: List[Any] = []  # Track current search results

        # Create dynamic style based on configuration
        self.style = Style.from_dict(
            {
                "prompt": self.config.prompt_color,
                "highlighted": self.config.highlight_color,
                "normal": self.config.normal_color,
                "separator": self.config.separator_color,
                "query": "bold yellow",
                "input": self.config.normal_color,
            }
        )

        from prompt_toolkit.layout.containers import VSplit
        from prompt_toolkit.layout.controls import FormattedTextControl

        # Prompt window
        prompt_window = Window(
            FormattedTextControl(lambda: [("class:prompt", self.config.prompt_text)]),
            height=1,
            width=len(self.config.prompt_text) + 1,
            dont_extend_width=True,
        )
        # Input window
        self.input_window = Window(
            BufferControl(buffer=self.input_buffer),
            height=1,
            style="class:input",
        )
        # Combine prompt and input
        self.input_container = VSplit([prompt_window, self.input_window], padding=0)

        # Output window uses FormattedTextControl for styling
        self.output_control = FormattedTextControl(text="")
        self.output_window = Window(self.output_control)

        # Create preview window if enabled
        self.preview_control = FormattedTextControl(text="")
        self.preview_window = None
        if self.config.enable_preview:
            self.preview_window = Window(
                self.preview_control,
                height=10,  # Increased height for better visibility
                style="class:normal",
                char=" ",
                wrap_lines=True,  # Enable text wrapping
            )

        # Setup layout with styled separator
        separator_window = Window(height=1, char="-", style="class:separator")

        # Create layout components
        layout_components = [self.input_container, separator_window, self.output_window]

        # Add preview window if enabled
        if self.config.enable_preview and self.preview_window:
            preview_separator = Window(height=1, char="=", style="class:separator")
            layout_components.extend([preview_separator, self.preview_window])

        self.layout = Layout(HSplit(layout_components))

        # Setup key bindings
        self.bindings = KeyBindings()
        self._setup_key_bindings()

        # Connect input buffer to update results
        self.input_buffer.on_text_changed += self._on_text_changed

        # Initialize application
        self.app: Application[Any] = Application(
            layout=self.layout,
            key_bindings=self.bindings,
            full_screen=True,
            style=self.style,
            mouse_support=False,
        )

    def _setup_key_bindings(self) -> Union[None, Exception]:
        """Configure key bindings for the finder, including navigation."""
        try:

            @self.bindings.add("c-c")
            def _(event: Any) -> None:
                event.app.exit(result=None)

            @self.bindings.add("enter")
            def _(event: Any) -> None:
                if self.config.multi_select:
                    # In multi-select mode, toggle selection (not implemented here)
                    pass
                else:
                    selected = (
                        self.current_results[self.highlighted_index]
                        if self.current_results
                        else None
                    )
                    event.app.exit(result=selected if selected else None)

            @self.bindings.add("up")
            def _(_: Any) -> None:
                if self.highlighted_index > 0:
                    self.highlighted_index -= 1
                    self._update_output_buffer()

            @self.bindings.add("down")
            def _(_: Any) -> None:
                if self.highlighted_index < len(self.current_results) - 1:
                    self.highlighted_index += 1
                    self._update_output_buffer()

            return None
        except Exception as e:
            return e

    def _display_prompt(self) -> None:
        """Display the styled prompt text."""
        # This is now handled by the FloatContainer in the layout
        pass

    def _search(self, query: str) -> Union[List[Any], Exception]:
        """Perform fuzzy search based on the query."""
        try:
            items_to_search = self.config.items
            if self.config.sort_items:
                try:
                    # Sort items based on their display value
                    items_to_search = sorted(
                        items_to_search,
                        key=lambda item: str(self.config.get_display_value(item) or ""),
                    )
                except Exception as exc:
                    # If sorting fails (e.g., unorderable types), proceed without sorting
                    raise exc

            choices_with_originals = [
                (self.config.get_display_value(item), item) for item in items_to_search
            ]
            # check for exception
            choice_exceptions = [
                c[0] for c in choices_with_originals if isinstance(c[0], Exception)
            ]
            if choice_exceptions:
                return choice_exceptions[0]

            choices = [str(c[0]) for c in choices_with_originals]

            if not query:
                return [item[1] for item in choices_with_originals][
                    : self.config.max_results
                ]

            # Prepare query for case-insensitive matching
            query_lower = query.lower() if not self.config.case_sensitive else query

            scorer_func = self.config.get_scorer_function()
            if isinstance(scorer_func, Exception):
                return scorer_func

            # Get fuzzy search results
            results = process.extract(
                query,
                choices,
                scorer=scorer_func,
                limit=len(choices),  # Get all results for custom sorting
            )

            # Custom scoring and sorting to prioritize exact matches
            scored_results = []
            for result_str, score, index in results:
                if score < self.config.score_threshold:
                    continue

                choice_lower = (
                    result_str.lower() if not self.config.case_sensitive else result_str
                )

                # Calculate custom score based on match type
                custom_score = score

                # Bonus for exact matches
                if choice_lower == query_lower:
                    custom_score += 1000
                # Bonus for prefix matches
                elif choice_lower.startswith(query_lower):
                    custom_score += 500
                # Bonus for longer matches (more specific)
                elif len(choice_lower) > len(query_lower):
                    # Give bonus for items that are longer than the query
                    # This helps prioritize "metagit_cli" over "metagit" when typing "metagit_cli"
                    length_bonus = min(100, (len(choice_lower) - len(query_lower)) * 10)
                    custom_score += length_bonus

                scored_results.append(
                    (custom_score, result_str, choices_with_originals[index][1])
                )

            # Sort by custom score (highest first) and then by original string length (shorter first for same score)
            scored_results.sort(key=lambda x: (-x[0], len(x[1])))

            # Return the top results
            return [item[2] for item in scored_results[: self.config.max_results]]

        except Exception as e:
            return e

    def _update_output_buffer(self) -> Union[None, Exception]:
        """Update the output buffer with the current search results and highlight."""
        try:
            formatted_text: List[Any] = []
            for i, result in enumerate(self.current_results):
                display_value = self.config.get_display_value(result)
                if isinstance(display_value, Exception):
                    return display_value
                if i == self.highlighted_index:
                    formatted_text.append(("class:highlighted", f"> {display_value}\n"))
                else:
                    formatted_text.append(("class:normal", f"  {display_value}\n"))
            self.output_control.text = FormattedText(formatted_text)

            # Update preview if enabled (always update, even with no results)
            if self.config.enable_preview:
                self._update_preview()

            return None
        except Exception as e:
            return e

    def _update_preview(self) -> Union[None, Exception]:
        """Update the preview pane with information about the highlighted item."""
        try:
            if not self.current_results or self.highlighted_index >= len(
                self.current_results
            ):
                self.preview_control.text = FormattedText(
                    [("class:normal", "No preview available")]
                )
                return None

            highlighted_item = self.current_results[self.highlighted_index]
            preview_value = self.config.get_preview_value(highlighted_item)

            if isinstance(preview_value, Exception):
                return preview_value

            if preview_value is None:
                # Fallback to string representation
                preview_value = str(highlighted_item)

            # Format the preview text with better structure
            formatted_preview = [
                ("class:normal", f"{self.config.preview_header}\n"),
                ("class:normal", "─" * 40 + "\n"),
                ("class:normal", f"{preview_value}\n"),
                ("class:normal", "─" * 40 + "\n"),
            ]
            self.preview_control.text = FormattedText(formatted_preview)
            return None
        except Exception as e:
            return e

    def _on_text_changed(self, _: Any) -> Union[None, Exception]:
        """Handle text changes in the input buffer."""
        try:
            search_results = self._search(self.input_buffer.text)
            if isinstance(search_results, Exception):
                # How to show this to the user? For now, just exit.
                self.app.exit(result=search_results)
                return None
            self.current_results = search_results
            self.highlighted_index = 0
            update_result = self._update_output_buffer()
            if isinstance(update_result, Exception):
                self.app.exit(result=update_result)
                return update_result
            return None
        except Exception as e:
            self.app.exit(result=e)
            return e

    def run(self) -> Union[Optional[Union[str, List[str], Any]], Exception]:
        """Run the fuzzy finder application."""
        try:
            # Initialize with empty search
            init_result = self._on_text_changed(None)
            if isinstance(init_result, Exception):
                return init_result

            with suppress_stdout() as so:
                if isinstance(so, Exception):
                    return so
                result: Optional[Union[str, List[str], Any]] = self.app.run()

            if self.config.multi_select:
                return self.selected_items
            return result
        except Exception as e:
            return e


@contextmanager
def suppress_stdout() -> Generator[Any, None, None]:
    """A context manager to suppress stdout, for cleaner full-screen app display."""
    original_stdout = sys.stdout
    devnull = None
    try:
        devnull = open(os.devnull, "w")
        sys.stdout = devnull
        yield
    except Exception as e:
        yield e
    finally:
        if devnull:
            devnull.close()
        sys.stdout = original_stdout


def fuzzyfinder(query: str, collection: List[str]) -> List[str]:
    """
    Simple fuzzy finder function that returns matching items from a collection.

    Args:
        query: Search query string
        collection: List of strings to search in

    Returns:
        List of matching strings
    """
    if not query:
        return collection

    from rapidfuzz import fuzz, process

    # Use rapidfuzz to find matches
    results = process.extract(
        query, collection, scorer=fuzz.partial_ratio, limit=len(collection)
    )

    # Return items with score >= 70
    return [item for item, score, _ in results if score >= 70]
