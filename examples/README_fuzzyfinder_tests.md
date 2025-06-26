# FuzzyFinder Test Scripts

This directory contains test scripts that demonstrate the functionality of the `FuzzyFinder` utility from the `metagit.core.utils.fuzzyfinder` module.

## Overview

The `FuzzyFinder` is a powerful interactive search tool that provides:
- Fuzzy text matching using rapidfuzz
- Interactive navigation with arrow keys
- Preview pane for detailed information
- Customizable styling and configuration
- Support for both string lists and object lists

## Test Scripts

### 1. `fuzzyfinder_simple_test.py`
**Purpose**: Basic demonstration with simple string list
**Features**:
- Uses a list of programming language names
- Shows basic search functionality
- Demonstrates navigation and selection

**Usage**:
```bash
python examples/fuzzyfinder_simple_test.py
```

### 2. `fuzzyfinder_preview_test.py`
**Purpose**: Demonstrates preview functionality with object list
**Features**:
- Uses `ProjectFile` objects with multiple attributes
- Shows preview pane with file descriptions
- Demonstrates `display_field` and `preview_field` configuration

**Usage**:
```bash
python examples/fuzzyfinder_preview_test.py
```

### 3. `fuzzyfinder_comprehensive_test.py`
**Purpose**: Comprehensive demonstration of all features
**Features**:
- Multiple test configurations
- Different scorers (partial_ratio, token_sort_ratio)
- Case-sensitive vs case-insensitive search
- Various score thresholds
- Different styling configurations

**Usage**:
```bash
python examples/fuzzyfinder_comprehensive_test.py
```

## Key Features Demonstrated

### Object Support
The FuzzyFinder can work with both simple strings and complex objects:

```python
# Simple string list
config = FuzzyFinderConfig(
    items=["python", "javascript", "typescript"],
    prompt_text="Search: "
)

# Object list with custom fields
config = FuzzyFinderConfig(
    items=file_objects,
    display_field="name",      # Field to display and search
    preview_field="description", # Field to show in preview
    enable_preview=True
)
```

### Preview Functionality
When `enable_preview=True` is set, the FuzzyFinder shows a preview pane below the search results:

```python
config = FuzzyFinderConfig(
    items=files,
    display_field="name",
    preview_field="description",
    enable_preview=True,
    prompt_text="Search files: "
)
```

### Different Scorers
The FuzzyFinder supports multiple fuzzy matching algorithms:

- `partial_ratio`: Best for partial string matches
- `ratio`: Best for exact string similarity
- `token_sort_ratio`: Best for word order variations

```python
config = FuzzyFinderConfig(
    items=items,
    scorer="token_sort_ratio",  # or "partial_ratio", "ratio"
    score_threshold=70.0
)
```

### Custom Styling
You can customize the appearance with different colors and styles:

```python
config = FuzzyFinderConfig(
    items=items,
    highlight_color="bold white bg:#0066cc",
    normal_color="white",
    prompt_color="bold green",
    separator_color="gray"
)
```

## Navigation Controls

- **Arrow Keys**: Navigate up/down through results
- **Type**: Search/filter results
- **Enter**: Select highlighted item
- **Ctrl+C**: Exit without selection

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `items` | List | Required | Items to search (strings or objects) |
| `display_field` | str | None | Field name for display/search (objects only) |
| `preview_field` | str | None | Field name for preview (objects only) |
| `enable_preview` | bool | False | Enable preview pane |
| `score_threshold` | float | 70.0 | Minimum match score (0-100) |
| `max_results` | int | 10 | Maximum results to display |
| `scorer` | str | "partial_ratio" | Fuzzy matching algorithm |
| `case_sensitive` | bool | False | Case-sensitive matching |
| `prompt_text` | str | "> " | Input prompt text |
| `highlight_color` | str | "bold white bg:#4444aa" | Highlighted item style |
| `normal_color` | str | "white" | Normal item style |
| `prompt_color` | str | "bold cyan" | Prompt text style |
| `separator_color` | str | "gray" | Separator line style |

## Example Output

When running the preview test, you'll see an interface like this:

```
Search files: py
> main.py
  api.py
  database.py
  models.py
  utils.py
  middleware.py
  cli.py
=====================================
Preview:
Main application entry point with CLI interface and core functionality
```

## Requirements

The test scripts require the following dependencies:
- `prompt_toolkit`: For the interactive terminal interface
- `rapidfuzz`: For fuzzy string matching
- `pydantic`: For configuration validation

These should be installed as part of the metagit package dependencies.

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure you're running from the project root directory
2. **Display Issues**: Ensure your terminal supports the color codes used
3. **Navigation Problems**: Check that your terminal supports arrow key input

### Debug Mode

To see more detailed error information, you can modify the scripts to catch and display exceptions:

```python
try:
    result = finder.run()
    if isinstance(result, Exception):
        print(f"Error: {result}")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc() 