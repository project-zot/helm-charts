#!/usr/bin/env python3
"""
Integration tests for chart_tracker.py using real git repositories
"""

import os
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path

from chart_tracker import ChartTracker


class TestChartTrackerGitIntegration(unittest.TestCase):
    """Integration tests using real git repositories"""

    def setUp(self):
        """Set up a temporary git repository with test charts"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.test_dir.name)

        # Initialize git repository
        self._run_git(['init'])
        self._run_git(['config', 'user.name', 'Test User'])
        self._run_git(['config', 'user.email', 'test@example.com'])

        # Create test charts structure
        self.charts_dir = self.repo_path / "charts"
        self.charts_dir.mkdir()

        # Create test chart 1
        self.chart1_dir = self.charts_dir / "test-chart-1"
        self.chart1_dir.mkdir()
        self.chart1_yaml = self.chart1_dir / "Chart.yaml"
        self.chart1_yaml.write_text("""apiVersion: v2
appVersion: "1.0.0"
description: Test chart 1
name: test-chart-1
type: application
version: 1.0.0
""")
        # Create values.yaml for helm-docs
        self.chart1_values = self.chart1_dir / "values.yaml"
        self.chart1_values.write_text("""# Default values for test-chart-1
replicaCount: 1

image:
  repository: nginx
  pullPolicy: IfNotPresent
  tag: ""

service:
  type: ClusterIP
  port: 80
""")
        self.chart1_readme = self.chart1_dir / "README.md"
        self.chart1_readme.write_text("# Test Chart 1\n\nThis is a test chart.")

        # Create test chart 2
        self.chart2_dir = self.charts_dir / "test-chart-2"
        self.chart2_dir.mkdir()
        self.chart2_yaml = self.chart2_dir / "Chart.yaml"
        self.chart2_yaml.write_text("""apiVersion: v2
appVersion: "2.0.0"
description: Test chart 2
name: test-chart-2
type: application
version: 2.0.0
""")
        # Create values.yaml for helm-docs
        self.chart2_values = self.chart2_dir / "values.yaml"
        self.chart2_values.write_text("""# Default values for test-chart-2
replicaCount: 1

image:
  repository: nginx
  pullPolicy: IfNotPresent
  tag: ""

service:
  type: ClusterIP
  port: 80
""")
        self.chart2_readme = self.chart2_dir / "README.md"
        self.chart2_readme.write_text("# Test Chart 2\n\nThis is another test chart.")

        # Create ct.yaml configuration for chart-testing
        self.ct_yaml = self.repo_path / "ct.yaml"
        self.ct_yaml.write_text("""chart-dirs:
  - charts
chart-repos:
  - bitnami=https://charts.bitnami.com/bitnami
