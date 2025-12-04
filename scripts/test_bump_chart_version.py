#!/usr/bin/env python3
"""
Unit tests for bump_chart_version.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the module directly
from bump_chart_version import bump_patch_version


class TestBumpChartVersion(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.chart_path = Path(self.test_dir.name) / "test-chart"
        self.chart_path.mkdir()
        self.chart_yaml = self.chart_path / "Chart.yaml"

    def tearDown(self):
        """Clean up test fixtures"""
        self.test_dir.cleanup()

    def create_test_chart_yaml(self, content):
        """Helper method to create a test Chart.yaml file"""
        with open(self.chart_yaml, 'w') as f:
            f.write(content)

    def test_successful_version_bump(self):
        """Test successful version bump from 1.2.3 to 1.2.4"""
        self.create_test_chart_yaml("version: 1.2.3")
        result = bump_patch_version(str(self.chart_path))
        self.assertTrue(result)

        with open(self.chart_yaml, 'r') as f:
            updated_content = f.read()
        self.assertIn("version: 1.2.4", updated_content)
        self.assertNotIn("version: 1.2.3", updated_content)

    def test_version_bump_with_comments(self):
        """Test version bump (comments are not preserved by YAML parser)"""
        test_content = """# This is a test chart
apiVersion: v2
appVersion: "1.0.0"
description: Test chart
name: test-chart
type: application
version: 0.1.5  # Current version
"""
        self.create_test_chart_yaml(test_content)

        result = bump_patch_version(str(self.chart_path))

        self.assertTrue(result)

        with open(self.chart_yaml, 'r') as f:
            updated_content = f.read()

        self.assertIn("version: 0.1.6", updated_content)
        # Note: Comments are not preserved by YAML parser, which is expected behavior

    def test_version_with_quotes(self):
        """Test version bump with quoted version"""
        self.create_test_chart_yaml('version: "2.1.0"')
        result = bump_patch_version(str(self.chart_path))
        self.assertTrue(result)

        with open(self.chart_yaml, 'r') as f:
            updated_content = f.read()
        self.assertIn("version: 2.1.1", updated_content)

    def test_zero_version_bump(self):
        """Test version bump from 0.0.0 to 0.0.1"""
        self.create_test_chart_yaml("version: 0.0.0")
        result = bump_patch_version(str(self.chart_path))
        self.assertTrue(result)

        with open(self.chart_yaml, 'r') as f:
            updated_content = f.read()
        self.assertIn("version: 0.0.1", updated_content)

    def test_large_version_numbers(self):
        """Test version bump with large version numbers"""
        self.create_test_chart_yaml("version: 999.888.777")
        result = bump_patch_version(str(self.chart_path))
        self.assertTrue(result)

        with open(self.chart_yaml, 'r') as f:
            updated_content = f.read()
        self.assertIn("version: 999.888.778", updated_content)

    def test_complex_yaml_structure(self):
        """Test version bump with complex YAML structure"""
        complex_content = """apiVersion: v2
appVersion: "1.0.0"
description: A complex test chart
name: complex-chart
type: application
version: 3.2.1
dependencies:
  - name: postgresql
    version: "11.6.12"
    repository: "https://charts.bitnami.com/bitnami"
keywords:
  - database
  - postgresql
maintainers:
  - name: Test Maintainer
    email: test@example.com
"""
        self.create_test_chart_yaml(complex_content)
        result = bump_patch_version(str(self.chart_path))
        self.assertTrue(result)

        with open(self.chart_yaml, 'r') as f:
            updated_content = f.read()
        self.assertIn("version: 3.2.2", updated_content)

    def test_chart_yaml_not_found(self):
        """Test error when Chart.yaml doesn't exist"""
        result = bump_patch_version(str(self.chart_path))
        self.assertFalse(result)

    def test_missing_version_field(self):
        """Test error when version field is missing"""
        self.create_test_chart_yaml("name: test-chart\ntype: application")
        result = bump_patch_version(str(self.chart_path))
        self.assertFalse(result)

    def test_invalid_version_format(self):
        """Test error with invalid version format"""
        self.create_test_chart_yaml("version: 1.2")  # Missing patch version
        result = bump_patch_version(str(self.chart_path))
        self.assertFalse(result)

    def test_non_numeric_version_parts(self):
        """Test error with non-numeric version parts"""
        self.create_test_chart_yaml("version: 1.2.a")  # Non-numeric patch
        result = bump_patch_version(str(self.chart_path))
        self.assertFalse(result)

    def test_invalid_yaml(self):
        """Test error with invalid YAML"""
        invalid_yaml = """version: 1.2.3
invalid: [unclosed list
"""
        self.create_test_chart_yaml(invalid_yaml)
        result = bump_patch_version(str(self.chart_path))
        self.assertFalse(result)


class TestBumpChartVersionIntegration(unittest.TestCase):
    """Integration tests for the script execution"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.chart_path = Path(self.test_dir.name) / "test-chart"
        self.chart_path.mkdir()
        self.chart_yaml = self.chart_path / "Chart.yaml"

    def tearDown(self):
        """Clean up test fixtures"""
        self.test_dir.cleanup()

    def test_script_execution_success(self):
        """Test successful script execution"""
        test_content = """apiVersion: v2
appVersion: 1.0.0
description: Test chart
name: test-chart
type: application
version: 1.0.0
"""
        with open(self.chart_yaml, 'w') as f:
            f.write(test_content)

        # Import and test the main function
        from bump_chart_version import main

        # Mock sys.argv to simulate command line arguments
        with patch('sys.argv', ['bump-chart-version.py', str(self.chart_path)]):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_with(0)

        with open(self.chart_yaml, 'r') as f:
            updated_content = f.read()

        self.assertIn("version: 1.0.1", updated_content)

    def test_script_execution_failure(self):
        """Test script execution with invalid chart path"""
        from bump_chart_version import main

        # Mock sys.argv with non-existent path
        with patch('sys.argv', ['bump-chart-version.py', '/non/existent/path']):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_with(1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
