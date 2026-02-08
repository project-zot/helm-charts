# Helm Chart Provenance Verification

All charts in this repository are cryptographically signed to ensure authenticity and integrity. This document explains how to verify chart signatures.

## What is Chart Provenance?

Chart provenance files (`.prov`) contain cryptographic signatures that allow you to verify:
- **Origin**: The chart comes from the project-zot organization
- **Integrity**: The chart hasn't been tampered with

## Complete Example

Here's a complete workflow for downloading and verifying a chart:

```bash
# 1. Import the public key (only needed once)
curl -sL https://raw.githubusercontent.com/project-zot/helm-charts/main/signing-key.pub | gpg --import

# 2. Create legacy keyring format (required by Helm)
# Helm requires the legacy GPG keyring format, not the modern format
mkdir -p ~/.gnupg
gpg --export >> ~/.gnupg/pubring.gpg

# 3. Add the repository
helm repo add zot https://zotregistry.dev/helm-charts
helm repo update

# 4. Pull chart with provenance (downloads both .tgz and .tgz.prov files)
helm pull --prov zot/zot

# 5. Verify the signature
helm verify zot-*.tgz
# If verification succeeds, you'll see:
# Signed by: <signer information>
# Chart Hash: <hash>

# 6. Install the verified chart
helm install my-zot zot-*.tgz
```

## Verifying During Installation

You can also verify charts automatically during installation:

```bash
helm install my-zot zot --repo https://zotregistry.dev/helm-charts --verify
```

The `--verify` flag ensures the chart is verified before installation.

## Key Fingerprint

For additional security, you can verify the key fingerprint before importing:

```bash
# Download the key
curl -sL https://raw.githubusercontent.com/project-zot/helm-charts/main/signing-key.pub -o signing-key.pub

# Check the fingerprint (without importing)
gpg --show-keys --with-fingerprint signing-key.pub

# If the fingerprint matches, import the key
gpg --import signing-key.pub
```

> ⚠️ **Warning**: Always verify the fingerprint matches `6559 87EE 2D5C 291F CDFA  6592 606D B108 4F6D 3EF0` before trusting the key.

## Troubleshooting

### "WARNING: Verification not found"

This means the `.prov` file is missing. This can happen if:
- The chart version was released before provenance signing was enabled
- The download was interrupted
- The repository doesn't have provenance files for that version

Try pulling a newer chart version or ensure you're using the `--prov` flag.

### "Error: failed to load keyring"

This error means Helm can't find the keyring in the legacy format. After importing the key, create the legacy keyring:

```bash
# Import the key
curl -sL https://raw.githubusercontent.com/project-zot/helm-charts/main/signing-key.pub | gpg --import

# Create legacy keyring format (required by Helm)
mkdir -p ~/.gnupg
gpg --export >> ~/.gnupg/pubring.gpg
```

### "Error: signature is invalid"

This indicates the chart may have been tampered with or corrupted. Do not install the chart. Please report this issue to the project-zot team.

### "gpg: no valid OpenPGP data found"

The public key file may be corrupted or incorrectly downloaded. Try downloading again:
```bash
curl -sL https://raw.githubusercontent.com/project-zot/helm-charts/main/signing-key.pub | gpg --import
```

## Security Best Practices

1. **Always verify signatures** before installing charts in production
2. **Import the public key** from the official repository URL
3. **Verify the key fingerprint** matches the expected value
4. **Use `--verify` flag** during installation for automatic verification
5. **Keep your GPG keyring updated** if keys are rotated

## Additional Resources

- [Helm Provenance and Integrity Documentation](https://helm.sh/docs/topics/provenance/)
- [Helm Verify Command](https://helm.sh/docs/helm/helm_verify/)
- [GPG Manual](https://www.gnupg.org/documentation/)