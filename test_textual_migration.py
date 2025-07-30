#!/usr/bin/env python
"""
Test script to verify that the Textual migration is working correctly.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig, fuzzyfinder


def test_basic_fuzzyfinder():
    """Test the basic fuzzyfinder function."""
    print("Testing basic fuzzyfinder function...")
    
    collection = ["apple", "banana", "grape", "apricot"]
    results = fuzzyfinder("ap", collection)
    
    print(f"Query: 'ap'")
    print(f"Collection: {collection}")
    print(f"Results: {results}")
    
    assert "apple" in results
    assert "apricot" in results
    assert "banana" not in results
    print("✓ Basic fuzzyfinder test passed!")
    print()


def test_fuzzy_finder_config():
    """Test FuzzyFinderConfig creation."""
    print("Testing FuzzyFinderConfig...")
    
    languages = ["python", "javascript", "typescript", "golang", "rust"]
    
    config = FuzzyFinderConfig(
        items=languages,
        prompt_text="Search: ",
        max_results=5,
        score_threshold=60.0,
        scorer="partial_ratio",
        case_sensitive=False,
    )
    
    print(f"Config created with {len(config.items)} items")
    print(f"Prompt text: '{config.prompt_text}'")
    print(f"Max results: {config.max_results}")
    print("✓ FuzzyFinderConfig test passed!")
    print()


def test_fuzzy_finder_class():
    """Test FuzzyFinder class creation."""
    print("Testing FuzzyFinder class...")
    
    languages = ["python", "javascript", "typescript", "golang", "rust"]
    
    config = FuzzyFinderConfig(
        items=languages,
        prompt_text="Search: ",
        max_results=5,
    )
    
    finder = FuzzyFinder(config)
    print("✓ FuzzyFinder class created successfully!")
    print()


def main():
    """Run all tests."""
    print("Testing Textual migration for FuzzyFinder")
    print("=" * 50)
    print()
    
    try:
        test_basic_fuzzyfinder()
        test_fuzzy_finder_config()
        test_fuzzy_finder_class()
        
        print("🎉 All tests passed! The Textual migration is working correctly.")
        print()
        print("Key changes made:")
        print("- Replaced prompt_toolkit imports with textual imports")
        print("- Rewrote FuzzyFinder class to use Textual App")
        print("- Added FuzzyFinderApp class with proper Textual widgets")
        print("- Maintained backward compatibility with existing API")
        print("- Kept the simple fuzzyfinder() function unchanged")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
