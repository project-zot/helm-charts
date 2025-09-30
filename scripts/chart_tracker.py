#!/usr/bin/env python3
"""
Chart Tracker - Manages chart version bumping with JSON state tracking
"""

import json
import os
import sys
import argparse
import subprocess
from pathlib import Path

# Import the version bumping function directly
from bump_chart_version import bump_patch_version


class ChartTracker:
    def __init__(self, state_file=".chart-tracker.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self):
        """Load the current state from JSON file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load state file {self.state_file}: {e}")

        return {
            "charts_to_bump": []
        }

    def _save_state(self):
        """Save the current state to JSON file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            print(f"Error: Could not save state file {self.state_file}: {e}")
            raise

    def add_chart(self, chart_path):
        """Add a chart to the bump list if not already present"""
        chart_path = str(chart_path)
        if chart_path not in self.state["charts_to_bump"]:
            self.state["charts_to_bump"].append(chart_path)
            return True
        return False

    def add_charts_from_list(self, chart_list):
        """Add multiple charts from a list"""
        for chart_path in chart_list:
            self.add_chart(chart_path)

    def add_charts_from_docs(self, doc_list):
        """Add charts based on changed documentation files"""
        for doc_path in doc_list:
            if doc_path.endswith('/README.md'):
                chart_path = os.path.dirname(doc_path)
                self.add_chart(chart_path)

    def save(self):
        """Save the current state"""
        self._save_state()

    def print_status(self):
        """Print the current status"""
        charts = self.state["charts_to_bump"]
        if charts:
            print(f"Charts to bump ({len(charts)}):")
            for chart in charts:
                print(f"  - {chart}")
        else:
            print("No charts to bump")

    def cleanup(self):
        """Clean up the state file after processing"""
        if self.state_file.exists():
            self.state_file.unlink()

    def run_helm_docs(self, charts_dir="charts"):
        """Run helm-docs and return list of changed documentation files"""
        try:
            # Run helm-docs
            result = subprocess.run(
                ["helm-docs", "--chart-search-root", charts_dir],
                capture_output=True,
                text=True,
                check=True
            )

            # Check which README.md files were modified or created
            result = subprocess.run(
                ["git", "status", "--porcelain", f"{charts_dir}/*/README.md"],
                capture_output=True,
                text=True
            )

            changed_docs = []
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and 'README.md' in line:
                        # Extract the file path (remove status prefix)
                        file_path = line.strip().split(None, 1)[1] if len(line.strip().split(None, 1)) > 1 else line.strip()
                        changed_docs.append(file_path)

            return changed_docs

        except subprocess.CalledProcessError as e:
            print(f"Error running helm-docs: {e}")
            return []

    def get_changed_charts_from_git(self, target_branch, since):
        """Get list of changed charts using git operations"""
        try:
            # Use git diff to find changed files between target branch and since commit
            result = subprocess.run(['git', 'diff', f'{target_branch}..{since}', '--name-only'],
                                   capture_output=True, text=True)
            if result.returncode != 0:
                return []

            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

            # Filter for chart directories
            changed_charts = []
            for file_path in changed_files:
                if file_path.startswith('charts/') and '/Chart.yaml' in file_path:
                    chart_dir = file_path.split('/Chart.yaml')[0]
                    if chart_dir not in changed_charts:
                        changed_charts.append(chart_dir)

            return changed_charts

        except Exception as e:
            print(f"Error getting changed charts: {e}")
            return []

    def check_version_bumps_in_commits(self, chart_paths, target_branch, since):
        """Check if chart versions have already been bumped in the commits"""
        charts_with_bumps = []

        for chart_path in chart_paths:
            chart_yaml = Path(chart_path) / "Chart.yaml"
            if not chart_yaml.exists():
                continue

            try:
                # Get the git diff for this specific Chart.yaml file
                result = subprocess.run(
                    ["git", "diff", f"{target_branch}...HEAD", "--", str(chart_yaml)],
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Check if the diff shows a version change
                if result.stdout.strip():
                    # Look for version changes in the diff
                    lines = result.stdout.split('\n')
                    version_changed = False
                    old_version = None
                    new_version = None

                    for line in lines:
                        # Look for version field changes (added/removed lines)
                        if line.startswith('-') and 'version:' in line:
                            # Extract old version
                            old_version = line.split('version:')[1].strip()
                        elif line.startswith('+') and 'version:' in line:
                            # Extract new version
                            new_version = line.split('version:')[1].strip()

                    # Only consider it a version bump if the version actually changed
                    if old_version and new_version and old_version != new_version:
                        version_changed = True

                    if version_changed:
                        print(f"Version already bumped in commits for: {chart_path}")
                        charts_with_bumps.append(chart_path)
                    else:
                        print(f"No version bump found in commits for: {chart_path}")
                else:
                    print(f"No changes to Chart.yaml in commits for: {chart_path}")

            except subprocess.CalledProcessError as e:
                print(f"Error checking git diff for {chart_path}: {e}")
                # If we can't check, assume no version bump
                continue

        return charts_with_bumps

    def bump_chart_versions(self):
        """Bump versions for all tracked charts"""
        for chart_path in self.state["charts_to_bump"]:
            try:
                if bump_patch_version(chart_path):
                    print(f"Bumped version for: {chart_path}")
                else:
                    print(f"Failed to bump version for: {chart_path}")
            except Exception as e:
                print(f"Error bumping version for {chart_path}: {e}")

    def process_all_changes(self, target_branch, since, charts_dir="charts"):
        """Process all chart changes and documentation updates"""
        # Get changed charts using git operations
        changed_charts = self.get_changed_charts_from_git(target_branch, since)
        if changed_charts:
            print(f"Found {len(changed_charts)} changed charts")

            # Check which charts already have version bumps in the commits
            charts_with_existing_bumps = self.check_version_bumps_in_commits(changed_charts, target_branch, since)

            # Only add charts that don't already have version bumps
            charts_needing_bumps = [chart for chart in changed_charts if chart not in charts_with_existing_bumps]

            if charts_needing_bumps:
                print(f"Adding {len(charts_needing_bumps)} charts that need version bumps")
                self.add_charts_from_list(charts_needing_bumps)
            else:
                print("All changed charts already have version bumps in commits")

        # Run helm-docs and get changed documentation
        changed_docs = self.run_helm_docs(charts_dir)
        if changed_docs:
            print(f"Found {len(changed_docs)} changed documentation files")
            self.add_charts_from_docs(changed_docs)

        # Save the state
        self.save()

        return len(self.state["charts_to_bump"]) > 0


def main():
    parser = argparse.ArgumentParser(description="Chart Tracker - Manage chart version bumping")
    parser.add_argument("--state-file", default=".chart-tracker.json",
                       help="Path to the state JSON file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Process command
    process_parser = subparsers.add_parser("process", help="Process all changes and detect charts to bump")
    process_parser.add_argument("--target-branch", required=True, help="Target branch for git diff comparison")
    process_parser.add_argument("--since", required=True, help="Since commit for git diff comparison")

    # Cleanup command
    subparsers.add_parser("cleanup", help="Remove state file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    tracker = ChartTracker(args.state_file)

    try:
        if args.command == "process":
            has_changes = tracker.process_all_changes(args.target_branch, args.since)
            if has_changes:
                print("Charts need version bumps:")
                tracker.print_status()
                tracker.bump_chart_versions()
                return 0
            else:
                print("No charts need version bumps")
                return 1

        elif args.command == "cleanup":
            tracker.cleanup()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())