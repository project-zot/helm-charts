# Helm Charts
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fproject-zot%2Fhelm-charts.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fproject-zot%2Fhelm-charts?ref=badge_shield)

## Installation

### Using OCI registry (ghcr.io)

Charts are published to the GitHub Container Registry as OCI artifacts. You can install directly without adding a Helm repository:

```bash
# Install the chart
helm install zot oci://ghcr.io/project-zot/helm-charts/zot --version <version>

# Inspect default values before installing
helm show values oci://ghcr.io/project-zot/helm-charts/zot --version <version>

# Upgrade an existing release
helm upgrade zot oci://ghcr.io/project-zot/helm-charts/zot --version <version>
```

Replace `<version>` with the desired chart version (e.g. `0.1.104`). You can find the list of available versions on the [ghcr.io package page](https://github.com/project-zot/helm-charts/pkgs/container/helm-charts%2Fzot).

### Using the Helm repository (Artifact Hub)

```bash
# Add the zot Helm repository
helm repo add project-zot https://zotregistry.dev/helm-charts

# Update repositories
helm repo update

# Install the chart
helm install zot project-zot/zot
```

Find the chart on [Artifact Hub](https://artifacthub.io/packages/helm/project-zot/zot).

## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fproject-zot%2Fhelm-charts.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fproject-zot%2Fhelm-charts?ref=badge_large)