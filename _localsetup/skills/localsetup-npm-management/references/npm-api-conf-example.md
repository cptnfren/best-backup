# npm-api.conf: config file template

Create this file at `<TOOLS_DIR>/npm-api/npm-api.conf` and set permissions to `600`.
**Never commit this file.** Add it to `.gitignore`.

```bash
# IP address where the NPM admin API is reachable from this machine
NGINX_IP=127.0.0.1

# NPM admin port (default 81)
NGINX_PORT=81

# NPM admin email
API_USER=admin@example.com

# NPM admin password
API_PASS=yourpassword

# Optional: override backup/token directory (default: data/ next to npm_api.py)
# DATA_DIR=/path/to/npm-api/data
```

## Security

```bash
chmod 600 <TOOLS_DIR>/npm-api/npm-api.conf
```

`npm_api.py` will warn if the file is world-readable.

## Environment variable override

You can override the config file path without editing it:

```bash
NPM_CONF=/custom/path/npm-api.conf python3 npm_api.py --info
```

## Debug mode

```bash
LOCALSETUP_DEBUG=1 python3 npm_api.py --host-list
```

Prints full HTTP request/response trace to STDERR.
