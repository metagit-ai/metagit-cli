#!/usr/bin/env python
"""
Example demonstrating custom colors per list item in FuzzyFinder.
This shows different ways to assign colors to individual items, including:
1. FuzzyFinderTarget objects with built-in color/opacity properties
2. Custom color mapping via custom_colors configuration
3. Mixed approaches and fallback behavior
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig, FuzzyFinderTarget


def test_fuzzyfindertarget_with_colors():
    """Test FuzzyFinderTarget objects with built-in color and opacity properties."""
    print("🎨 Test 1: FuzzyFinderTarget Objects with Built-in Colors")
    print("-" * 55)
    
    # Create FuzzyFinderTarget objects with individual colors and opacity
    items = [
        FuzzyFinderTarget(
            name="Critical Bug Fix",
            description="Urgent security vulnerability needs immediate attention",
            color="bold white bg:#cc0000",  # Red background for critical
            opacity=1.0
        ),
        FuzzyFinderTarget(
            name="Feature Development", 
            description="New user dashboard implementation",
            color="bold yellow",  # Yellow for high priority
            opacity=0.9
        ),
        FuzzyFinderTarget(
            name="Code Refactoring",
            description="Clean up legacy authentication module",
            color="green",  # Green for normal priority
            opacity=0.8
        ),
        FuzzyFinderTarget(
            name="Documentation Update",
            description="Update API documentation and examples",
            color="#0088cc",  # Blue hex color for docs
            opacity=0.7
        ),
        FuzzyFinderTarget(
            name="Testing Suite",
            description="Add comprehensive unit tests for new features",
            color="cyan",  # Cyan for testing
            opacity=0.9
        ),
        FuzzyFinderTarget(
            name="Performance Optimization",
            description="Improve database query performance",
            color="magenta bg:#001122",  # Custom background
            opacity=0.85
        )
    ]
    
    # Note: custom_colors is defined but will be overridden by FuzzyFinderTarget properties
    fallback_colors = {
        "Critical Bug Fix": "red",  # This won't be used - object has its own color
        "Feature Development": "blue"  # This won't be used either
    }
    
    config = FuzzyFinderConfig(
        items=items,
        display_field="name",
        prompt_text="🔍 Search tasks (object colors): ",
        max_results=10,
        custom_colors=fallback_colors,  # These are fallbacks, won't be used
        item_opacity=0.5,  # This is fallback opacity, objects have their own
        highlight_color="bold white bg:#4400aa"
    )
    
    finder = FuzzyFinder(config)
    print("Each FuzzyFinderTarget has its own color and opacity:")
    print("- 🔴 Critical Bug: Red background, full opacity")
    print("- 🟡 Feature Dev: Yellow, 90% opacity")
    print("- 🟢 Refactoring: Green, 80% opacity")
    print("- 🔵 Documentation: Blue hex, 70% opacity")
    print("- 🟦 Testing: Cyan, 90% opacity") 
    print("- 🟣 Performance: Magenta with custom background, 85% opacity")
    print("\n💡 These colors come from the objects themselves, not custom_colors!")
    print()
    
    result = finder.run()
    if result:
        print(f"Selected: {result.name}")
        print(f"Description: {result.description}")
        print(f"Color: {result.color}")
        print(f"Opacity: {result.opacity}")
    else:
        print("No selection made.")
    print()


def test_mixed_object_types():
    """Test mixing FuzzyFinderTarget objects with regular objects."""
    print("🎨 Test 2: Mixed Object Types (FuzzyFinderTarget + Custom Objects)")
    print("-" * 65)
    
    # Mix FuzzyFinderTarget objects with regular objects
    class SimpleTask:
        def __init__(self, name, priority):
            self.name = name
            self.priority = priority
    
    items = [
        # FuzzyFinderTarget with built-in colors
        FuzzyFinderTarget(
            name="Security Audit",
            description="Comprehensive security review",
            color="bold red",
            opacity=1.0
        ),
        FuzzyFinderTarget(
            name="UI Polish",
            description="Final touches on user interface",
            color="#ff6600",
            opacity=0.8
        ),
        
        # Regular objects that will use custom_colors mapping
        SimpleTask("Database Migration", "high"),
        SimpleTask("Email Integration", "medium"),
        SimpleTask("Backup System", "low"),
    ]
    
    # Custom colors for regular objects (by name)
    color_mapping = {
        "Database Migration": "bold yellow bg:#332200",
        "Email Integration": "green", 
        "Backup System": "#888888"
    }
    
    config = FuzzyFinderConfig(
        items=items,
        display_field="name",
        custom_colors=color_mapping,
        item_opacity=0.6,  # Fallback opacity for regular objects
        prompt_text="🔍 Mixed object types: ",
        max_results=10,
        highlight_color="bold white bg:#006600"
    )
    
    finder = FuzzyFinder(config)
    print("Mixing FuzzyFinderTarget objects with regular objects:")
    print("- FuzzyFinderTarget objects use their own color/opacity")
    print("- Regular objects use custom_colors mapping and fallback opacity")
    print()
    
    result = finder.run()
    if result:
        if isinstance(result, FuzzyFinderTarget):
            print(f"Selected FuzzyFinderTarget: {result.name}")
            print(f"Built-in color: {result.color}, opacity: {result.opacity}")
        else:
            print(f"Selected regular object: {result.name}")
            print("Uses custom_colors mapping and fallback opacity")
    else:
        print("No selection made.")
    print()


def test_priority_demonstration():
    """Demonstrate the priority system: FuzzyFinderTarget properties override custom_colors."""
    print("🎨 Test 3: Priority System Demonstration")
    print("-" * 43)
    
    # Create items where custom_colors would conflict with object properties
    items = [
        FuzzyFinderTarget(
            name="Override Test",
            description="This item should be GREEN despite custom_colors saying red",
            color="green",  # Object says GREEN
            opacity=0.9
        ),
        FuzzyFinderTarget(
            name="Another Override",
            description="This should be BLUE despite custom_colors",
            color="blue",   # Object says BLUE
            opacity=0.7
        ),
        FuzzyFinderTarget(
            name="No Color Set", 
            description="This will fall back to custom_colors",
            # No color/opacity set - will use fallbacks
        )
    ]
    
    # Custom colors that would conflict with object properties
    conflicting_colors = {
        "Override Test": "red",      # Object overrides this with GREEN
        "Another Override": "yellow", # Object overrides this with BLUE  
        "No Color Set": "purple"     # This will be used (no object color)
    }
    
    config = FuzzyFinderConfig(
        items=items,
        display_field="name",
        custom_colors=conflicting_colors,
        item_opacity=0.5,  # Fallback opacity
        prompt_text="🔍 Priority system test: ",
        max_results=10
    )
    
    finder = FuzzyFinder(config)
    print("Priority system in action:")
    print("- 'Override Test': GREEN (object) not red (custom_colors)")
    print("- 'Another Override': BLUE (object) not yellow (custom_colors)")
    print("- 'No Color Set': PURPLE (falls back to custom_colors)")
    print("\n💡 FuzzyFinderTarget properties always take precedence!")
    print()
    
    result = finder.run()
    if result:
        print(f"Selected: {result.name}")
        print(f"Object color: {result.color or 'None (uses fallback)'}")
        print(f"Object opacity: {result.opacity or 'None (uses fallback)'}")
    else:
        print("No selection made.")
    print()


def test_string_items_with_colors():
    """Test custom colors with string items."""
    print("🎨 Test 4: String Items with Custom Colors (Legacy Method)")
    print("-" * 58)
    
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
    print("🎨 Test 5: Object Items with Custom Colors (Legacy Method)")
    print("-" * 56)
    
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
    print("🎨 Test 6: Mixed Color Formats")
    print("-" * 31)
    
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
    print("🎨 Test 7: Custom Colors with Preview")
    print("-" * 36)
    
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


def test_fuzzyfindertarget_with_preview():
    """Test FuzzyFinderTarget objects with preview functionality."""
    print("🎨 Test 8: FuzzyFinderTarget with Preview and Custom Colors")
    print("-" * 60)
    
    # Create FuzzyFinderTarget objects for UI components with rich descriptions
    items = [
        FuzzyFinderTarget(
            name="Primary Button",
            description="Main call-to-action button used for primary user actions like 'Save', 'Submit', or 'Continue'. Should be prominent and easily discoverable.",
            color="bold white bg:#0066cc",
            opacity=1.0
        ),
        FuzzyFinderTarget(
            name="Warning Alert",
            description="Alert component for cautionary messages. Used to warn users about potential issues or consequences before they take action.",
            color="bold black bg:#ffaa00", 
            opacity=0.95
        ),
        FuzzyFinderTarget(
            name="Success Message",
            description="Positive feedback component shown after successful operations. Confirms to users that their action was completed successfully.",
            color="bold white bg:#00aa00",
            opacity=0.9
        ),
        FuzzyFinderTarget(
            name="Error State",
            description="Error feedback component displayed when operations fail. Should clearly communicate what went wrong and suggest next steps.",
            color="bold white bg:#cc0000",
            opacity=1.0
        ),
        FuzzyFinderTarget(
            name="Loading Spinner",
            description="Progress indicator shown during asynchronous operations. Keeps users informed that the system is processing their request.",
            color="cyan",
            opacity=0.8
        )
    ]
    
    config = FuzzyFinderConfig(
        items=items,
        display_field="name",
        preview_field="description",
        preview_header="🎨 UI Component Details:",
        enable_preview=True,
        prompt_text="🔍 Search UI components: ",
        max_results=10,
        highlight_color="bold white bg:#4400aa"
    )
    
    finder = FuzzyFinder(config)
    print("FuzzyFinderTarget objects with preview and custom colors:")
    print("- Each component has its own semantic color and opacity")
    print("- Navigate with arrows to see detailed descriptions →")
    print("- Colors come directly from the objects, not configuration")
    print()
    
    result = finder.run()
    if result:
        print(f"Selected: {result.name}")
        print(f"Color: {result.color}")
        print(f"Opacity: {result.opacity}")
        print(f"Description: {result.description}")
    else:
        print("No selection made.")
    print()


def main():
    """Run all custom color demonstrations."""
    print("🌈 FuzzyFinder Custom Colors Demo - Updated with FuzzyFinderTarget")
    print("=" * 70)
    print()
    
    try:
        # New tests showcasing FuzzyFinderTarget objects
        test_fuzzyfindertarget_with_colors()
        test_mixed_object_types()
        test_priority_demonstration()
        test_fuzzyfindertarget_with_preview()
        
        # Legacy tests for custom_colors mapping
        test_string_items_with_colors()
        test_object_items_with_colors() 
        test_mixed_color_formats()
        test_preview_with_colors()
        
        print("✅ All custom color tests completed!")
        print("\n🎨 FuzzyFinder Color System Features:")
        print("=" * 40)
        print("🆕 NEW - FuzzyFinderTarget Objects:")
        print("   ✅ Built-in color and opacity properties")
        print("   ✅ Object properties override custom_colors mapping")
        print("   ✅ Perfect for type-safe, object-oriented design")
        print("   ✅ Works seamlessly with preview mode")
        print()
        print("🔄 LEGACY - Custom Colors Mapping:")
        print("   ✅ Color mapping for string items")
        print("   ✅ Color mapping for object items with color_field")
        print("   ✅ Multiple color formats (hex, named, background, combined)")
        print("   ✅ Fallback system when FuzzyFinderTarget has no color")
        print()
        print("🎯 PRIORITY SYSTEM:")
        print("   1. FuzzyFinderTarget.color/opacity (highest priority)")
        print("   2. custom_colors mapping (fallback)")
        print("   3. config.item_opacity (fallback for opacity)")
        print()
        print("💡 RECOMMENDATION: Use FuzzyFinderTarget objects for new code!")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user.")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
