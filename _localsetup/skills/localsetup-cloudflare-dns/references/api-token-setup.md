# Cloudflare API token setup

1. Log in to https://dash.cloudflare.com/
2. Go to: My Profile > API Tokens > Create Token.
3. Use the "Edit zone DNS" template, or create a custom token with:
   - Permissions: Zone > DNS > Edit
   - Zone resources: Include > All zones (or specific zones)
   - IP restrictions (recommended): add the public IP(s) of the machine(s) calling the API.
4. Copy the token and store it in `<TOOLS_DIR>/cf-dns/cf-dns.conf`:

```
CF_API_TOKEN=your_token_here
```

Set permissions: `chmod 600 <TOOLS_DIR>/cf-dns/cf-dns.conf`

**Multi-machine note:** Each machine needs its public IP whitelisted, or use separate tokens per machine. Do not use a token with no IP restriction across multiple machines.
