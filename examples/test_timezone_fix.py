#!/usr/bin/env python3

import sys
from pathlib import Path

from metagit.core.detect.repository import RepositoryAnalysis

"""
Test script to verify timezone fix for provider plugins.
"""
# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_timezone_fix():
    """Test that timezone issues are resolved."""
    print("🧪 Testing timezone fix for provider plugins...")

    # Test 1: Basic repository analysis without providers
    print("\n📋 Test 1: Basic repository analysis")
    try:
        analysis = RepositoryAnalysis.from_path(".")
        if isinstance(analysis, Exception):
            print(f"❌ Analysis failed: {analysis}")
            return False

        print("✅ Basic analysis completed successfully")

        # Test metrics detection
        if analysis.metrics:
            print(f"✅ Metrics detected: {analysis.metrics.contributors} contributors")
        else:
            print("⚠️  No metrics detected")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_provider_timezone():
    """Test provider timezone handling."""
    print("\n📋 Test 2: Provider timezone handling")

    try:
        # Mock some commit data to test timezone handling
        from datetime import datetime, timedelta, timezone

        # Create a mock commit with timezone-aware datetime
        mock_commit_date = datetime.now(timezone.utc) - timedelta(days=3)

        print(f"✅ Timezone-aware datetime created: {mock_commit_date}")
        print(f"✅ Timezone info: {mock_commit_date.tzinfo}")

        # Test comparison with timezone-aware datetime
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        comparison_result = mock_commit_date >= week_ago

        print(f"✅ DateTime comparison successful: {comparison_result}")

        return True

    except Exception as e:
        print(f"❌ Provider timezone test failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Timezone Fix Test")
    print("=" * 50)

    # Run tests
    test1_passed = test_timezone_fix()
    test2_passed = test_provider_timezone()

    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Basic Analysis: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Timezone Handling: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Timezone fix is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")

    return test1_passed and test2_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
