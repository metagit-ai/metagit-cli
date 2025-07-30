#! /usr/bin/env python3

from typing import Any, Callable, Dict, List, Optional, Union

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Static, ListView, ListItem, Label
from textual.binding import Binding
from pydantic import BaseModel, Field, field_validator
from rapidfuzz import fuzz, process

"""
This is a fuzzy finder that uses Textual and rapidfuzz to find items in a list.
I'm only doing this because I don't want to have to wrap the fzf binary in a python script.
"""


class FuzzyFinderTarget(BaseModel):
    """A target for a fuzzy finder."""

    name: str
    description: str


class FuzzyFinderConfig(BaseModel):
    """Configuration for a fuzzy finder using Textual and rapidfuzz."""

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
    preview_header: Optional[str] = Field(None, description="Header for preview pane.")
    sort_items: bool = Field(True, description="Whether to sort the items.")
    # Styling options
    highlight_color: str = Field(
        "bold white bg:#4444aa", description="Color/style for highlighted items."
    )
    normal_color: str = Field("white", description="Color/style for normal items.")
    prompt_color: str = Field("bold cyan", description="Color/style for prompt text.")
    separator_color: str = Field("gray", description="Color/style for separator line.")
    item_opacity: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Optional opacity for list items (0.0-1.0)."
    )

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


