"""
Purpose: Native Python client for Nginx Proxy Manager REST API.
         Replaces the upstream npm-api.sh Bash script entirely.
         No shell, curl, or jq dependencies required.
Created: 2026-02-26
Last Updated: 2026-02-27
Requires: requests (see _localsetup/requirements.txt)

Usage:
    python3 npm_api.py --info
    python3 npm_api.py --host-list
    python3 npm_api.py --host-create example.com -i mycontainer -p 8080
    python3 npm_api.py --host-delete 42
    python3 npm_api.py --backup

All operations require npm-api.conf in the same directory as this script,
or the path set via NPM_CONF environment variable.

Environment variables:
    NPM_CONF          Path to config file (default: <script_dir>/npm-api.conf)
    LOCALSETUP_DEBUG  Set to 1 for verbose HTTP tracing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from configparser import ConfigParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Resolve _localsetup/lib/ from skills/localsetup-npm-management/scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from deps import require_deps  # noqa: E402

require_deps(["requests"])

import requests  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_CONF = SCRIPT_DIR / "npm-api.conf"
TOKEN_EXPIRY_HOURS = 24
TOKEN_REFRESH_BUFFER_SECONDS = 3600  # refresh if less than 1 hour remains
MAX_FIELD_LENGTH = 4096
MAX_DOMAIN_LENGTH = 253
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
DEBUG = os.environ.get("LOCALSETUP_DEBUG", "0") == "1"


# ---------------------------------------------------------------------------
# Input hardening helpers
# ---------------------------------------------------------------------------

def _sanitize_str(value: Any, max_len: int = MAX_FIELD_LENGTH, field: str = "field") -> str:
    """Normalize and validate a string from external input."""
    if not isinstance(value, (str, int, float)):
        _die(f"Expected string for {field}, got {type(value).__name__}")
    raw = str(value)
    # Strip control characters (keep printable + whitespace)
    cleaned = "".join(
        ch for ch in raw
        if unicodedata.category(ch)[0] != "C" or ch in ("\t", "\n", "\r")
    )
    cleaned = cleaned.strip()
    if len(cleaned) > max_len:
        _die(f"{field} exceeds maximum length {max_len}: got {len(cleaned)} chars")
    return cleaned


def _validate_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        _die(f"Invalid port value: {value!r} (must be an integer)")
    if not 1 <= port <= 65535:
        _die(f"Port {port} is out of valid range 1-65535")
    return port


def _validate_domain(domain: str) -> str:
    domain = _sanitize_str(domain, MAX_DOMAIN_LENGTH, "domain")
    # RFC 1123 relaxed: labels separated by dots, alphanumeric + hyphens + wildcards
    pattern = re.compile(
        r"^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    )
    if not pattern.match(domain):
        _die(f"Invalid domain name: {domain!r}")
    # Wildcard domains are rejected for host creation (same rule as upstream)
    if domain.startswith("*."):
        _die(f"Wildcard domains are not allowed for proxy host creation: {domain!r}")
    return domain


def _validate_scheme(scheme: str) -> str:
    scheme = _sanitize_str(scheme, 8, "scheme").lower()
    if scheme not in ("http", "https"):
        _die(f"Invalid forward_scheme {scheme!r}; must be 'http' or 'https'")
    return scheme


def _validate_host_id(value: Any) -> int:
    try:
        hid = int(value)
    except (TypeError, ValueError):
        _die(f"Invalid host ID: {value!r} (must be an integer)")
    if hid < 1:
        _die(f"Host ID must be a positive integer, got {hid}")
    return hid


def _die(msg: str, exc: BaseException | None = None) -> None:
    """Emit actionable error to stderr and exit non-zero."""
    label = "[npm_api ERROR]"
    print(f"{label} {msg}", file=sys.stderr)
    if exc is not None and DEBUG:
        import traceback
        traceback.print_exc(file=sys.stderr)
    sys.exit(1)


def _warn(msg: str) -> None:
    print(f"[npm_api WARN] {msg}", file=sys.stderr)


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[npm_api DEBUG] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

class Config:
    """Load and validate npm-api.conf."""

    def __init__(self, conf_path: Path | None = None) -> None:
        path = conf_path or Path(os.environ.get("NPM_CONF", str(DEFAULT_CONF)))
        if not path.exists():
            _die(
                f"Config file not found: {path}\n"
                "  Create it with: NGINX_IP, NGINX_PORT, API_USER, API_PASS\n"
                "  See npm-api.conf.example for a template."
            )
        if oct(path.stat().st_mode)[-3:] not in ("600", "400"):
            _warn(f"Config file {path} is world-readable; run: chmod 600 {path}")

        # ConfigParser requires a section header; we fake one
        raw = path.read_text(encoding="utf-8", errors="replace")
        ini = "[conf]\n" + raw
        cp = ConfigParser(interpolation=None)
        cp.read_string(ini)
        section = cp["conf"]

        self.nginx_ip   = _sanitize_str(section.get("NGINX_IP", "127.0.0.1"), 64, "NGINX_IP")
        self.nginx_port = _validate_port(section.get("NGINX_PORT", "81"))
        self.api_user   = _sanitize_str(section.get("API_USER", ""), 256, "API_USER")
        self.api_pass   = _sanitize_str(section.get("API_PASS", ""), 256, "API_PASS")

        if not self.api_user or not self.api_pass:
            _die("API_USER and API_PASS must be set in the config file")

        default_data_dir = SCRIPT_DIR / "data"
        raw_data_dir = section.get("DATA_DIR", str(default_data_dir))
        self.data_dir = Path(_sanitize_str(raw_data_dir, 512, "DATA_DIR")).expanduser().resolve()

        self.base_url = f"http://{self.nginx_ip}:{self.nginx_port}/api"

        # Per-instance token paths (scoped by IP+port to support multiple NPM instances)
        slug = f"{self.nginx_ip.replace('.', '_')}_{self.nginx_port}"
        self.token_dir  = self.data_dir / slug / "token"
        self.token_file = self.token_dir / "token.txt"
        self.expiry_file = self.token_dir / "expiry.txt"
        self.backup_dir = self.data_dir / slug / "backups"


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

class NPMClient:
    """Low-level HTTP client for the NPM REST API."""

    def __init__(self, config: Config) -> None:
        self.cfg = config
        self._token: str | None = None
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # --- Token management ---------------------------------------------------

    def _ensure_token(self) -> str:
        """Return a valid bearer token, refreshing if needed."""
        if self._token_is_valid():
            assert self._token is not None
            return self._token
        self._refresh_token()
        assert self._token is not None
        return self._token

    def _token_is_valid(self) -> bool:
        tf, ef = self.cfg.token_file, self.cfg.expiry_file
        if not tf.exists() or not ef.exists():
            return False
        try:
            token   = tf.read_text(encoding="utf-8").strip()
            expiry  = ef.read_text(encoding="utf-8").strip()
        except OSError:
            return False
        if not token or not expiry:
            return False
        try:
            # NPM returns ISO8601; parse it
            exp_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except ValueError:
            _debug(f"Could not parse token expiry: {expiry!r}; will refresh")
            return False
        remaining = exp_dt.timestamp() - time.time()
        if remaining < TOKEN_REFRESH_BUFFER_SECONDS:
            _debug(f"Token expires in {remaining:.0f}s; refreshing")
            return False
        self._token = token
        return True

    def _refresh_token(self) -> None:
        """Obtain a new bearer token from NPM and cache it."""
        _debug("Requesting new API token")

        # Step 1: short-lived token (no auth header)
        resp = self._raw_request("POST", "/tokens", {
            "identity": self.cfg.api_user,
            "secret":   self.cfg.api_pass,
        }, auth=False)
        short_token = resp.get("token")
        if not short_token:
            _die(
                "Token endpoint returned no token field.\n"
                f"  Check NGINX_IP={self.cfg.nginx_ip}, NGINX_PORT={self.cfg.nginx_port},\n"
                "  API_USER and API_PASS in npm-api.conf."
            )

        # Step 2: long-lived token
        resp2 = self._raw_request(
            "GET",
            f"/tokens?expiry={TOKEN_EXPIRY_HOURS}h",
            auth_token=short_token,
        )
        token  = resp2.get("token")
        expiry = resp2.get("expires")
        if not token or not expiry:
            _die("Failed to obtain long-lived token from NPM")

        # Persist token files, then update session Authorization header
        self.cfg.token_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.cfg.token_file.write_text(token, encoding="utf-8")
        self.cfg.expiry_file.write_text(expiry, encoding="utf-8")
        os.chmod(self.cfg.token_file, 0o600)
        os.chmod(self.cfg.expiry_file, 0o600)
        self._token = token
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        _debug(f"Token cached; expires {expiry}")

    # --- Core HTTP ----------------------------------------------------------

    def _raw_request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        auth: bool = True,
        auth_token: str | None = None,
    ) -> Any:
        """
        Execute a single HTTP request using the shared session.
        Returns parsed JSON body on success. Raises SystemExit on errors.
        """
        url = self.cfg.base_url + path
        _debug(f"{method} {url}")

        # Override Authorization for this single call when auth_token is given
        # (used during token bootstrap before the session header is set).
        headers: dict[str, str] = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        elif not auth:
            # Temporarily strip Authorization for unauthenticated calls
            headers["Authorization"] = ""

        try:
            resp = self._session.request(
                method,
                url,
                json=body,
                headers={k: v for k, v in headers.items() if v} or None,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            # Extract NPM's structured error message (behavioral parity)
            msg = ""
            if exc.response is not None:
                try:
                    err_json = exc.response.json()
                    msg = (
                        err_json.get("error", {}).get("message")
                        or err_json.get("message")
                        or exc.response.text
                    )
                except Exception:
                    msg = exc.response.text
            _die(
                f"HTTP {status} from {method} {url}\n"
                f"  {msg}\n"
                "  Check NPM admin credentials and that the API is reachable."
            )
        except requests.ConnectionError as exc:
            _die(
                f"Network error reaching {url}: {exc}\n"
                f"  Verify NGINX_IP={self.cfg.nginx_ip} and NGINX_PORT={self.cfg.nginx_port}."
            )
        except requests.RequestException as exc:
            _die(f"Request failed for {method} {url}: {exc}")

        if not resp.content:
            return {}
        try:
            return resp.json()
        except Exception as exc:
            _die(
                f"Invalid JSON response from {method} {url}: {exc}\n"
                f"  Raw (first 200 chars): {resp.text[:200]!r}"
            )

    def request(self, method: str, path: str, body: dict | None = None) -> Any:
        """Authenticated request with automatic token refresh."""
        token = self._ensure_token()
        return self._raw_request(method, path, body, auth_token=token)

    # --- Connectivity check --------------------------------------------------

    def info(self) -> dict:
        return self.request("GET", "/tokens")

    # --- Proxy host operations ----------------------------------------------

    def host_list(self) -> list[dict]:
        data = self.request("GET", "/nginx/proxy-hosts")
        if not isinstance(data, list):
            _die(f"Expected list from host-list, got {type(data).__name__}")
        return data

    def host_search(self, domain: str) -> list[dict]:
        domain = _sanitize_str(domain, MAX_DOMAIN_LENGTH, "domain")
        hosts = self.host_list()
        domain_lower = domain.lower()
        return [
            h for h in hosts
            if any(d.lower() == domain_lower for d in h.get("domain_names", []))
        ]

    def host_show(self, host_id: int) -> dict:
        host_id = _validate_host_id(host_id)
        return self.request("GET", f"/nginx/proxy-hosts/{host_id}")

    def host_create(
        self,
        domain: str,
        forward_host: str,
        forward_port: int,
        forward_scheme: str = "http",
        ssl_forced: bool = True,
        http2_support: bool = True,
        hsts_enabled: bool = False,
        caching_enabled: bool = False,
        block_exploits: bool = True,
        allow_websocket_upgrade: bool = False,
        access_list_id: int = 0,
        advanced_config: str = "",
        locations: list | None = None,
    ) -> dict:
        domain        = _validate_domain(domain)
        forward_host  = _sanitize_str(forward_host, 253, "forward_host")
        forward_port  = _validate_port(forward_port)
        forward_scheme = _validate_scheme(forward_scheme)
        advanced_config = _sanitize_str(advanced_config, MAX_FIELD_LENGTH, "advanced_config")

        payload: dict[str, Any] = {
            "domain_names":           [domain],
            "forward_host":           forward_host,
            "forward_port":           forward_port,
            "forward_scheme":         forward_scheme,
            "ssl_forced":             ssl_forced,
            "http2_support":          http2_support,
            "hsts_enabled":           hsts_enabled,
            "caching_enabled":        caching_enabled,
            "block_exploits":         block_exploits,
            "allow_websocket_upgrade": allow_websocket_upgrade,
            "access_list_id":         access_list_id or None,
            "certificate_id":         None,
            "advanced_config":        advanced_config,
            "meta":                   {"dns_challenge": None},
            "locations":              locations or [],
            "enabled":                True,
        }
        return self.request("POST", "/nginx/proxy-hosts", payload)

    def host_update(self, host_id: int, fields: dict) -> dict:
        """Patch specific fields on an existing proxy host (PATCH via PUT)."""
        host_id = _validate_host_id(host_id)
        # Validate any field we recognise; pass others through for forward-compat
        sanitized: dict[str, Any] = {}
        for key, val in fields.items():
            key = _sanitize_str(key, 64, "field name")
            if key == "forward_host":
                sanitized[key] = _sanitize_str(val, 253, key)
            elif key == "forward_port":
                sanitized[key] = _validate_port(val)
            elif key == "forward_scheme":
                sanitized[key] = _validate_scheme(val)
            elif key in ("ssl_forced", "http2_support", "hsts_enabled",
                         "caching_enabled", "block_exploits", "allow_websocket_upgrade",
                         "enabled"):
                if not isinstance(val, bool):
                    _die(f"Field {key!r} must be a boolean, got {type(val).__name__}")
                sanitized[key] = val
            elif key == "advanced_config":
                sanitized[key] = _sanitize_str(val, MAX_FIELD_LENGTH, key)
            elif key == "access_list_id":
                sanitized[key] = int(val) if val else None
            else:
                # Unknown field: pass through with basic string sanitization
                sanitized[key] = _sanitize_str(str(val), MAX_FIELD_LENGTH, key)
        return self.request("PUT", f"/nginx/proxy-hosts/{host_id}", sanitized)

    def host_enable(self, host_id: int) -> dict:
        host_id = _validate_host_id(host_id)
        return self.request("PUT", f"/nginx/proxy-hosts/{host_id}", {"enabled": True})

    def host_disable(self, host_id: int) -> dict:
        host_id = _validate_host_id(host_id)
        return self.request("PUT", f"/nginx/proxy-hosts/{host_id}", {"enabled": False})

    def host_delete(self, host_id: int) -> bool:
        host_id = _validate_host_id(host_id)
        self.request("DELETE", f"/nginx/proxy-hosts/{host_id}")
        return True

    # --- Backup -------------------------------------------------------------

    def backup(self, backup_dir: Path | None = None) -> Path:
        """
        Snapshot proxy hosts, users, settings, and access lists to JSON files.
        Returns the path of the timestamped backup directory created.
        """
        ts = datetime.now(tz=timezone.utc).strftime("%Y_%m_%d__%H_%M_%S")
        out = (backup_dir or self.cfg.backup_dir) / ts
        out.mkdir(parents=True, mode=0o700, exist_ok=True)

        endpoints: list[tuple[str, str]] = [
            ("/nginx/proxy-hosts", "proxy_hosts"),
            ("/users",             "users"),
            ("/settings",         "settings"),
            ("/nginx/access-lists", "access_lists"),
            ("/nginx/certificates", "certificates"),
        ]
        summary: dict[str, int] = {}
        errors: list[str] = []

        for api_path, name in endpoints:
            try:
                data = self.request("GET", api_path)
                dest = out / f"{name}.json"
                dest.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                os.chmod(dest, 0o600)
                count = len(data) if isinstance(data, list) else 1
                summary[name] = count
                _debug(f"Backed up {name}: {count} item(s)")
            except SystemExit:
                # _die was called; record and continue for partial backup
                errors.append(name)

        full: dict[str, Any] = {"backup_timestamp": ts, "items": summary}
        manifest = out / "manifest.json"
        manifest.write_text(json.dumps(full, indent=2), encoding="utf-8")
        os.chmod(manifest, 0o600)

        if errors:
            _warn(f"Backup completed with errors on: {', '.join(errors)}")

        return out


# ---------------------------------------------------------------------------
# Output formatting (GFM-compatible per TOOLING_POLICY.md)
# ---------------------------------------------------------------------------

def _fmt_hosts_table(hosts: list[dict]) -> str:
    if not hosts:
        return "*No proxy hosts found.*"
    lines = ["| ID | Domain | Enabled | SSL | Target | Cert ID |",
             "|----|--------|---------|-----|--------|---------|"]
    for h in hosts:
        hid      = h.get("id", "?")
        domains  = ", ".join(h.get("domain_names", []))
        enabled  = "yes" if h.get("enabled") else "no"
        cert_id  = h.get("certificate_id") or "-"
        ssl      = "yes" if cert_id != "-" else "no"
        scheme   = h.get("forward_scheme", "http")
        fhost    = h.get("forward_host", "?")
        fport    = h.get("forward_port", "?")
        target   = f"`{scheme}://{fhost}:{fport}`"
        lines.append(f"| {hid} | {domains} | {enabled} | {ssl} | {target} | {cert_id} |")
    return "\n".join(lines)


def _fmt_host_detail(h: dict) -> str:
    hid      = h.get("id", "?")
    domains  = ", ".join(h.get("domain_names", []))
    enabled  = "yes" if h.get("enabled") else "no"
    scheme   = h.get("forward_scheme", "http")
    fhost    = h.get("forward_host", "?")
    fport    = h.get("forward_port", "?")
    cert_id  = h.get("certificate_id") or "-"
    ssl_f    = "yes" if h.get("ssl_forced") else "no"
    http2    = "yes" if h.get("http2_support") else "no"
    hsts     = "yes" if h.get("hsts_enabled") else "no"
    ws       = "yes" if h.get("allow_websocket_upgrade") else "no"
    caching  = "yes" if h.get("caching_enabled") else "no"
    exploits = "yes" if h.get("block_exploits") else "no"
    adv      = h.get("advanced_config") or "-"
    acl_id   = h.get("access_list_id") or "-"

    return (
        f"## Proxy host {hid}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **Domain(s)** | {domains} |\n"
        f"| **Enabled** | {enabled} |\n"
        f"| **Target** | `{scheme}://{fhost}:{fport}` |\n"
        f"| **Certificate ID** | {cert_id} |\n"
        f"| **SSL forced** | {ssl_f} |\n"
        f"| **HTTP/2** | {http2} |\n"
        f"| **HSTS** | {hsts} |\n"
        f"| **WebSocket upgrade** | {ws} |\n"
        f"| **Caching** | {caching} |\n"
        f"| **Block exploits** | {exploits} |\n"
        f"| **Access list ID** | {acl_id} |\n"
        f"| **Advanced config** | {adv} |\n"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="npm_api.py",
        description="Nginx Proxy Manager API client (Python, no shell dependencies)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 npm_api.py --info\n"
            "  python3 npm_api.py --host-list\n"
            "  python3 npm_api.py --host-create example.com -i mycontainer -p 8080\n"
            "  python3 npm_api.py --host-create app.example.com -i appcontainer -p 3000 --websocket\n"
            "  python3 npm_api.py --host-search example.com\n"
            "  python3 npm_api.py --host-show 5\n"
            "  python3 npm_api.py --host-update 5 forward_port=9000\n"
            "  python3 npm_api.py --host-enable 5\n"
            "  python3 npm_api.py --host-disable 5\n"
            "  python3 npm_api.py --host-delete 5\n"
            "  python3 npm_api.py --backup\n"
        ),
    )

    ops = p.add_mutually_exclusive_group(required=True)
    ops.add_argument("--info",         action="store_true", help="Check API connectivity and token")
    ops.add_argument("--host-list",    action="store_true", help="List all proxy hosts")
    ops.add_argument("--host-search",  metavar="DOMAIN",    help="Search proxy hosts by domain")
    ops.add_argument("--host-show",    metavar="ID",        help="Show details for a proxy host ID")
    ops.add_argument("--host-create",  metavar="DOMAIN",    help="Create a proxy host for DOMAIN")
    ops.add_argument("--host-update",  metavar="ID",        help="Update fields on a proxy host ID")
    ops.add_argument("--host-enable",  metavar="ID",        help="Enable a proxy host by ID")
    ops.add_argument("--host-disable", metavar="ID",        help="Disable a proxy host by ID")
    ops.add_argument("--host-delete",  metavar="ID",        help="Delete a proxy host by ID")
    ops.add_argument("--backup",       action="store_true", help="Backup NPM configuration to DATA_DIR")

    # Create options
    p.add_argument("-i", "--forward-host",   metavar="HOST",   help="Backend container name or hostname")
    p.add_argument("-p", "--forward-port",   metavar="PORT",   type=int, help="Backend port")
    p.add_argument("--scheme",               metavar="SCHEME", default="http", help="forward_scheme: http or https (default: http)")
    p.add_argument("--websocket",            action="store_true", help="Enable WebSocket upgrade")
    p.add_argument("--no-ssl-force",         action="store_true", help="Do not force SSL redirect (default: ssl_forced=true)")
    p.add_argument("--no-http2",             action="store_true", help="Disable HTTP/2 (default: enabled)")
    p.add_argument("--hsts",                 action="store_true", help="Enable HSTS header")
    p.add_argument("--caching",              action="store_true", help="Enable NPM caching")
    p.add_argument("--no-block-exploits",    action="store_true", help="Disable exploit blocking (default: enabled)")
    p.add_argument("--access-list-id",       metavar="ACL_ID", type=int, default=0, help="NPM access list ID (default: 0 = none)")
    p.add_argument("--advanced-config",      metavar="CONFIG", default="", help="Raw nginx config block")

    # Update options (KEY=VALUE pairs)
    p.add_argument("fields", nargs="*", help="KEY=VALUE pairs for --host-update")

    # Shared
    p.add_argument("--conf", metavar="PATH", help="Path to npm-api.conf (overrides NPM_CONF env)")
    p.add_argument("--backup-dir", metavar="PATH", help="Override backup output directory")

    return p


def main() -> None:  # noqa: C901 (complexity acceptable for CLI dispatcher)
    parser = _build_parser()
    args = parser.parse_args()

    conf_path = Path(args.conf).expanduser().resolve() if args.conf else None
    cfg = Config(conf_path)
    client = NPMClient(cfg)

    # --info
    if args.info:
        result = client.info()
        print("## NPM API connectivity\n")
        print("**Status:** OK")
        print(f"**Endpoint:** `{cfg.base_url}`")
        expires = result.get("expires", "unknown")
        print(f"**Token expires:** {expires}")
        return

    # --host-list
    if args.host_list:
        hosts = client.host_list()
        print("## Proxy hosts\n")
        print(_fmt_hosts_table(hosts))
        return

    # --host-search
    if args.host_search:
        domain = _sanitize_str(args.host_search, MAX_DOMAIN_LENGTH, "domain")
        hosts = client.host_search(domain)
        print(f"## Search: `{domain}`\n")
        print(_fmt_hosts_table(hosts))
        return

    # --host-show
    if args.host_show:
        hid = _validate_host_id(args.host_show)
        host = client.host_show(hid)
        print(_fmt_host_detail(host))
        return

    # --host-create
    if args.host_create:
        domain = args.host_create
        if not args.forward_host:
            _die("--host-create requires -i/--forward-host (container name or hostname)")
        if not args.forward_port:
            _die("--host-create requires -p/--forward-port")
        host = client.host_create(
            domain              = domain,
            forward_host        = args.forward_host,
            forward_port        = args.forward_port,
            forward_scheme      = args.scheme,
            ssl_forced          = not args.no_ssl_force,
            http2_support       = not args.no_http2,
            hsts_enabled        = args.hsts,
            caching_enabled     = args.caching,
            block_exploits      = not args.no_block_exploits,
            allow_websocket_upgrade = args.websocket,
            access_list_id      = args.access_list_id,
            advanced_config     = args.advanced_config,
        )
        hid = host.get("id", "?")
        print(f"## Proxy host created\n")
        print(f"**Domain:** `{domain}`  ")
        print(f"**ID:** {hid}  ")
        print(f"**Target:** `{args.scheme}://{args.forward_host}:{args.forward_port}`  ")
        print(f"\n> Note: attach an SSL certificate via NPM UI or `--host-ssl-enable` if HTTPS is required.")
        return

    # --host-update
    if args.host_update:
        hid = _validate_host_id(args.host_update)
        if not args.fields:
            _die("--host-update requires at least one KEY=VALUE field argument")
        fields: dict[str, Any] = {}
        for item in args.fields:
            if "=" not in item:
                _die(f"Invalid field format {item!r}; expected KEY=VALUE")
            k, _, v = item.partition("=")
            fields[k.strip()] = v.strip()
        result = client.host_update(hid, fields)
        print(f"## Host {hid} updated\n")
        print(_fmt_host_detail(result))
        return

    # --host-enable
    if args.host_enable:
        hid = _validate_host_id(args.host_enable)
        client.host_enable(hid)
        print(f"**Host {hid} enabled.**")
        return

    # --host-disable
    if args.host_disable:
        hid = _validate_host_id(args.host_disable)
        client.host_disable(hid)
        print(f"**Host {hid} disabled.**")
        return

    # --host-delete
    if args.host_delete:
        hid = _validate_host_id(args.host_delete)
        client.host_delete(hid)
        print(f"**Host {hid} deleted.**")
        return

    # --backup
    if args.backup:
        backup_dir = Path(args.backup_dir).expanduser().resolve() if args.backup_dir else None
        out = client.backup(backup_dir)
        print(f"## Backup complete\n")
        print(f"**Location:** `{out}`")
        return


if __name__ == "__main__":
    main()