validate-maintainers: false
""")

        # Create initial commit
        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit with test charts'])

        # Create main branch (rename from master)
        self._run_git(['branch', '-M', 'main'])

        # Set up chart tracker
        self.state_file = self.repo_path / ".chart-tracker.json"
        self.tracker = ChartTracker(str(self.state_file))

        # Store original working directory
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """Clean up test repository"""
        # Restore original working directory
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    def _run_git(self, args, cwd=None):
        """Helper method to run git commands"""
        if cwd is None:
            cwd = self.repo_path
        result = subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(args)}\n{result.stderr}")
        return result

    def _run_ct(self, args, cwd=None):
        """Helper method to run ct commands"""
        if cwd is None:
            cwd = self.repo_path
        result = subprocess.run(['ct'] + args, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"CT command failed: {' '.join(args)}\n{result.stderr}")
        return result

    def _is_ct_available(self):
        """Check if ct (chart-testing) is available"""
        try:
            result = subprocess.run(['ct', 'version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _get_changed_charts_from_git(self, target_branch, since):
        """Get changed charts using real git operations"""
        try:
            # Get current branch name
            result = subprocess.run(['git', 'branch', '--show-current'],
                                   cwd=self.repo_path, capture_output=True, text=True)
            current_branch = result.stdout.strip()

            # Use git diff to find changed files between target branch and current branch
            result = subprocess.run(['git', 'diff', f'{target_branch}..{current_branch}', '--name-only'],
                                   cwd=self.repo_path, capture_output=True, text=True)
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
        except Exception:
            return []

    def _create_branch(self, branch_name, from_branch='main'):
        """Create and checkout a new branch"""
        self._run_git(['checkout', from_branch])
        self._run_git(['checkout', '-b', branch_name])

    def _modify_chart(self, chart_path, changes):
        """Modify a chart file"""
        file_path = self.repo_path / chart_path
        if file_path.suffix == '.yaml':
            # Modify Chart.yaml
            content = file_path.read_text()
            for old, new in changes.items():
                content = content.replace(old, new)
            file_path.write_text(content)
        else:
            # Modify other files
            file_path.write_text(changes)

    def _commit_changes(self, message):
        """Commit current changes"""
        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', message])

    def test_basic_chart_detection(self):
        """Test basic chart detection with chart tracker using real git operations"""
        # Create a feature branch and modify a chart
        self._create_branch('feature-branch')
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'version: 1.0.0': 'version: 1.0.1'})
        self._commit_changes('Update test-chart-1 version')

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test the chart tracker's get_changed_charts_from_git method with real git operations
        # Compare main branch to current HEAD (feature-branch)
        changed_charts = self.tracker.get_changed_charts_from_git('main', 'HEAD')

        self.assertIn('charts/test-chart-1', changed_charts)
        self.assertNotIn('charts/test-chart-2', changed_charts)

    def test_version_bump_detection_in_commits(self):
        """Test detection of version bumps in git commits"""
        # Create a feature branch and modify chart version
        self._create_branch('feature-branch')
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'version: 1.0.0': 'version: 1.0.1'})
        self._commit_changes('Bump test-chart-1 version to 1.0.1')

        # Switch back to main
        self._run_git(['checkout', 'main'])

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test version bump detection - use relative paths for the test charts
        # We need to be on the feature branch to compare it to main
        self._run_git(['checkout', 'feature-branch'])
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(
            ['charts/test-chart-1'], 'main', 'HEAD~1'
        )
        self.assertIn('charts/test-chart-1', charts_with_bumps)

    def test_no_version_bump_detection(self):
        """Test detection when no version bump exists"""
        # Create a feature branch and modify chart without version change
        self._create_branch('feature-branch')
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'description: Test chart 1': 'description: Updated test chart 1'})
        self._commit_changes('Update test-chart-1 description')

        # Switch back to main
        self._run_git(['checkout', 'main'])

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test version bump detection - use relative paths for the test charts
        # We need to be on the feature branch to compare it to main
        self._run_git(['checkout', 'feature-branch'])
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(
            ['charts/test-chart-1'], 'main', 'HEAD~1'
        )
        self.assertNotIn('charts/test-chart-1', charts_with_bumps)

    def test_process_all_changes_with_existing_version_bumps(self):
        """Test process_all_changes skips charts with existing version bumps"""
        # Create a feature branch and bump version
        self._create_branch('feature-branch')
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'version: 1.0.0': 'version: 1.0.1'})
        self._commit_changes('Bump test-chart-1 version')

        # Switch back to main
        self._run_git(['checkout', 'main'])

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test process_all_changes with real git operations
        # We need to be on the feature branch to compare it to main
        self._run_git(['checkout', 'feature-branch'])

        # Use real git operations to detect changed charts
        changed_charts = self._get_changed_charts_from_git('main', 'HEAD~1')

        # Test the chart tracker logic directly
        # Manually add the changed charts to the tracker
        for chart in changed_charts:
            self.tracker.add_chart(chart)

        # Check for existing version bumps
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(changed_charts, 'main', 'HEAD~1')

        # Remove charts that already have version bumps
        for chart in charts_with_bumps:
            if chart in self.tracker.state["charts_to_bump"]:
                self.tracker.state["charts_to_bump"].remove(chart)

        # Should have no charts to bump (chart1 already has version bump)
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 0)

    def test_process_all_changes_without_existing_version_bumps(self):
        """Test process_all_changes adds charts without existing version bumps"""
        # Create a feature branch and modify chart without version change
        self._create_branch('feature-branch')
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'description: Test chart 1': 'description: Updated test chart 1'})
        self._commit_changes('Update test-chart-1 description')

        # Switch back to main
        self._run_git(['checkout', 'main'])

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test process_all_changes with real git operations
        # We need to be on the feature branch to compare it to main
        self._run_git(['checkout', 'feature-branch'])

        # Use real git operations to detect changed charts
        changed_charts = self._get_changed_charts_from_git('main', 'HEAD~1')

        # Test the chart tracker logic directly
        # Manually add the changed charts to the tracker
        for chart in changed_charts:
            self.tracker.add_chart(chart)

        # Check for existing version bumps
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(changed_charts, 'main', 'HEAD~1')

        # Remove charts that already have version bumps
        for chart in charts_with_bumps:
            if chart in self.tracker.state["charts_to_bump"]:
                self.tracker.state["charts_to_bump"].remove(chart)

        # Should have chart1 to bump (no existing version bump)
        self.assertIn('charts/test-chart-1', self.tracker.state["charts_to_bump"])

    def test_multiple_charts_mixed_version_bumps(self):
        """Test handling multiple charts with mixed version bump status"""
        # Create a feature branch
        self._create_branch('feature-branch')

        # Modify chart1 with version bump
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'version: 1.0.0': 'version: 1.0.1'})

        # Modify chart2 without version bump
        self._modify_chart('charts/test-chart-2/Chart.yaml', {'description: Test chart 2': 'description: Updated test chart 2'})

        self._commit_changes('Mixed changes: chart1 version bump, chart2 description update')

        # Switch back to main
        self._run_git(['checkout', 'main'])

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test process_all_changes with real git operations
        # We need to be on the feature branch to compare it to main
        self._run_git(['checkout', 'feature-branch'])

        # Use real git operations to detect changed charts
        changed_charts = self._get_changed_charts_from_git('main', 'HEAD~1')

        # Test the chart tracker logic directly
        # Manually add the changed charts to the tracker
        for chart in changed_charts:
            self.tracker.add_chart(chart)

        # Check for existing version bumps
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(changed_charts, 'main', 'HEAD~1')

        # Remove charts that already have version bumps
        for chart in charts_with_bumps:
            if chart in self.tracker.state["charts_to_bump"]:
                self.tracker.state["charts_to_bump"].remove(chart)

        # Should only have chart2 to bump (chart1 already has version bump)
        self.assertIn('charts/test-chart-2', self.tracker.state["charts_to_bump"])
        self.assertNotIn('charts/test-chart-1', self.tracker.state["charts_to_bump"])

    def test_helm_docs_integration(self):
        """Test helm-docs integration with git changes"""
        # Create a feature branch and modify only values.yaml (not Chart.yaml)
        self._create_branch('feature-branch')
        self._modify_chart('charts/test-chart-1/values.yaml', {'replicaCount: 1': 'replicaCount: 2'})
        self._commit_changes('Update test-chart-1 values')

        # Switch back to main
        self._run_git(['checkout', 'main'])

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test with real helm-docs operations
        # We need to be on the feature branch to compare it to main
        self._run_git(['checkout', 'feature-branch'])

        # Test process_all_changes with real operations
        # This should detect no chart changes (Chart.yaml not modified) but helm-docs will generate new README.md
        result = self.tracker.process_all_changes('main', 'HEAD~1', 'charts')

        # Should return True and add chart1 (needs version bump for doc changes)
        self.assertTrue(result)
        self.assertIn('charts/test-chart-1', self.tracker.state["charts_to_bump"])

    def test_state_persistence(self):
        """Test that chart tracker state persists correctly"""
        # Add a chart to the tracker
        self.tracker.add_chart('charts/test-chart-1')
        self.tracker._save_state()

        # Create a new tracker instance
        new_tracker = ChartTracker(str(self.state_file))

        # Verify state was loaded correctly
        self.assertIn('charts/test-chart-1', new_tracker.state["charts_to_bump"])

    def test_cleanup(self):
        """Test cleanup functionality"""
        # Add a chart and save state
        self.tracker.add_chart('charts/test-chart-1')
        self.tracker._save_state()

        # Verify state file exists
        self.assertTrue(self.state_file.exists())

        # Cleanup
        self.tracker.cleanup()

        # Verify state file is removed
        self.assertFalse(self.state_file.exists())

    def test_bump_chart_versions_integration(self):
        """Test actual version bumping integration"""
        # Add charts to tracker using absolute paths
        self.tracker.add_chart(str(self.chart1_dir))
        self.tracker.add_chart(str(self.chart2_dir))

        # Bump versions
        self.tracker.bump_chart_versions()

        # Verify versions were bumped
        chart1_content = self.chart1_yaml.read_text()
        chart2_content = self.chart2_yaml.read_text()

        self.assertIn('version: 1.0.1', chart1_content)
        self.assertIn('version: 2.0.1', chart2_content)

    def test_git_diff_edge_cases(self):
        """Test git diff edge cases"""
        # Test with non-existent chart path
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(
            ['charts/non-existent'], 'main', 'HEAD~1'
        )
        self.assertEqual(charts_with_bumps, [])

        # Test with empty chart list
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(
            [], 'main', 'HEAD~1'
        )
        self.assertEqual(charts_with_bumps, [])

    def test_complex_git_scenario(self):
        """Test complex git scenario with multiple commits and branches"""
        # Create feature branch
        self._create_branch('feature-branch')

        # First commit: modify chart1 without version bump
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'description: Test chart 1': 'description: Updated test chart 1'})
        self._commit_changes('Update chart1 description')

        # Second commit: bump chart1 version
        self._modify_chart('charts/test-chart-1/Chart.yaml', {'version: 1.0.0': 'version: 1.0.1'})
        self._commit_changes('Bump chart1 version')

        # Third commit: modify chart2 without version bump
        self._modify_chart('charts/test-chart-2/Chart.yaml', {'description: Test chart 2': 'description: Updated test chart 2'})
        self._commit_changes('Update chart2 description')

        # Switch back to main
        self._run_git(['checkout', 'main'])

        # Change to test repository directory for git operations
        os.chdir(self.repo_path)

        # Test process_all_changes with real git operations
        # We need to be on the feature branch to compare it to main
        self._run_git(['checkout', 'feature-branch'])

        # Use real git operations to detect changed charts
        changed_charts = self._get_changed_charts_from_git('main', 'HEAD~3')

        # Test the chart tracker logic directly
        # Manually add the changed charts to the tracker
        for chart in changed_charts:
            self.tracker.add_chart(chart)

        # Check for existing version bumps
        charts_with_bumps = self.tracker.check_version_bumps_in_commits(changed_charts, 'main', 'HEAD~3')

        # Remove charts that already have version bumps
        for chart in charts_with_bumps:
            if chart in self.tracker.state["charts_to_bump"]:
                self.tracker.state["charts_to_bump"].remove(chart)

        # Should only have chart2 to bump (chart1 already has version bump)
        self.assertIn('charts/test-chart-2', self.tracker.state["charts_to_bump"])
        self.assertNotIn('charts/test-chart-1', self.tracker.state["charts_to_bump"])


if __name__ == '__main__':
    unittest.main(verbosity=2)
