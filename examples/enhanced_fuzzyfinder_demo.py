#!/usr/bin/env python
"""
Example demonstrating the enhanced FuzzyFinder features:
- Optional item opacity
- Vertical scrolling for large lists
- Enhanced navigation (Page Up/Down, Home/End)
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def main():
    """Demonstrate enhanced FuzzyFinder features."""
    
    # Create a larger dataset to show scrolling
    programming_languages = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "Clojure", "Haskell", "Erlang",
        "Elixir", "Dart", "Lua", "Perl", "R", "MATLAB", "Julia", "F#", "OCaml",
        "Assembly", "C", "Objective-C", "Pascal", "Fortran", "COBOL", "Ada"
    ]
    
    print("Enhanced FuzzyFinder Demo")
    print("=" * 30)
    print(f"Dataset: {len(programming_languages)} programming languages")
    print()
    print("New Features:")
    print("1. ✨ Item opacity (80% transparency)")
    print("2. 📜 Vertical scrolling for long lists")
    print("3. 🚀 Enhanced navigation:")
    print("   - Arrow keys: Move up/down")
    print("   - Page Up/Down: Jump by 10 items")
    print("   - Home/End: Jump to first/last")
    print("4. 🎯 Auto-scroll to highlighted item")
    print()
    
    # Configure with new features
    config = FuzzyFinderConfig(
        items=programming_languages,
        prompt_text="Search programming languages: ",
        max_results=25,  # Show many results to demonstrate scrolling
        score_threshold=40.0,
        item_opacity=0.8,  # 80% opacity for subtle transparency
        highlight_color="bold white bg:#2563eb",  # Nice blue highlight
        normal_color="white",
        sort_items=True
    )
    
    # Create and run the fuzzy finder
    finder = FuzzyFinder(config)
    
    print("Starting enhanced FuzzyFinder...")
    print("Try typing partial names like 'py', 'java', 'rust', etc.")
    
    try:
        result = finder.run()
        
        if result:
            print(f"\n🎉 You selected: {result}")
        else:
            print("\n👋 No selection made.")
            
    except KeyboardInterrupt:
        print("\n👋 Exited by user.")


if __name__ == "__main__":
    main()
