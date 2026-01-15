# Encryption Guide

## Quick Start: GitHub Username Shortcuts

Instead of providing full URLs, you can use GitHub username shortcuts:

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:USERNAME        # Auto-resolves to standard locations
    # or
    public_key: gh:USERNAME            # Shorter alias
    private_key: ~/.config/bbackup/backup_private.pem
```

bbackup will automatically try to find your key in:
1. Gist named `bbackup-keys` or `backup-keys`
2. Repository named `bbackup-keys` or `backup-keys`
3. Explicit formats: `github:USERNAME/gist:GIST_ID` or `github:USERNAME/repo:REPO_NAME`

**Examples:**
```yaml
# Simple username (tries standard locations)
public_key: github:myusername

# Explicit gist
public_key: github:myusername/gist:abc123def456

# Explicit repository
public_key: github:myusername/repo:backup-keys
```

---

# Encryption Guide - bbackup

## Overview

bbackup supports encryption of backups at rest using industry-standard encryption algorithms. This guide covers setup, key management, and deployment strategies.

## Encryption Methods

### Symmetric Encryption (AES-256-GCM)

**Best for:** Single-server deployments or trusted environments

- Single key for both encryption and decryption
- Faster performance
- Simpler key management
- Key can be stored as file or fetched from URL

**Use case:** All servers need the same key to encrypt/decrypt backups.

### Asymmetric Encryption (RSA-4096 / ECDSA P-384)

**Best for:** Multi-server deployments, production environments

- Public key for encryption (can be shared)
- Private key for decryption (must be kept secret)
- More secure, supports multiple recipients
- Public key can be URL, private key must be local file

**Use case:** Backup servers encrypt with public key, restore servers decrypt with private key.

## Quick Start

### 1. Generate Keys

```bash
# Symmetric key
bbackup init-encryption --method symmetric

# Asymmetric keys
bbackup init-encryption --method asymmetric --algorithm rsa-4096
```

This creates:
- **Symmetric**: `~/.config/bbackup/encryption.key`
- **Asymmetric**: 
  - `~/.config/bbackup/backup_public.pem` (can be shared)
  - `~/.config/bbackup/backup_private.pem` (keep secret!)

### 2. Configure Encryption

Edit `~/.config/bbackup/config.yaml`:

```yaml
encryption:
  enabled: true
  method: symmetric  # or asymmetric
  symmetric:
    key_file: ~/.config/bbackup/encryption.key
    # OR use URL:
    # key_url: https://raw.githubusercontent.com/user/repo/encryption.key
  asymmetric:
    public_key: ~/.config/bbackup/backup_public.pem
    private_key: ~/.config/bbackup/backup_private.pem
    algorithm: rsa-4096
```

### 3. Run Backup

Backups are automatically encrypted:

```bash
bbackup backup --containers test_web
# Backup is encrypted before upload
```

## URL-Based Key Deployment

### Why URL-Based Keys?

Traditional key deployment requires:
1. Generate keys on master server
2. Copy keys to all servers via SSH/SCP
3. Set permissions on each server
4. Update configs on each server

**URL-based deployment simplifies this:**
1. Upload public key to GitHub (gist or repo)
2. Configure URL in all server configs
3. System automatically downloads and validates key

### Setup URL-Based Public Keys

#### Step 1: Generate Keys

```bash
bbackup init-encryption --method asymmetric
```

#### Step 2: Upload Public Key to GitHub

**Option A: GitHub Gist**
1. Go to https://gist.github.com
2. Create new gist
3. Paste contents of `backup_public.pem`
4. Click "Create public gist"
5. Click "Raw" to get URL:
   ```
   https://gist.githubusercontent.com/username/gist_id/raw/backup_public.pem
   ```

**Option B: GitHub Repository**
1. Create repository (public or private)
2. Upload `backup_public.pem` to repository
3. Get raw URL:
   ```
   https://raw.githubusercontent.com/username/repo/main/backup_public.pem
   ```

#### Step 3: Configure Servers

On all backup servers, configure:

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://raw.githubusercontent.com/user/repo/backup_public.pem
    # Private key only on restore servers
    private_key: ~/.config/bbackup/backup_private.pem
```

#### Step 4: System Behavior

- First use: Downloads public key from URL
- Validates key format and HTTPS
- Caches key locally (`~/.cache/bbackup/keys/`)
- Uses cached key if URL unavailable (offline mode)

### URL Examples

**GitHub Raw File:**
```
https://raw.githubusercontent.com/myorg/backup-keys/main/public.pem
```

**GitHub Gist:**
```
https://gist.githubusercontent.com/user/abc123def456/raw/backup_public.pem
```

**Private Repository (requires auth):**
- Use GitHub token in URL (not recommended for public keys)
- Or use local file path instead

## Multi-Server Deployment

### Scenario 1: All Servers Backup and Restore

**Setup:**
1. Generate symmetric key on master server
2. Upload key to GitHub (private repo recommended)
3. Configure all servers with key URL

```yaml
encryption:
  enabled: true
  method: symmetric
  symmetric:
    key_url: https://raw.githubusercontent.com/myorg/keys/main/encryption.key
```

**Pros:**
- Simple setup
- All servers can encrypt/decrypt
- Easy key rotation (update URL)

**Cons:**
- Single key compromise affects all servers
- Key must be kept secure

### Scenario 2: Backup Servers vs Restore Servers

**Setup:**
1. Generate asymmetric keypair
2. Upload public key to GitHub
3. Distribute public key URL to backup servers
4. Keep private key secure on restore servers only

