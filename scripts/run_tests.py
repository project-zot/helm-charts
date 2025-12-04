#!/usr/bin/env python3
"""
Test runner for all chart tracker scripts
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_test_file(test_file, verbose=False):
    """Run a test file and return success status"""
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print(f"{'='*60}")

    try:
        result = subprocess.run([sys.executable, test_file],
                              capture_output=not verbose,
                              text=True)

        # Show output if verbose or if there are failures
        if verbose:
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        elif result.returncode != 0:
            print(result.stdout)
            print(result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"Error running {test_file}: {e}")
        return False

def main():
    """Run all test files"""
    parser = argparse.ArgumentParser(description="Run chart tracker tests")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Show detailed test output")
    args = parser.parse_args()

    scripts_dir = Path(__file__).parent

    test_files = [
        scripts_dir / "test_bump_chart_version.py",
        scripts_dir / "test_chart_tracker.py",
        scripts_dir / "test_chart_tracker_integration.py"
    ]

    print("Chart Tracker Test Suite")
    print("=" * 60)

    all_passed = True
    for test_file in test_files:
        if test_file.exists():
            success = run_test_file(str(test_file), verbose=args.verbose)
            if not success:
                all_passed = False
        else:
            print(f"Warning: Test file {test_file} not found")
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
