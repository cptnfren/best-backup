#!/bin/bash
# Get public key from GitHub for bbackup encryption
# Usage: ./get_github_key.sh <github_username> [output_file]

set -e

GITHUB_USER="${1:-}"
OUTPUT_FILE="${2:-}"

if [ -z "$GITHUB_USER" ]; then
    echo "Usage: $0 <github_username> [output_file]"
    echo ""
    echo "Examples:"
    echo "  $0 octocat                    # Print SSH keys to stdout"
    echo "  $0 octocat backup_key.pem     # Save to file"
    echo "  $0 octocat ~/.config/bbackup/public_key.pem"
    exit 1
fi

echo "Fetching public keys from GitHub user: $GITHUB_USER"
echo ""

# Method 1: Get SSH keys (if user has SSH keys uploaded)
echo "=== SSH Public Keys ==="
curl -s "https://github.com/${GITHUB_USER}.keys" | while read -r key; do
    if [ -n "$key" ]; then
        echo "$key"
        if [ -n "$OUTPUT_FILE" ]; then
            echo "$key" >> "$OUTPUT_FILE"
        fi
    fi
done

echo ""
echo "=== GitHub API (Detailed) ==="
curl -s "https://api.github.com/users/${GITHUB_USER}/keys" | \
    python3 -m json.tool 2>/dev/null || \
    curl -s "https://api.github.com/users/${GITHUB_USER}/keys"

echo ""
echo ""
echo "=== Usage with bbackup ==="
echo ""
echo "For SSH keys, you can:"
echo "1. Save to file and use in config:"
echo "   key_file: ~/.config/bbackup/github_key.pem"
echo ""
echo "2. Create a GitHub Gist with your RSA public key:"
echo "   - Generate key: bbackup init-encryption --method asymmetric"
echo "   - Upload public key to gist"
echo "   - Use raw gist URL in config:"
echo "     public_key: https://gist.githubusercontent.com/user/gist_id/raw/public_key.pem"
echo ""
echo "3. Use GitHub raw content URL:"
echo "   public_key: https://raw.githubusercontent.com/user/repo/main/public_key.pem"
