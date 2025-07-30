#!/usr/bin/env python
"""
Example demonstrating custom colors per list item in FuzzyFinder.
This shows different ways to assign colors to individual items.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def test_string_items_with_colors():
    """Test custom colors with string items."""
    print("🎨 Test 1: String Items with Custom Colors")
    print("-" * 40)
    
    # Create items with different priorities/types
    items = [
        "critical_bug",
        "urgent_feature", 
        "normal_task",
        "low_priority",
        "documentation",
        "testing",
        "refactoring",
        "security_fix"
    ]
    
    # Define custom colors for different item types
    color_map = {
        "critical_bug": "bold red",
        "urgent_feature": "bold yellow", 
        "security_fix": "bold red bg:#440000",
        "normal_task": "green",
        "low_priority": "#888888",
        "documentation": "blue",
        "testing": "cyan",
        "refactoring": "magenta"
    }
    
    config = FuzzyFinderConfig(
        items=items,
        prompt_text="🔍 Search tasks (notice colors): ",
        max_results=10,
        custom_colors=color_map,
        item_opacity=0.9,
        highlight_color="bold white bg:#0066cc"
    )
    
    finder = FuzzyFinder(config)
    print("Each item type has its own color:")
    print("- 🔴 Critical/Security: Red")
    print("- 🟡 Urgent: Yellow") 
    print("- 🟢 Normal: Green")
    print("- ⚪ Low Priority: Gray")
    print("- 🔵 Documentation: Blue")
    print("- 🟦 Testing: Cyan")
    print("- 🟣 Refactoring: Magenta")
    print()
    
    result = finder.run()
    print(f"Selected: {result}" if result else "No selection made.")
    print()


def test_object_items_with_colors():
    """Test custom colors with object items."""
    print("🎨 Test 2: Object Items with Custom Colors")
    print("-" * 40)
    
    # Create task objects
    class Task:
        def __init__(self, name, priority, category):
            self.name = name
            self.priority = priority
            self.category = category
        
        def __str__(self):
            return f"{self.name} ({self.priority})"
    
    tasks = [
        Task("Fix login bug", "critical", "bug"),
        Task("Add user dashboard", "high", "feature"),
        Task("Update documentation", "medium", "docs"),
        Task("Write unit tests", "medium", "testing"),
        Task("Refactor auth module", "low", "refactor"),
        Task("Security audit", "critical", "security"),
        Task("Performance optimization", "high", "performance"),
        Task("UI polish", "low", "ui")
    ]
    
    # Color by priority
    priority_colors = {
        "critical": "bold white bg:#cc0000",
        "high": "bold yellow",
        "medium": "green", 
        "low": "#999999"
    }
    
    config = FuzzyFinderConfig(
        items=tasks,
        display_field="name",
        color_field="priority",  # Use priority field for color mapping
        custom_colors=priority_colors,
        prompt_text="🔍 Search tasks by priority color: ",
        max_results=10,
        item_opacity=0.85,
        highlight_color="bold white bg:#4400aa"
    )
    
    finder = FuzzyFinder(config)
    print("Tasks colored by priority:")
    print("- 🔴 Critical: Red background")
    print("- 🟡 High: Yellow")
    print("- 🟢 Medium: Green") 
    print("- ⚪ Low: Gray")
    print()
    
    result = finder.run()
    if result:
        print(f"Selected: {result.name} (Priority: {result.priority})")
    else:
        print("No selection made.")
    print()


def test_mixed_color_formats():
    """Test different color format specifications."""
    print("🎨 Test 3: Mixed Color Formats")
    print("-" * 40)
    
    items = [
        "hex_color",
        "named_color", 
        "background_only",
        "text_and_bg",
        "rich_markup"
    ]
    
    # Demonstrate different color formats
    color_formats = {
        "hex_color": "#ff6600",           # Hex color
        "named_color": "cyan",            # Named color
        "background_only": "bg:#ffff00",  # Background only
        "text_and_bg": "blue bg:#ffffcc", # Text and background
        "rich_markup": "bold magenta"     # Rich markup
    }
    
    config = FuzzyFinderConfig(
        items=items,
        prompt_text="🎨 Different color formats: ",
        custom_colors=color_formats,
        max_results=10,
        highlight_color="bold white bg:#006600"
    )
    
    finder = FuzzyFinder(config)
    print("Different color format examples:")
    print("- hex_color: Orange (#ff6600)")
    print("- named_color: Cyan")
    print("- background_only: Yellow background")
    print("- text_and_bg: Blue text on light yellow")
    print("- rich_markup: Bold magenta")
    print()
    
    result = finder.run()
    print(f"Selected: {result}" if result else "No selection made.")
    print()


def test_preview_with_colors():
    """Test custom colors with preview enabled."""
    print("🎨 Test 4: Custom Colors with Preview")
    print("-" * 40)
    
    class ColoredItem:
        def __init__(self, name, color_type, description):
            self.name = name
            self.color_type = color_type
            self.description = description
    
    items = [
        ColoredItem("Primary Action", "primary", "Main action button - most important user action"),
        ColoredItem("Secondary Action", "secondary", "Secondary button - alternative action"),
        ColoredItem("Success Message", "success", "Positive feedback - operation completed successfully"),
        ColoredItem("Warning Alert", "warning", "Caution message - potential issues or important info"),
        ColoredItem("Error State", "error", "Error feedback - something went wrong"),
        ColoredItem("Info Notice", "info", "Neutral information - general notices or tips")
    ]
    
    ui_colors = {
        "primary": "bold white bg:#0066cc",
        "secondary": "white bg:#666666", 
        "success": "bold white bg:#00aa00",
        "warning": "bold black bg:#ffaa00",
        "error": "bold white bg:#cc0000",
        "info": "white bg:#0088cc"
    }
    
    config = FuzzyFinderConfig(
        items=items,
        display_field="name",
        color_field="color_type",
        preview_field="description",
        preview_header="UI Element Details:",
        enable_preview=True,
        custom_colors=ui_colors,
        prompt_text="🎨 Search UI elements: ",
        max_results=10,
        item_opacity=0.9
    )
    
    finder = FuzzyFinder(config)
    print("UI elements with semantic colors and preview:")
    print("Navigate with arrows to see descriptions →")
    print()
    
    result = finder.run()
    if result:
        print(f"Selected: {result.name} ({result.color_type})")
    else:
        print("No selection made.")


def main():
    """Run all custom color demonstrations."""
    print("🌈 FuzzyFinder Custom Colors Demo")
    print("=" * 50)
    print()
    
    try:
        test_string_items_with_colors()
        test_object_items_with_colors() 
        test_mixed_color_formats()
        test_preview_with_colors()
        
        print("✅ All custom color tests completed!")
        print("\n🎨 Custom Color Features:")
        print("1. ✅ Color mapping for string items")
        print("2. ✅ Color mapping for object items with color_field")
        print("3. ✅ Multiple color formats (hex, named, background, combined)")
        print("4. ✅ Integration with opacity and highlighting")
        print("5. ✅ Works with preview mode")
        print("6. ✅ Graceful fallback if colors fail to apply")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user.")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    main()
