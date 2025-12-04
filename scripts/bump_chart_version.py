#!/usr/bin/env python3
"""
Bump chart version - Automatically increment patch version of a Helm chart
"""

import argparse
import sys
import yaml
from pathlib import Path


def bump_patch_version(chart_path):
    """
    Bump the patch version of a Helm chart by 1

    Args:
        chart_path (str): Path to the chart directory

    Returns:
        bool: True if successful, False otherwise
    """
    chart_path = Path(chart_path)
    chart_yaml = chart_path / "Chart.yaml"

    if not chart_yaml.exists():
        print(f"Error: Chart.yaml not found at {chart_yaml}")
        return False

    try:
        # Read and parse the Chart.yaml file
        with open(chart_yaml, 'r') as f:
            chart_data = yaml.safe_load(f)

        if not chart_data or 'version' not in chart_data:
            print(f"Error: No version field found in {chart_yaml}")
            return False

        current_version = chart_data['version']
        print(f"Current version: {current_version}")

        # Parse the version string
        try:
            version_parts = current_version.split('.')
            if len(version_parts) != 3:
                raise ValueError("Invalid version format")

            major, minor, patch = version_parts
            major, minor, patch = int(major), int(minor), int(patch)

        except (ValueError, IndexError):
            print(f"Error: Could not parse version format: {current_version}")
            print("Expected format: major.minor.patch (e.g., 1.2.3)")
            return False

        # Increment patch version
        new_patch = patch + 1
        new_version = f"{major}.{minor}.{new_patch}"

        print(f"New version: {new_version}")

        # Update the version in the chart data
        chart_data['version'] = new_version

        # Write the updated Chart.yaml file
        with open(chart_yaml, 'w') as f:
            yaml.dump(chart_data, f, default_flow_style=False, sort_keys=False)

        print(f"Updated {chart_yaml} to version {new_version}")
        return True

    except yaml.YAMLError as e:
        print(f"Error parsing YAML in {chart_yaml}: {e}")
        return False
    except Exception as e:
        print(f"Error updating {chart_yaml}: {e}")
        return False


def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description="Bump patch version of a Helm chart")
    parser.add_argument("chart_path", help="Path to the chart directory")
    args = parser.parse_args()

    if bump_patch_version(args.chart_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
