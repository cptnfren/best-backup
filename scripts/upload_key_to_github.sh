#!/bin/bash
# Upload bbackup public key to GitHub gist
# Usage: ./upload_key_to_github.sh [key_file] [gist_name]

set -e

KEY_FILE="${1:-$HOME/.config/bbackup/backup_public.pem}"
GIST_NAME="${2:-bbackup-keys}"

if [ ! -f "$KEY_FILE" ]; then
    echo "Error: Key file not found: $KEY_FILE"
    echo "Usage: $0 [key_file] [gist_name]"
    exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo "Error: Not logged into GitHub"
    echo "Run: gh auth login"
    exit 1
fi

# Get username
USERNAME=$(gh api user --jq .login)

echo "Uploading public key to GitHub..."
echo "  Key file: $KEY_FILE"
echo "  Username: $USERNAME"
echo "  Gist name: $GIST_NAME"
echo ""

# Create gist with the key file
GIST_URL=$(gh gist create --public --desc "bbackup encryption public key" "$KEY_FILE" 2>&1 | grep -o 'https://gist.github.com/[^ ]*' | head -1)

if [ -z "$GIST_URL" ]; then
    echo "Error: Failed to create gist"
    exit 1
fi

echo "✓ Gist created: $GIST_URL"
echo ""
echo "You can now use in your config:"
echo "  public_key: github:$USERNAME"
echo ""
echo "Or with explicit gist ID:"
GIST_ID=$(echo "$GIST_URL" | sed 's|https://gist.github.com/||')
echo "  public_key: github:$USERNAME/gist:$GIST_ID"
echo ""
echo "Note: For auto-discovery to work, the gist should be named '$GIST_NAME'"
echo "Current gist URL: $GIST_URL"
