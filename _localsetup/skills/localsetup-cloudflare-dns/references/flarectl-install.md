# flarectl install methods

## Option 1: Go install (recommended)

```bash
go install github.com/cloudflare/cloudflare-go/cmd/flarectl@latest
cp "$(go env GOPATH)/bin/flarectl" <TOOLS_DIR>/cf-dns/flarectl
```

## Option 2: Homebrew (Linux/macOS)

```bash
brew install flarectl
```

The wrapper resolves the binary from PATH, so no copy is needed for Homebrew installs.

## Option 3: Manual build

```bash
git clone https://github.com/cloudflare/cloudflare-go
cd cloudflare-go
go build ./cmd/flarectl
cp flarectl <TOOLS_DIR>/cf-dns/flarectl
```

## Verify

```bash
flarectl --version
```
