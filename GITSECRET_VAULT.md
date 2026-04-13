# Git-Secret Vault

This repository uses [`git-secret`](https://git-secret.io/) to encrypt sensitive files.

## Encrypted Files

The following secrets are stored in the vault:

| Original File | Encrypted File |
|---------------|----------------|
| `.env` | `.env.secret` |
| `backend/.env` | `backend/.env.secret` |
| `.ssh-keys/github_ed25519` | `.ssh-keys/github_ed25519.secret` |
| `.ssh-keys/render_ed25519` | `.ssh-keys/render_ed25519.secret` |
| `gcp-sa-key.json` | `gcp-sa-key.json.secret` |

## GPG Key

- **User:** `Cerebrum GitSecret Vault <gitsecret@cerebrum.local>`
- **Fingerprint:** `0BB0 7F94 38B8 2DA0 15CE  FB2B 6F66 8120 1711 75C0`
- **Export Location (local only):** `.gitsecret/gitsecret-private-key.asc`

> ⚠️ **Keep the private key safe.** If you lose it, you cannot decrypt the secrets.

## Quick Reference

### Reveal (decrypt) all secrets
```bash
git secret reveal
```

### Hide (encrypt) all secrets after editing
```bash
git secret hide
```

### Check who can decrypt
```bash
git secret whoknows
```

### Add a new GPG user
```bash
git secret tell <email>
git secret hide
```

## Setup on a New Machine

1. Install `git-secret`:
   ```bash
   # macOS
   brew install git-secret

   # Ubuntu/Debian (see git-secret docs for latest install method)
   ```

2. Import the private GPG key:
   ```bash
   gpg --import .gitsecret/gitsecret-private-key.asc
   ```

3. Reveal secrets:
   ```bash
   git secret reveal
   ```

## What Changed

- `.gitignore` updated to ignore raw secrets and allow `*.secret` files
- `.gitsecret/` directory initialized with user mapping and pubring
- Encrypted `.secret` files committed to the repo
