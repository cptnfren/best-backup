# Getting Public Keys from GitHub for bbackup Encryption

This guide shows how to get public keys from GitHub profiles and use them with bbackup encryption.

## 🚀 Quick Start: GitHub Username Shortcuts (NEW!)

**Simplest way - just use your GitHub username:**

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:YOUR_USERNAME    # That's it!
    private_key: ~/.config/bbackup/backup_private.pem
```

bbackup will automatically find your key in standard locations:
1. Gist named `bbackup-keys` or `backup-keys`
2. Repository named `bbackup-keys` or `backup-keys`

**No need for long URLs!**

## Quick Commands

### Get SSH Keys from GitHub User

```bash
# Get SSH public keys (if user has uploaded SSH keys)
curl https://github.com/USERNAME.keys

# Example
curl https://github.com/octocat.keys
```

### Get Keys via GitHub API

```bash
# Get detailed key information
curl https://api.github.com/users/USERNAME/keys | jq .

# Example
curl https://api.github.com/users/octocat/keys | jq .
```

### Using the Helper Script

```bash
# Print keys to stdout
./scripts/get_github_key.sh USERNAME

# Save to file
./scripts/get_github_key.sh USERNAME ~/.config/bbackup/github_key.pem
```

## GitHub Shortcut Formats

### Simple Username (Auto-Discovery)

```yaml
public_key: github:USERNAME
# or
public_key: gh:USERNAME  # Shorter alias
```

bbackup tries these locations automatically:
- `https://gist.githubusercontent.com/USERNAME/bbackup-keys/raw/backup_public.pem`
- `https://gist.githubusercontent.com/USERNAME/backup-keys/raw/backup_public.pem`
- `https://raw.githubusercontent.com/USERNAME/bbackup-keys/main/backup_public.pem`
- `https://raw.githubusercontent.com/USERNAME/backup-keys/main/backup_public.pem`

### Explicit Gist

```yaml
public_key: github:USERNAME/gist:GIST_ID
```

Example:
```yaml
public_key: github:octocat/gist:abc123def456
```

### Explicit Repository

```yaml
public_key: github:USERNAME/repo:REPO_NAME
```

Example:
```yaml
public_key: github:octocat/repo:backup-keys
```

## Methods for bbackup Encryption

### Method 1: GitHub Username Shortcut (Recommended)

**Step 1: Generate encryption keys**
```bash
bbackup init-encryption --method asymmetric
```

**Step 2: Create a GitHub Gist or Repository**
- **Option A - Gist:**
  1. Go to https://gist.github.com
  2. Create new gist named `bbackup-keys` or `backup-keys`
  3. Upload your `backup_public.pem` file
  4. Click "Create public gist"

- **Option B - Repository:**
  1. Create new repo named `bbackup-keys` or `backup-keys`
  2. Upload `backup_public.pem` to the repo
  3. Commit and push

**Step 3: Configure bbackup (Super Simple!)**
```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:YOUR_USERNAME    # Just your username!
    private_key: ~/.config/bbackup/backup_private.pem
    algorithm: rsa-4096
```

That's it! No URLs needed!

### Method 2: Full URL (Traditional)

**Step 1: Generate encryption keys**
```bash
bbackup init-encryption --method asymmetric
```

**Step 2: Create a GitHub Gist**
1. Go to https://gist.github.com
2. Create a new gist
3. Upload your `backup_public.pem` file
4. Click "Create public gist" (or private if preferred)

**Step 3: Get Raw URL**
- Click on the file in the gist
- Click "Raw" button
- Copy the URL (e.g., `https://gist.githubusercontent.com/user/gist_id/raw/backup_public.pem`)

**Step 4: Configure bbackup**
```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://gist.githubusercontent.com/user/gist_id/raw/backup_public.pem
    private_key: ~/.config/bbackup/backup_private.pem
    algorithm: rsa-4096
```

### Method 3: GitHub Repository

