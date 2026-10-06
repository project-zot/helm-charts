# Scripts

This directory contains utility scripts for the Helm charts repository.

## bump_chart_version.py

Python script that automatically bumps the patch version of a Helm chart by directly manipulating the Chart.yaml file.

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

## chart_tracker.py

Python script that manages chart version bumping with JSON state tracking for deduplication. Used by the release job in `.github/workflows/ci-cd.yml`.

### Commands

```bash
# Detect chart/doc changes; queue and attempt bumps (exit 1), or do nothing (exit 0)
python3 ./scripts/chart_tracker.py process --since HEAD~1

# Remove the temporary .chart-tracker.json state file
python3 ./scripts/chart_tracker.py cleanup
```

Exit codes: `process` returns `0` if nothing was queued, `1` if charts were queued and bump was attempted (per-chart failures are logged but do not change the exit code), `2` on error. `cleanup` returns `0` on success, `2` on error.

### What it does

1. Finds charts changed since the given commit (`git diff`)
2. Skips charts whose `Chart.yaml` `version` was already bumped in that range
3. Runs `helm-docs` and may queue additional charts from stale READMEs (unless already bumped)
4. Bumps patch versions for queued charts via `bump_patch_version()`
5. Writes `.chart-tracker.json`; call `cleanup` afterward to remove it

## Testing

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

Note: The error messages you see in verbose mode (like "Warning: Could not load state file") are expected — they exercise error handling for invalid JSON.

The tests cover:
- bump_chart_version.py: Successful version bumps, error handling, YAML parsing edge cases, complex chart structures
- chart_tracker.py: State management, chart detection, version bumping integration, error handling, subprocess mocking, version bump detection in commits

## GitHub Actions Integration

The release job on `main` (see `.github/workflows/ci-cd.yml`) uses these scripts to:

1. Detect changed charts using git operations (`chart_tracker.py process`)
2. Check whether documentation is out of date by generating helm-docs
3. Bump versions for charts that need it (skipping charts already bumped in the push, e.g. from the zot publish pipeline)
4. Run `helm-docs` again in the workflow and commit any dirty `Chart.yaml` / README files
5. Choose the commit message from whether `Chart.yaml` changed (version bump) or only README (docs refresh); both messages include a token so the follow-up push runs CI but skips chart-releaser

### Smart Detection

The workflow handles these scenarios:
- Chart changes only: Bumps versions for changed charts and updates docs
- Docs out of date only: Bumps versions for charts with changed docs and updates docs
- Both: Bumps versions for changed charts and updates docs (deduplicated)
- Neither: No action taken
- Existing version bumps (for example the zot publish pipeline already bumped `Chart.yaml`): skips a second version bump, regenerates helm-docs, and commits README-only updates so docs stay aligned with `appVersion` / `image.tag`

### Version Bump Detection

The script detects if chart versions have already been bumped in the commits:
- Uses `git diff` to check for `version:` field changes in `Chart.yaml` files
- Skips those charts to avoid double-bumping
- Only processes charts that actually need version increments
- The CI release job still refreshes and commits chart READMEs when the version was pre-bumped

### Deduplication Logic

The workflow prevents double version bumps using `chart-tracker.py`:
1. JSON state management via `.chart-tracker.json` for unique chart paths
2. Python logic for deduplication
3. `process` / `cleanup` commands for adding charts and clearing state

### Why Version Bump for Docs?

When documentation is out of date because chart metadata changed without a version bump in the same push, the tracker bumps the chart so a new release can publish. If the version was already bumped in that push, the workflow commits README updates only and does not bump again.

### Dependencies

- helm-docs: Installed via GitHub Action `losisin/helm-docs-github-action@v1.6.2` (also invoked as `helm-docs` in the release job)
- Git: Used to detect changed charts and for committing changes
- PyYAML: Required by the Python scripts