class FuzzyFinderApp(App):
    """A Textual app for fuzzy finding."""

    CSS = """
    .fuzzy-finder-input {
        dock: top;
        height: 3;
        border: solid $primary;
    }
    
    .fuzzy-finder-results {
        border: solid $primary;
        scrollbar-gutter: stable;
        overflow-y: auto;
        height: 1fr;
    }
    
    .fuzzy-finder-preview {
        dock: right;
        width: 40%;
        border: solid $primary;
        overflow-y: auto;
    }
    
    .highlighted {
        background: $primary;
        color: $text;
    }
    
    .list-item-normal {
        opacity: 1.0;
    }
    
    .list-item-opacity {
        /* Opacity will be set dynamically */
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("enter", "select", "Select"),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "cursor_home", "Home", show=False),
        Binding("end", "cursor_end", "End", show=False),
    ]

    def __init__(self, config: FuzzyFinderConfig, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.current_results: List[Any] = []
        self.selected_item: Optional[Any] = None
        self.highlighted_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Vertical():
            # Input field
            yield Input(
                placeholder=self.config.prompt_text,
                id="search_input",
                classes="fuzzy-finder-input",
            )

            if self.config.enable_preview:
                # Split layout with results and preview
                with Horizontal():
                    yield ListView(id="results_list", classes="fuzzy-finder-results")
                    yield Static("", id="preview_pane", classes="fuzzy-finder-preview")
            else:
                # Just results
                yield ListView(id="results_list", classes="fuzzy-finder-results")

    def on_mount(self) -> None:
        """Called when app starts."""
        # Initial search with empty query
        self._perform_search("")
        # Focus the input
        self.query_one("#search_input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Called when the input changes."""
        if event.input.id == "search_input":
            self._perform_search(event.value)

    def _perform_search(self, query: str) -> None:
        """Perform fuzzy search and update results."""
        try:
            results = self._search(query)
            if isinstance(results, Exception):
                # Handle error - for now just show empty results
                results = []

            self.current_results = results
            self.highlighted_index = 0
            self._update_results_list()

            if self.config.enable_preview:
                self._update_preview()

        except Exception:
            # Handle error gracefully
            self.current_results = []
            self._update_results_list()

    def _update_results_list(self) -> None:
        """Update the results ListView."""
        results_list = self.query_one("#results_list", ListView)
        results_list.clear()

        for i, result in enumerate(self.current_results):
            display_value = self.config.get_display_value(result)
            if isinstance(display_value, Exception):
                display_value = str(result)

            # Create list item
            item = ListItem(Label(display_value))
            
            # Apply highlighting
            if i == self.highlighted_index:
                item.add_class("highlighted")
            
            # Apply opacity if configured
            if self.config.item_opacity is not None:
                item.add_class("list-item-opacity")
                # Set opacity via inline style
                item.styles.opacity = self.config.item_opacity
            else:
                item.add_class("list-item-normal")
                
            results_list.append(item)

    def _update_preview(self) -> None:
        """Update the preview pane."""
        if not self.config.enable_preview:
            return

        preview_pane = self.query_one("#preview_pane", Static)

        if not self.current_results or self.highlighted_index >= len(
            self.current_results
        ):
            preview_pane.update("No preview available")
            return

        highlighted_item = self.current_results[self.highlighted_index]
        preview_value = self.config.get_preview_value(highlighted_item)

        if isinstance(preview_value, Exception) or preview_value is None:
            preview_value = str(highlighted_item)

        if self.config.preview_header:
            preview_text = f"{self.config.preview_header}\n\n{preview_value}"
        else:
            preview_text = preview_value

        preview_pane.update(preview_text)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Called when a list item is selected."""
        if event.list_view.id == "results_list" and self.current_results:
            # Update highlighted index based on selection
            self.highlighted_index = (
                event.item.index if hasattr(event.item, "index") else 0
            )
            if self.highlighted_index < len(self.current_results):
                self.selected_item = self.current_results[self.highlighted_index]
                self.exit(self.selected_item)

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        if self.current_results and self.highlighted_index > 0:
            self.highlighted_index -= 1
            self._update_results_list()
            self._scroll_to_highlighted()
            if self.config.enable_preview:
                self._update_preview()

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        if (
            self.current_results
            and self.highlighted_index < len(self.current_results) - 1
        ):
            self.highlighted_index += 1
            self._update_results_list()
            self._scroll_to_highlighted()
            if self.config.enable_preview:
                self._update_preview()

    def _scroll_to_highlighted(self) -> None:
        """Scroll the results list to ensure the highlighted item is visible."""
        try:
            results_list = self.query_one("#results_list", ListView)
            if self.highlighted_index < len(results_list.children):
                # Get the highlighted list item
                highlighted_item = results_list.children[self.highlighted_index]
                # Scroll to make the item visible
                results_list.scroll_to_widget(highlighted_item)
        except Exception:
            # If scrolling fails, continue without it
            pass

    def action_page_up(self) -> None:
        """Move cursor up by a page (10 items)."""
        if self.current_results:
            page_size = 10
            self.highlighted_index = max(0, self.highlighted_index - page_size)
            self._update_results_list()
            self._scroll_to_highlighted()
            if self.config.enable_preview:
                self._update_preview()

    def action_page_down(self) -> None:
        """Move cursor down by a page (10 items)."""
        if self.current_results:
            page_size = 10
            max_index = len(self.current_results) - 1
            self.highlighted_index = min(max_index, self.highlighted_index + page_size)
            self._update_results_list()
            self._scroll_to_highlighted()
            if self.config.enable_preview:
                self._update_preview()

    def action_cursor_home(self) -> None:
        """Move cursor to the first item."""
        if self.current_results:
            self.highlighted_index = 0
            self._update_results_list()
            self._scroll_to_highlighted()
            if self.config.enable_preview:
                self._update_preview()

    def action_cursor_end(self) -> None:
        """Move cursor to the last item."""
        if self.current_results:
            self.highlighted_index = len(self.current_results) - 1
            self._update_results_list()
            self._scroll_to_highlighted()
            if self.config.enable_preview:
                self._update_preview()

    def action_select(self) -> None:
        """Select the highlighted item."""
        if self.current_results and self.highlighted_index < len(self.current_results):
            self.selected_item = self.current_results[self.highlighted_index]
            self.exit(self.selected_item)
        else:
            self.exit(None)

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit(None)

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
                except Exception:
                    # If sorting fails, proceed without sorting
                    pass

            choices_with_originals = [
                (self.config.get_display_value(item), item) for item in items_to_search
            ]
            # Check for exceptions
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


class FuzzyFinder:
    """A reusable fuzzy finder using Textual and rapidfuzz with navigation support."""

    def __init__(self, config: FuzzyFinderConfig):
        """Initialize the fuzzy finder with a configuration."""
        self.config = config

    def run(self) -> Union[Optional[Union[str, List[str], Any]], Exception]:
        """Run the fuzzy finder application."""
        try:
            app = FuzzyFinderApp(self.config)
            result = app.run()

            if self.config.multi_select:
                # Multi-select not fully implemented yet
                return [result] if result else []
            return result
        except Exception as e:
            return e


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
