#!/usr/bin/env python
"""
Test script to demonstrate the updated FuzzyFinder with opacity and scrolling features.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def create_large_dataset():
    """Create a large list of items to test scrolling."""
    items = []

    # Programming languages
    languages = [
        "Python",
        "JavaScript",
        "TypeScript",
        "Java",
        "C++",
        "C#",
        "Go",
        "Rust",
        "Ruby",
        "PHP",
        "Swift",
        "Kotlin",
        "Scala",
        "Clojure",
        "Haskell",
        "Erlang",
        "Elixir",
        "Dart",
        "Lua",
        "Perl",
        "R",
        "MATLAB",
        "Julia",
        "F#",
        "OCaml",
        "Scheme",
        "Racket",
        "Common Lisp",
        "Assembly",
        "C",
        "Objective-C",
        "Pascal",
        "Fortran",
        "COBOL",
        "Ada",
        "Prolog",
        "SQL",
        "HTML",
        "CSS",
        "XML",
        "JSON",
    ]

    # Frameworks and libraries
    frameworks = [
        "React",
        "Vue",
        "Angular",
        "Svelte",
        "Node.js",
        "Express",
        "FastAPI",
        "Django",
        "Flask",
        "Spring",
        "Laravel",
        "Rails",
        "ASP.NET",
        "Gin",
        "Echo",
        "Fiber",
        "Actix",
        "Phoenix",
        "Sinatra",
        "Koa",
        "Nest.js",
        "Next.js",
        "Nuxt.js",
        "Gatsby",
        "SvelteKit",
        "Remix",
        "Astro",
        "TensorFlow",
        "PyTorch",
        "Scikit-learn",
        "Pandas",
        "NumPy",
        "Matplotlib",
    ]

    # Tools and technologies
    tools = [
        "Docker",
        "Kubernetes",
        "Git",
        "GitHub",
        "GitLab",
        "BitBucket",
        "Jenkins",
        "CircleCI",
        "Travis CI",
        "GitHub Actions",
        "AWS",
        "Azure",
        "GCP",
        "Terraform",
        "Ansible",
        "Chef",
        "Puppet",
        "Vagrant",
        "VirtualBox",
        "VMware",
        "Redis",
        "MongoDB",
        "PostgreSQL",
        "MySQL",
        "SQLite",
        "Elasticsearch",
        "Apache",
        "Nginx",
        "Prometheus",
        "Grafana",
        "Kibana",
    ]

    # Add all items with some duplicates and variations
    items.extend(languages)
    items.extend(frameworks)
    items.extend(tools)

    # Add some prefixed variations to test searching
    for lang in languages[:10]:
        items.append(f"learn_{lang.lower()}")
        items.append(f"awesome_{lang.lower()}")

    return sorted(set(items))  # Remove duplicates and sort


def test_opacity_feature():
    """Test the opacity feature."""
    print("Testing Opacity Feature")
    print("=" * 30)

    items = ["apple", "banana", "cherry", "date", "elderberry"]

    config = FuzzyFinderConfig(
        items=items,
        prompt_text="Search with opacity (0.7): ",
        max_results=10,
        item_opacity=0.7,  # Set opacity to 70%
        highlight_color="bold white bg:#00aa00",
    )

    finder = FuzzyFinder(config)
    print("Starting FuzzyFinder with 70% opacity...")
    print("Notice how the items appear slightly transparent.")
    print("Use Ctrl+C to exit and proceed to scrolling test.")

    result = finder.run()
    print(f"Selected: {result}" if result else "No selection made.")
    print()


def test_scrolling_feature():
    """Test the scrolling feature with many items."""
    print("Testing Scrolling Feature")
    print("=" * 30)

    items = create_large_dataset()
    print(f"Created dataset with {len(items)} items")

    config = FuzzyFinderConfig(
        items=items,
        prompt_text="Search (try typing 'py' or 'java'): ",
        max_results=50,  # Show many results to test scrolling
        score_threshold=30.0,  # Lower threshold to get more results
        item_opacity=0.9,  # Slight transparency
        highlight_color="bold white bg:#0066cc",
    )

    finder = FuzzyFinder(config)
    print("Starting FuzzyFinder with large dataset...")
    print("Navigation tips:")
    print("- Arrow keys: Move up/down one item")
    print("- Page Up/Down: Move by 10 items")
    print("- Home/End: Jump to first/last item")
    print("- Type to filter results")
    print("- Enter to select, Ctrl+C to exit")

    result = finder.run()
    print(f"Selected: {result}" if result else "No selection made.")
    print()


def test_preview_with_scrolling():
    """Test preview feature with scrolling."""
    print("Testing Preview + Scrolling")
    print("=" * 30)

    # Create items with descriptions for preview
    class TechItem:
        def __init__(self, name, description):
            self.name = name
            self.description = description

    tech_items = [
        TechItem(
            "Python",
            "A high-level programming language known for its simplicity and versatility. Great for web development, data science, AI, and automation.",
        ),
        TechItem(
            "JavaScript",
            "The programming language of the web. Used for both frontend and backend development with Node.js.",
        ),
        TechItem(
            "React",
            "A popular JavaScript library for building user interfaces, especially single-page applications.",
        ),
        TechItem(
            "Docker",
            "A containerization platform that makes it easy to package and deploy applications.",
        ),
        TechItem(
            "Kubernetes",
            "An orchestration platform for managing containerized applications at scale.",
        ),
        TechItem(
            "PostgreSQL",
            "A powerful, open-source relational database system with advanced features.",
        ),
        TechItem(
            "Redis",
            "An in-memory data structure store used as a database, cache, and message broker.",
        ),
        TechItem(
            "FastAPI",
            "A modern, fast web framework for building APIs with Python 3.7+ and type hints.",
        ),
        TechItem(
            "Vue.js",
            "A progressive JavaScript framework for building user interfaces and single-page applications.",
        ),
        TechItem(
            "Go",
            "A programming language developed by Google, known for its simplicity and performance.",
        ),
    ]

    config = FuzzyFinderConfig(
        items=tech_items,
        display_field="name",
        preview_field="description",
        preview_header="Technology Description:",
        enable_preview=True,
        prompt_text="Search technologies: ",
        max_results=20,
        item_opacity=0.85,
        highlight_color="bold white bg:#aa4400",
    )

    finder = FuzzyFinder(config)
    print("Starting FuzzyFinder with preview pane...")
    print("The right panel shows details about the highlighted item.")

    result = finder.run()
    if result:
        print(f"Selected: {result.name} - {result.description[:50]}...")
    else:
        print("No selection made.")


def main():
    """Run all tests."""
    print("FuzzyFinder Enhanced Features Test")
    print("=" * 50)
    print()

    try:
        # Test 1: Opacity
        test_opacity_feature()

        # Test 2: Scrolling
        test_scrolling_feature()

        # Test 3: Preview with scrolling
        test_preview_with_scrolling()

        print("✅ All tests completed!")
        print("\nNew features demonstrated:")
        print("1. ✅ Item opacity (0.0-1.0) for visual styling")
        print("2. ✅ Vertical scrolling with proper ListView configuration")
        print("3. ✅ Enhanced navigation (Page Up/Down, Home/End)")
        print("4. ✅ Scroll-to-highlighted functionality")
        print("5. ✅ Works with large datasets (100+ items)")

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    main()