**Backup Servers:**
```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://raw.githubusercontent.com/myorg/keys/main/backup_public.pem
    # No private key needed for backup servers
```

**Restore Servers:**
```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://raw.githubusercontent.com/myorg/keys/main/backup_public.pem
    private_key: ~/.config/bbackup/backup_private.pem  # Local file only
```

**Pros:**
- More secure (private key only on restore servers)
- Public key can be shared freely
- Supports multiple backup servers

**Cons:**
- More complex setup
- Need to manage private key distribution securely

## Key Management

### Key Rotation

**Symmetric Keys:**
1. Generate new key: `bbackup init-encryption --method symmetric`
2. Update key URL in config
3. New backups use new key
4. Old backups still decrypt with old key (if kept)

**Asymmetric Keys:**
1. Generate new keypair: `bbackup init-encryption --method asymmetric`
2. Upload new public key to GitHub
3. Update public key URL in config
4. Distribute new private key to restore servers
5. Old backups still decrypt with old private key (if kept)

### Key Storage

**File Permissions:**
- Private keys: `600` (owner read/write only)
- Public keys: `644` (readable by all)
- Symmetric keys: `600` (owner read/write only)

**Key Locations:**
- Default: `~/.config/bbackup/`
- Cache: `~/.cache/bbackup/keys/` (for URL-fetched keys)

### Password Protection

Protect key files with passwords:

```yaml
encryption:
  symmetric:
    key_file: ~/.config/bbackup/encryption.key
    key_password: "your-secure-password"
  asymmetric:
    private_key: ~/.config/bbackup/backup_private.pem
    private_key_password: "your-secure-password"
```

## Security Best Practices

1. **Never upload private keys**
   - Private keys should only exist as local files
   - Never commit private keys to repositories
   - Never share private keys via URL

2. **Use HTTPS for public keys**
   - System requires HTTPS URLs (blocks HTTP)
   - Ensures key integrity during transfer

3. **Validate key sources**
   - Verify GitHub URLs before using
   - Use private repositories for sensitive keys
   - Consider key signing for additional verification

4. **Secure key storage**
   - Set proper file permissions (600 for private keys)
   - Use password protection for key files
   - Store keys in secure locations

5. **Key rotation**
   - Rotate keys periodically
   - Keep old keys for decrypting old backups
   - Document key rotation process

6. **Backup key management**
   - Backup private keys securely (encrypted)
   - Store key backups separately from data backups
   - Document key recovery process

## Troubleshooting

### "Failed to fetch key from URL"

**Causes:**
- Network connectivity issues
- Invalid URL
- URL requires authentication
- HTTPS certificate issues

**Solutions:**
- Check network connectivity
- Verify URL is accessible
- Use local file path instead
- Check cached key: `~/.cache/bbackup/keys/`

### "No encryption key available"

**Causes:**
- Key file not found
- Key URL invalid
- Key file permissions incorrect

**Solutions:**
- Verify key path in config
- Check file permissions
- Test key loading manually

### "Decryption failed"

**Causes:**
- Wrong key used
- Corrupted encrypted file
- Key format invalid

**Solutions:**
- Verify correct key is configured
- Check encrypted file integrity
- Verify key format (PEM, etc.)

## Examples

### Example 1: Simple Single-Server Setup

```bash
# Generate key
bbackup init-encryption --method symmetric

# Configure (auto-generated in ~/.config/bbackup/config.yaml)
encryption:
  enabled: true
  method: symmetric
  symmetric:
    key_file: ~/.config/bbackup/encryption.key

# Backup (automatically encrypted)
bbackup backup --containers web_app
```

### Example 2: Multi-Server with GitHub

```bash
# On master server: Generate keys
bbackup init-encryption --method asymmetric

# Upload public key to GitHub gist
# Get URL: https://gist.githubusercontent.com/user/abc123/raw/backup_public.pem

# On all backup servers: Configure
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://gist.githubusercontent.com/user/abc123/raw/backup_public.pem

# On restore servers: Add private key
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://gist.githubusercontent.com/user/abc123/raw/backup_public.pem
    private_key: ~/.config/bbackup/backup_private.pem
```

### Example 3: Password-Protected Keys

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://raw.githubusercontent.com/user/repo/public.pem
    private_key: ~/.config/bbackup/backup_private.pem
    private_key_password: "secure-password-here"
```

## Advanced Topics

### Custom Key Algorithms

Supported algorithms:
- **Symmetric**: AES-256-GCM (fixed)
- **Asymmetric**: RSA-4096, ECDSA P-384

To use ECDSA:
```bash
bbackup init-encryption --method asymmetric --algorithm ecdsa-p384
```

### Key Caching

URL-fetched keys are cached locally:
- Location: `~/.cache/bbackup/keys/`
- Format: `key_{url_hash}.cache`
- Permissions: `600`

Cache is used when:
- URL is unavailable (offline mode)
- Network errors occur
- Faster subsequent access

Clear cache:
```bash
rm -rf ~/.cache/bbackup/keys/
```

### Encryption Metadata

Encrypted backups include metadata:
```json
{
  "encrypted": true,
  "method": "symmetric",
  "algorithm": "aes-256-gcm",
  "key_id": "abc123...",
  "timestamp": "2026-01-08T12:00:00Z"
}
```

This helps identify:
- Encryption method used
- Key required for decryption
- When backup was encrypted

## Support

For issues or questions:
- Check logs: `~/.local/share/bbackup/bbackup.log`
- Verify key configuration
- Test key loading manually
- Review security best practices