**Step 1: Create a repository (public or private)**
```bash
git init backup-keys
cd backup-keys
# Add your public key
cp ~/.config/bbackup/backup_public.pem .
git add backup_public.pem
git commit -m "Add backup public key"
git remote add origin https://github.com/USERNAME/backup-keys.git
git push -u origin main
```

**Step 2: Use GitHub shortcut or full URL**
```yaml
# Option 1: Shortcut (if repo named backup-keys or bbackup-keys)
public_key: github:USERNAME

# Option 2: Explicit repo
public_key: github:USERNAME/repo:backup-keys

# Option 3: Full URL
public_key: https://raw.githubusercontent.com/USERNAME/backup-keys/main/backup_public.pem
```

## Complete Example Workflow

### Setup on Backup Server

```bash
# 1. Generate keys
bbackup init-encryption --method asymmetric

# 2. Upload public key to GitHub Gist
# - Go to gist.github.com
# - Create gist named "bbackup-keys"
# - Upload backup_public.pem

# 3. Configure bbackup (super simple!)
cat >> ~/.config/bbackup/config.yaml <<EOF
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:YOUR_USERNAME
    private_key: ~/.config/bbackup/backup_private.pem
    algorithm: rsa-4096
EOF

# 4. Test encryption
bbackup backup --containers test_container
```

### Setup on Restore Server

```bash
# 1. Copy private key securely (via secure channel)
scp user@backup-server:~/.config/bbackup/backup_private.pem ~/.config/bbackup/

# 2. Configure bbackup (same GitHub shortcut!)
cat >> ~/.config/bbackup/config.yaml <<EOF
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:YOUR_USERNAME
    private_key: ~/.config/bbackup/backup_private.pem
    algorithm: rsa-4096
EOF

# 3. Test restore
bbackup restore --backup-path /path/to/backup
```

## Security Best Practices

1. **Public Keys Only**: Only upload public keys to GitHub
2. **Private Keys**: Never upload private keys anywhere
3. **HTTPS Only**: bbackup requires HTTPS URLs for key fetching
4. **File Permissions**: Set private key permissions to 600
   ```bash
   chmod 600 ~/.config/bbackup/backup_private.pem
   ```
5. **Private Gists**: Use private gists if you want to limit access
6. **Key Rotation**: Regularly rotate encryption keys

## Troubleshooting

### Key Not Found

If bbackup can't find your key with `github:USERNAME`:

1. **Check gist/repo name**: Must be `bbackup-keys` or `backup-keys`
2. **Check filename**: Must be `backup_public.pem`
3. **Use explicit format**: `github:USERNAME/gist:GIST_ID` or `github:USERNAME/repo:REPO_NAME`
4. **Check URL manually**: Try accessing the URL in browser

### Key Format Issues

If you get format errors, ensure the key is in PEM format:
```bash
# Check key format
head -1 public_key.pem
# Should show: -----BEGIN PUBLIC KEY----- or -----BEGIN RSA PUBLIC KEY-----
```

### URL Access Issues

Test URL accessibility:
```bash
# Test GitHub shortcut resolution
curl https://gist.githubusercontent.com/user/bbackup-keys/raw/backup_public.pem
```

## Example URLs

**GitHub Shortcut:**
```
github:USERNAME
gh:USERNAME
github:USERNAME/gist:GIST_ID
github:USERNAME/repo:REPO_NAME
```

**GitHub Gist (Raw):**
```
https://gist.githubusercontent.com/USERNAME/GIST_ID/raw/FILENAME
```

**GitHub Repository (Raw):**
```
https://raw.githubusercontent.com/USERNAME/REPO/BRANCH/FILENAME
```

**GitHub User SSH Keys:**
```
https://github.com/USERNAME.keys
```

## Quick Reference

```bash
# Get SSH keys
curl https://github.com/USERNAME.keys

# Get via API
curl https://api.github.com/users/USERNAME/keys

# Helper script
./scripts/get_github_key.sh USERNAME [output_file]

# Generate keys for bbackup
bbackup init-encryption --method asymmetric

# Configure with GitHub shortcut (easiest!)
# In config.yaml:
#   public_key: github:USERNAME
```
