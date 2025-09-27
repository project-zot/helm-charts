#!/usr/bin/env python3
"""
Unit tests for ChartTracker class
"""

import unittest
import os
import sys
import tempfile
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

# Import the module
from chart_tracker import ChartTracker


class TestChartTracker(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.test_dir.name) / "test-tracker.json"
        self.tracker = ChartTracker(str(self.state_file))

    def tearDown(self):
        """Clean up test fixtures"""
        self.test_dir.cleanup()

    def test_initialization_without_state_file(self):
        """Test initialization when state file doesn't exist"""
        tracker = ChartTracker("nonexistent.json")
        self.assertEqual(tracker.state, {"charts_to_bump": []})
        self.assertFalse(tracker.state_file.exists())

    def test_initialization_with_existing_state_file(self):
        """Test initialization with existing state file"""
        # Create a state file
        test_state = {"charts_to_bump": ["charts/test1", "charts/test2"]}
        with open(self.state_file, 'w') as f:
            json.dump(test_state, f)

        # Create new tracker
        tracker = ChartTracker(str(self.state_file))
        self.assertEqual(tracker.state, test_state)

    def test_initialization_with_invalid_json(self):
        """Test initialization with invalid JSON file"""
        # Create invalid JSON file
        with open(self.state_file, 'w') as f:
            f.write("invalid json content")

        # Should handle gracefully and use default state
        tracker = ChartTracker(str(self.state_file))
        self.assertEqual(tracker.state, {"charts_to_bump": []})

    def test_add_chart_new(self):
        """Test adding a new chart"""
        result = self.tracker.add_chart("charts/test")
        self.assertTrue(result)
        self.assertIn("charts/test", self.tracker.state["charts_to_bump"])

    def test_add_chart_duplicate(self):
        """Test adding a duplicate chart"""
        self.tracker.add_chart("charts/test")
        result = self.tracker.add_chart("charts/test")
        self.assertFalse(result)
        self.assertEqual(self.tracker.state["charts_to_bump"].count("charts/test"), 1)

    def test_add_charts_from_list(self):
        """Test adding multiple charts from a list"""
        charts = ["charts/test1", "charts/test2", "charts/test1"]  # test1 appears twice
        self.tracker.add_charts_from_list(charts)
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 2)
        self.assertIn("charts/test1", self.tracker.state["charts_to_bump"])
        self.assertIn("charts/test2", self.tracker.state["charts_to_bump"])

    def test_add_charts_from_docs(self):
        """Test adding charts from documentation file paths"""
        docs = [
            "charts/test1/README.md",
            "charts/test2/README.md",
            "charts/test3/values.yaml",  # Should be ignored
            "charts/test4/README.md"
        ]
        self.tracker.add_charts_from_docs(docs)
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 3)
        self.assertIn("charts/test1", self.tracker.state["charts_to_bump"])
        self.assertIn("charts/test2", self.tracker.state["charts_to_bump"])
        self.assertIn("charts/test4", self.tracker.state["charts_to_bump"])
        self.assertNotIn("charts/test3", self.tracker.state["charts_to_bump"])

    def test_save_and_load_state(self):
        """Test saving and loading state"""
        # Add some charts
        self.tracker.add_chart("charts/test1")
        self.tracker.add_chart("charts/test2")

        # Save state
        self.tracker.save()
        self.assertTrue(self.state_file.exists())

        # Create new tracker and verify it loads the state
        new_tracker = ChartTracker(str(self.state_file))
        self.assertEqual(new_tracker.state["charts_to_bump"], ["charts/test1", "charts/test2"])

    def test_print_status_with_charts(self):
        """Test print_status when charts are present"""
        self.tracker.add_chart("charts/test1")
        self.tracker.add_chart("charts/test2")

        with patch('builtins.print') as mock_print:
            self.tracker.print_status()
            mock_print.assert_called()
            # Check that the output contains chart names
            calls = [call[0][0] for call in mock_print.call_args_list]
            output = ' '.join(calls)
            self.assertIn("charts/test1", output)
            self.assertIn("charts/test2", output)

    def test_print_status_without_charts(self):
        """Test print_status when no charts are present"""
        with patch('builtins.print') as mock_print:
            self.tracker.print_status()
            mock_print.assert_called_with("No charts to bump")

    def test_cleanup(self):
        """Test cleanup removes state file"""
        # Create state file
        self.tracker.save()
        self.assertTrue(self.state_file.exists())

        # Cleanup
        self.tracker.cleanup()
        self.assertFalse(self.state_file.exists())

    def test_cleanup_without_state_file(self):
        """Test cleanup when state file doesn't exist"""
        # Should not raise an error
        self.tracker.cleanup()
        self.assertFalse(self.state_file.exists())

    @patch('subprocess.run')
    def test_run_helm_docs_success(self, mock_run):
        """Test successful helm-docs execution"""
        # Mock successful helm-docs run and git status
        mock_run.side_effect = [
            # First call: helm-docs
            type('MockResult', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            # Second call: git status
            type('MockResult', (), {'returncode': 0, 'stdout': '?? charts/test1/README.md\n M charts/test2/README.md\n'})()
        ]

        result = self.tracker.run_helm_docs()
        self.assertEqual(result, ["charts/test1/README.md", "charts/test2/README.md"])

        # Verify both commands were called
        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call(["helm-docs", "--chart-search-root", "charts"], capture_output=True, text=True, check=True)
        mock_run.assert_any_call(["git", "status", "--porcelain", "charts/*/README.md"], capture_output=True, text=True)

    @patch('subprocess.run')
    def test_run_helm_docs_failure(self, mock_run):
        """Test helm-docs execution failure"""
        # Mock failed helm-docs run
        mock_run.side_effect = subprocess.CalledProcessError(1, "helm-docs")

        result = self.tracker.run_helm_docs()
        self.assertEqual(result, [])

    @patch('subprocess.run')
    def test_get_changed_charts_from_git_success(self, mock_run):
        """Test successful git-based chart detection"""
        # Mock successful git diff operation
        mock_run.return_value = type('MockResult', (), {
            'returncode': 0,
            'stdout': 'charts/test1/Chart.yaml\ncharts/test2/Chart.yaml\n'
        })()

        result = self.tracker.get_changed_charts_from_git("main", "HEAD~1")
        self.assertEqual(result, ["charts/test1", "charts/test2"])

        # Verify git diff was called with correct parameters
        mock_run.assert_called_once_with(
            ['git', 'diff', 'main..HEAD~1', '--name-only'],
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_get_changed_charts_from_git_failure(self, mock_run):
        """Test git-based chart detection failure"""
        # Mock failed git run
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = self.tracker.get_changed_charts_from_git("main", "HEAD~1")
        self.assertEqual(result, [])

    @patch('chart_tracker.bump_patch_version')
    def test_bump_chart_versions_success(self, mock_bump):
        """Test successful version bumping"""
        # Add charts to bump
        self.tracker.add_chart("charts/test1")
        self.tracker.add_chart("charts/test2")

        # Mock successful version bumps
        mock_bump.return_value = True

        with patch('builtins.print') as mock_print:
            self.tracker.bump_chart_versions()

            # Verify bump_patch_version was called for each chart
            self.assertEqual(mock_bump.call_count, 2)
            mock_bump.assert_any_call("charts/test1")
            mock_bump.assert_any_call("charts/test2")

            # Verify success messages were printed
            calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertIn("Bumped version for: charts/test1", calls)
            self.assertIn("Bumped version for: charts/test2", calls)

    @patch('chart_tracker.bump_patch_version')
    def test_bump_chart_versions_failure(self, mock_bump):
        """Test version bumping with failures"""
        # Add charts to bump
        self.tracker.add_chart("charts/test1")
        self.tracker.add_chart("charts/test2")

        # Mock one success, one failure
        mock_bump.side_effect = [True, False]

        with patch('builtins.print') as mock_print:
            self.tracker.bump_chart_versions()

            # Verify both charts were attempted
            self.assertEqual(mock_bump.call_count, 2)

            # Verify success and failure messages
            calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertIn("Bumped version for: charts/test1", calls)
            self.assertIn("Failed to bump version for: charts/test2", calls)

    @patch('chart_tracker.bump_patch_version')
    def test_bump_chart_versions_exception(self, mock_bump):
        """Test version bumping with exceptions"""
        # Add charts to bump
        self.tracker.add_chart("charts/test1")

        # Mock exception
        mock_bump.side_effect = Exception("Test error")

        with patch('builtins.print') as mock_print:
            self.tracker.bump_chart_versions()

            # Verify error message was printed
            calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertIn("Error bumping version for charts/test1: Test error", calls)

    @patch.object(ChartTracker, 'get_changed_charts_from_git')
    @patch.object(ChartTracker, 'run_helm_docs')
    def test_process_all_changes_with_changes(self, mock_helm_docs, mock_ct):
        """Test process_all_changes when changes are detected"""
        # Mock chart changes
        mock_ct.return_value = ["charts/test1"]
        mock_helm_docs.return_value = ["charts/test2/README.md"]

        result = self.tracker.process_all_changes("main", "HEAD~1")

        self.assertTrue(result)
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 2)
        self.assertIn("charts/test1", self.tracker.state["charts_to_bump"])
        self.assertIn("charts/test2", self.tracker.state["charts_to_bump"])

        # Verify methods were called
        mock_ct.assert_called_once_with("main", "HEAD~1")
        mock_helm_docs.assert_called_once_with("charts")

    @patch.object(ChartTracker, 'get_changed_charts_from_git')
    @patch.object(ChartTracker, 'run_helm_docs')
    def test_process_all_changes_without_changes(self, mock_helm_docs, mock_ct):
        """Test process_all_changes when no changes are detected"""
        # Mock no changes
        mock_ct.return_value = []
        mock_helm_docs.return_value = []

        result = self.tracker.process_all_changes("main", "HEAD~1")

        self.assertFalse(result)
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 0)

    @patch.object(ChartTracker, 'get_changed_charts_from_git')
    @patch.object(ChartTracker, 'run_helm_docs')
    def test_process_all_changes_deduplication(self, mock_helm_docs, mock_ct):
        """Test process_all_changes deduplicates charts"""
        # Mock same chart from both sources
        mock_ct.return_value = ["charts/test1"]
        mock_helm_docs.return_value = ["charts/test1/README.md"]

        result = self.tracker.process_all_changes("main", "HEAD~1")

        self.assertTrue(result)
        # Should only have one instance of charts/test1
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 1)
        self.assertEqual(self.tracker.state["charts_to_bump"], ["charts/test1"])

    @patch('subprocess.run')
    def test_check_version_bumps_in_commits_with_version_change(self, mock_run):
        """Test check_version_bumps_in_commits detects version changes"""
        # Mock git diff showing version change
        mock_run.return_value.stdout = """
diff --git a/charts/test1/Chart.yaml b/charts/test1/Chart.yaml
index 1234567..abcdefg 100644
--- a/charts/test1/Chart.yaml
+++ b/charts/test1/Chart.yaml
@@ -5,7 +5,7 @@ description: Test chart
 name: test1
 type: application
-version: 1.2.3
+version: 1.2.4
"""

        # Create a temporary chart directory and Chart.yaml for the test
        test_chart_dir = Path(self.test_dir.name) / "charts" / "test1"
        test_chart_dir.mkdir(parents=True)
        test_chart_yaml = test_chart_dir / "Chart.yaml"
        test_chart_yaml.write_text("version: 1.2.3")

        charts = [str(test_chart_dir)]
        result = self.tracker.check_version_bumps_in_commits(charts, "main", "HEAD~1")

        self.assertEqual(result, [str(test_chart_dir)])
        mock_run.assert_called_with(
            ["git", "diff", "main...HEAD", "--", str(test_chart_yaml)],
            capture_output=True,
            text=True,
            check=True
        )

    @patch('subprocess.run')
    def test_check_version_bumps_in_commits_without_version_change(self, mock_run):
        """Test check_version_bumps_in_commits when no version change"""
        # Mock git diff showing other changes but no version change
        mock_run.return_value.stdout = """
diff --git a/charts/test1/Chart.yaml b/charts/test1/Chart.yaml
index 1234567..abcdefg 100644
--- a/charts/test1/Chart.yaml
+++ b/charts/test1/Chart.yaml
@@ -2,7 +2,7 @@ apiVersion: v2
 appVersion: "1.0.0"
-description: Old description
+description: New description
 name: test1
 type: application
 version: 1.2.3
"""

        charts = ["charts/test1"]
        result = self.tracker.check_version_bumps_in_commits(charts, "main", "HEAD~1")

        self.assertEqual(result, [])

    @patch('subprocess.run')
    def test_check_version_bumps_in_commits_no_changes(self, mock_run):
        """Test check_version_bumps_in_commits when no changes to Chart.yaml"""
        # Mock git diff with no output
        mock_run.return_value.stdout = ""

        charts = ["charts/test1"]
        result = self.tracker.check_version_bumps_in_commits(charts, "main", "HEAD~1")

        self.assertEqual(result, [])

    @patch('subprocess.run')
    def test_check_version_bumps_in_commits_git_error(self, mock_run):
        """Test check_version_bumps_in_commits handles git errors"""
        # Mock git command failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        charts = ["charts/test1"]
        result = self.tracker.check_version_bumps_in_commits(charts, "main", "HEAD~1")

        self.assertEqual(result, [])

    @patch.object(ChartTracker, 'get_changed_charts_from_git')
    @patch.object(ChartTracker, 'run_helm_docs')
    @patch.object(ChartTracker, 'check_version_bumps_in_commits')
    def test_process_all_changes_with_existing_version_bumps(self, mock_check_bumps, mock_helm_docs, mock_ct):
        """Test process_all_changes skips charts with existing version bumps"""
        # Mock chart changes
        mock_ct.return_value = ["charts/test1", "charts/test2"]
        mock_helm_docs.return_value = []

        # Mock that test1 already has version bump, test2 doesn't
        mock_check_bumps.return_value = ["charts/test1"]

        result = self.tracker.process_all_changes("main", "HEAD~1")

        self.assertTrue(result)
        # Should only add test2 (test1 already has version bump)
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 1)
        self.assertEqual(self.tracker.state["charts_to_bump"], ["charts/test2"])

        # Verify check_version_bumps_in_commits was called
        mock_check_bumps.assert_called_once_with(["charts/test1", "charts/test2"], "main", "HEAD~1")

    @patch.object(ChartTracker, 'get_changed_charts_from_git')
    @patch.object(ChartTracker, 'run_helm_docs')
    @patch.object(ChartTracker, 'check_version_bumps_in_commits')
    def test_process_all_changes_all_charts_have_existing_bumps(self, mock_check_bumps, mock_helm_docs, mock_ct):
        """Test process_all_changes when all charts already have version bumps"""
        # Mock chart changes
        mock_ct.return_value = ["charts/test1", "charts/test2"]
        mock_helm_docs.return_value = []

        # Mock that all charts already have version bumps
        mock_check_bumps.return_value = ["charts/test1", "charts/test2"]

        result = self.tracker.process_all_changes("main", "HEAD~1")

        self.assertFalse(result)  # No charts need bumping
        # Should not add any charts from ct list-changed
        self.assertEqual(len(self.tracker.state["charts_to_bump"]), 0)


class TestChartTrackerIntegration(unittest.TestCase):
    """Integration tests for ChartTracker"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.test_dir.name) / "test-tracker.json"

    def tearDown(self):
        """Clean up test fixtures"""
        self.test_dir.cleanup()

    def test_full_workflow_simulation(self):
        """Test a complete workflow simulation"""
        tracker = ChartTracker(str(self.state_file))

        # Simulate adding charts manually (like the process command would)
        tracker.add_chart("charts/test1")
        tracker.add_chart("charts/test2")
        tracker.save()

        # Verify state was saved
        self.assertTrue(self.state_file.exists())

        # Create new tracker and verify state was loaded
        new_tracker = ChartTracker(str(self.state_file))
        self.assertEqual(len(new_tracker.state["charts_to_bump"]), 2)

        # Cleanup
        new_tracker.cleanup()
        self.assertFalse(self.state_file.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)

