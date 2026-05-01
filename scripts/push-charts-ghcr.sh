#!/usr/bin/env bash
# Package every top-level chart under charts/<name>/ and push .tgz artifacts to GHCR (OCI).
# Skips vendored dependency charts under charts/<name>/charts/<dep>/.
#
# Environment:
#   GITHUB_TOKEN     — required; used for helm registry login
#   GITHUB_ACTOR     — username for ghcr.io login (set automatically in GitHub Actions)
#   CHARTS_ROOT      — default: charts
#   REGISTRY_HOST    — default: ghcr.io
#   OCI_REPOSITORY — default: oci://ghcr.io/project-zot/helm-charts
#
# Optional GPG signing (Helm provenance .prov — uploaded with helm push when present):
#   HELM_SIGN_KEY          — secret key name / UID (matches chart-releaser CR_KEY / gpg uid)
#   HELM_KEYRING           — default: keyring.gpg — must contain *private* keys.
#                            Binary OpenPGP (same as: gpg --export-secret-keys without -a).
#                            ASCII-armored (.asc / many .pgp exports): script runs gpg --dearmor automatically.
#   HELM_PASSPHRASE_FILE   — default: passphrase-file.txt (passphrase for that private key)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

CHARTS_ROOT="${CHARTS_ROOT:-charts}"
REGISTRY_HOST="${REGISTRY_HOST:-ghcr.io}"
OCI_REPOSITORY="${OCI_REPOSITORY:-oci://ghcr.io/project-zot/helm-charts}"
HELM_KEYRING="${HELM_KEYRING:-keyring.gpg}"
HELM_PASSPHRASE_FILE="${HELM_PASSPHRASE_FILE:-passphrase-file.txt}"

_helm_ring_bin=""
cleanup_push_charts() {
  rm -rf "${WORKDIR:-}"
  [[ -n "${_helm_ring_bin:-}" && -f "${_helm_ring_bin}" ]] && rm -f "${_helm_ring_bin}"
}

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is required" >&2
  exit 1
fi

if [[ -z "${GITHUB_ACTOR:-}" ]]; then
  echo "GITHUB_ACTOR is required (use your ghcr.io username locally)" >&2
  exit 1
fi

echo "$GITHUB_TOKEN" | helm registry login "$REGISTRY_HOST" --username "$GITHUB_ACTOR" --password-stdin

WORKDIR="$(mktemp -d)"
trap cleanup_push_charts EXIT
mkdir -p "$WORKDIR/packaged"

mapfile -t chart_yamls < <(
  find "$CHARTS_ROOT" -maxdepth 3 -path "${CHARTS_ROOT}/*/charts/*" -prune -o -path "${CHARTS_ROOT}/*/Chart.yaml" -print | sort
)

if [[ ${#chart_yamls[@]} -eq 0 ]]; then
  echo "No Chart.yaml files found under ${CHARTS_ROOT}/" >&2
  exit 1
fi

sign_opts=()
if [[ -n "${HELM_SIGN_KEY:-}" && -f "$HELM_KEYRING" && -f "$HELM_PASSPHRASE_FILE" ]]; then
  keyring_for_helm="$HELM_KEYRING"
  # Helm uses Go openpgp and expects binary packets; ASCII armor yields: openpgp: invalid data: tag byte does not have MSB set
  if grep -q '^-----BEGIN PGP' "$HELM_KEYRING" 2>/dev/null; then
    _helm_ring_bin="$(mktemp)"
    gpg --batch --yes --dearmor --output "$_helm_ring_bin" "$HELM_KEYRING"
    keyring_for_helm="$_helm_ring_bin"
    echo "HELM_KEYRING is ASCII-armored; using dearmored copy for Helm"
  fi

  echo "GPG signing enabled for packaged charts (key=$HELM_SIGN_KEY)"
  sign_opts=(--sign --key "$HELM_SIGN_KEY" --keyring "$keyring_for_helm" --passphrase-file "$HELM_PASSPHRASE_FILE")
else
  echo "GPG signing skipped (set HELM_SIGN_KEY and ensure $HELM_KEYRING and $HELM_PASSPHRASE_FILE exist)"
fi

for chart_yaml in "${chart_yamls[@]}"; do
  chart_dir="$(dirname "$chart_yaml")"
  echo "Packaging: $chart_dir"
  helm package "$chart_dir" --destination "$WORKDIR/packaged" "${sign_opts[@]}"
done

shopt -s nullglob
pkgs=("$WORKDIR"/packaged/*.tgz)
shopt -u nullglob

if [[ ${#pkgs[@]} -eq 0 ]]; then
  echo "No chart packages produced" >&2
  ls -la "$WORKDIR/packaged" >&2 || true
  exit 1
fi

mapfile -t pkgs_sorted < <(printf '%s\n' "${pkgs[@]}" | sort)

for pkg in "${pkgs_sorted[@]}"; do
  echo "Pushing: $pkg"
  helm push "$pkg" "$OCI_REPOSITORY"
done
