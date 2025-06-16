import uuid
from typing import Any, List, Optional, Union

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl
from pydantic import BaseModel, Field, validator
from rapidfuzz import fuzz, process


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

    @validator("items")
    def validate_items(cls, v, values):
        """Ensure items are valid and consistent with display_field."""
        if not v:
            raise ValueError("Items list cannot be empty.")
        if values.get("display_field") and not isinstance(v[0], str):
            if not hasattr(v[0], values["display_field"]):
                raise ValueError(
                    f"Objects must have field '{values['display_field']}'."
                )
        return v

    @validator("scorer")
    def validate_scorer(cls, v):
        """Ensure scorer is valid."""
        valid_scorers = ["partial_ratio", "ratio", "token_sort_ratio"]
        if v not in valid_scorers:
            raise ValueError(f"Scorer must be one of {valid_scorers}.")
        return v

    @validator("preview_field")
    def validate_preview_field(cls, v, values):
        """Ensure preview_field is valid if enable_preview is True."""
        if values.get("enable_preview") and not v:
            raise ValueError(
                "preview_field must be specified when enable_preview is True."
            )
        if v and values.get("items") and not isinstance(values["items"][0], str):
            if not hasattr(values["items"][0], v):
                raise ValueError(f"Objects must have field '{v}' for preview.")
        return v

    def get_scorer_function(self):
        """Return the rapidfuzz scorer function based on configuration."""
        scorer_map = {
            "partial_ratio": fuzz.partial_ratio,
            "ratio": fuzz.ratio,
            "token_sort_ratio": fuzz.token_sort_ratio,
        }
        return scorer_map[self.scorer]

    def get_display_value(self, item: Any) -> str:
        """Extract the display value from an item."""
        if isinstance(item, str):
            return item
        if self.display_field:
            return str(getattr(item, self.display_field))
        raise ValueError("display_field must be specified for non-string items.")

    def get_preview_value(self, item: Any) -> Optional[str]:
        """Extract the preview value from an item if preview is enabled."""
        if not self.enable_preview or not self.preview_field:
            return None
        if isinstance(item, str):
            return item
        return str(getattr(item, self.preview_field))


class FuzzyFinder:
    """A reusable fuzzy finder using prompt_toolkit and rapidfuzz with navigation support."""

    def __init__(self, config: FuzzyFinderConfig):
        """Initialize the fuzzy finder with a configuration."""
        self.config = config
        self.input_buffer = Buffer()
        self.output_buffer = Buffer(multiline=True)
        self.selected_items = []
        self.highlighted_index = 0  # Track the highlighted item
        self.current_results = []  # Track current search results

        # Setup UI components
        self.input_window = Window(BufferControl(buffer=self.input_buffer), height=1)
        self.output_window = Window(BufferControl(buffer=self.output_buffer))

        # Setup layout
        self.layout = Layout(
            HSplit([self.input_window, Window(height=1, char="-"), self.output_window])
        )

        # Setup key bindings
        self.bindings = KeyBindings()
        self._setup_key_bindings()

        # Connect input buffer to update results
        self.input_buffer.on_text_changed += self._on_text_changed

        # Initialize application
        self.app = Application(
            layout=self.layout, key_bindings=self.bindings, full_screen=True
        )

    def _setup_key_bindings(self):
        """Configure key bindings for the finder, including navigation."""

        @self.bindings.add("c-c")
        def _(event):
            event.app.exit(result=None)

        @self.bindings.add("enter")
        def _(event):
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
        def _(event):
            if self.highlighted_index > 0:
                self.highlighted_index -= 1
                self._update_output_buffer()

        @self.bindings.add("down")
        def _(event):
            if self.highlighted_index < len(self.current_results) - 1:
                self.highlighted_index += 1
                self._update_output_buffer()

    def _search(self, query: str) -> List[str]:
        """Perform fuzzy search based on the query."""
        choices = [self.config.get_display_value(item) for item in self.config.items]
        if not query:
            return choices[: self.config.max_results]
        if not self.config.case_sensitive:
            query = query.lower()
            choices = [c.lower() if isinstance(c, str) else c for c in choices]
        results = process.extract(
            query,
            choices,
            scorer=self.config.get_scorer_function(),
            limit=self.config.max_results,
        )
        return [
            item for item, score, _ in results if score >= self.config.score_threshold
        ]

    def _update_output_buffer(self):
        """Update output buffer with current results, highlighting the selected item."""
        formatted_lines = []
        for i, item in enumerate(self.current_results):
            if i == self.highlighted_index:
                formatted_lines.append(HTML(f"<ansiblue>{item}</ansiblue>"))
            else:
                formatted_lines.append(item)
        self.output_buffer.text = "\n".join(str(line) for line in formatted_lines)

    def _on_text_changed(self, _):
        """Update output buffer when input changes."""
        query = self.input_buffer.text
        self.current_results = self._search(query)
        self.highlighted_index = min(
            self.highlighted_index, max(0, len(self.current_results) - 1)
        )
        self._update_output_buffer()

    def run(self) -> Optional[Union[str, List[str]]]:
        """Run the fuzzy finder and return selected item(s)."""
        # Initialize output buffer with initial results
        self._on_text_changed(None)
        result = self.app.run()
        if self.config.multi_select:
            return self.selected_items  # Return list for multi-select
        return result  # Return single item or None
