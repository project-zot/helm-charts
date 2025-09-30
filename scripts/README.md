# Scripts

This directory contains utility scripts for the Helm charts repository.

## bump_chart_version.py

Python script that automatically bumps the patch version of a Helm chart by directly manipulating the Chart.yaml file.

## chart_tracker.py

Python script that manages chart version bumping with JSON state tracking for deduplication.

### Usage

```bash
./scripts/bump_chart_version.py <chart_path>
```

### Examples

```bash
# Bump zot chart version
./scripts/bump_chart_version.py charts/zot

# Bump any other chart
./scripts/bump_chart_version.py charts/my-chart
```

### What it does

1. Reads and parses the `Chart.yaml` file using PyYAML
2. Extracts the current version from the parsed YAML data
3. Increments the patch version (e.g., `0.1.82` → `0.1.83`)
4. Updates the YAML data structure and writes it back
5. Preserves YAML formatting and structure

### Requirements

- Chart must have a valid `Chart.yaml` file
- Version must be in `major.minor.patch` format
- Python 3.9+ with PyYAML required

### Error Handling

- Validates chart path is provided
- Checks that `Chart.yaml` exists
- Handles YAML parsing errors
- Validates version format
- Handles file I/O errors gracefully
- Exits with appropriate error codes

### Testing

The scripts include comprehensive unit tests:

```bash
# Run all tests (quiet mode - only shows failures)
python3 scripts/run_tests.py

# Run all tests with detailed output
python3 scripts/run_tests.py --verbose

# Or run individual test suites
python3 scripts/test_bump_chart_version.py
python3 scripts/test_chart_tracker.py
python3 scripts/test_chart_tracker_integration.py
```

**Note**: The error messages you see in verbose mode (like "Warning: Could not load state file") are **expected** - they're testing error handling scenarios where invalid JSON is encountered.

The tests cover:
- **bump_chart_version.py**: Successful version bumps, error handling, YAML parsing edge cases, complex chart structures
- **chart_tracker.py**: State management, chart detection, version bumping integration, error handling, subprocess mocking, version bump detection in commits

## GitHub Actions Integration

The script is automatically used by the CI/CD workflow to:

1. **Detect changed charts** using git operations
2. **Check if documentation is out of date** by generating helm-docs
3. **Bump versions** for all changed charts
4. **Generate documentation** using `helm-docs` GitHub Action
5. **Commit changes** with appropriate commit messages

### Workflow Steps

1. When any push happens to `main` branch
2. Python script processes all changes using `chart_tracker.py process`
3. Script uses git operations to detect chart changes
4. Script runs `helm-docs` and checks for documentation changes
5. Script deduplicates and tracks unique charts that need version bumps
6. Script calls `bump_patch_version()` function directly for each chart (handled internally)
7. Generates helm-docs for all charts
8. Commits changes with message: `chore: auto-bump chart versions and update docs [skip pr]`

### Smart Detection

The workflow now handles these scenarios:
- **Chart changes only**: Bumps versions for changed charts and updates docs
- **Docs out of date only**: Bumps versions for charts with changed docs and updates docs
- **Both**: Bumps versions for changed charts and updates docs (deduplicated)
- **Neither**: No action taken
- **Existing version bumps**: Skips charts that already have version bumps in the commits

### Version Bump Detection

The script intelligently detects if chart versions have already been bumped in the commits:
- Uses `git diff` to check for version field changes in `Chart.yaml` files
- Skips charts that already have version bumps to avoid double-bumping
- Only processes charts that actually need version increments

### Deduplication Logic

The workflow prevents double version bumps using `chart-tracker.py`:
1. **JSON State Management**: Uses `.chart-tracker.json` to track unique chart paths
2. **Python Logic**: Handles deduplication with proper data structures
3. **Command Interface**: Simple commands for adding charts and managing state
4. **Automatic Cleanup**: Removes state file after processing

### Chart Tracker Commands

```bash
# Process all changes and bump versions
python3 ./scripts/chart_tracker.py process --target-branch main --since HEAD~1

# Clean up state file
python3 ./scripts/chart_tracker.py cleanup
```

### Why Version Bump for Docs?

When documentation is out of date, it means the chart metadata (version, appVersion, etc.) has changed, which requires a new chart version to be published. The workflow identifies which specific charts have stale documentation and bumps only those versions.

### Dependencies

- **helm-docs**: Installed via GitHub Action `losisin/helm-docs-github-action@v1.6.2`
- **Git**: Used to detect changed charts and for committing changes

