"""
Test suite for npm_api.py.
Tests all logic that does not require a live NPM instance:
- Input sanitization and validation
- Config loading (good + bad paths)
- Token caching logic
- CLI argument parsing
- Output formatting
- Backup filesystem logic
- HTTP error path handling (via mock)
"""

import json
import os
import sys
import tempfile
import time
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# The file under test lives alongside this test script
sys.path.insert(0, str(Path(__file__).parent))
import npm_api


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_conf(tmp: Path, **overrides) -> Path:
    """Write a minimal valid npm-api.conf and return its path."""
    fields = {
        "NGINX_IP": "127.0.0.1",
        "NGINX_PORT": "81",
        "API_USER": "admin@test.local",
        "API_PASS": "testpass",
    }
    fields.update(overrides)
    conf = tmp / "npm-api.conf"
    conf.write_text("\n".join(f"{k}={v}" for k, v in fields.items()))
    conf.chmod(0o600)
    return conf


# ---------------------------------------------------------------------------
# Input hardening: _sanitize_str
# ---------------------------------------------------------------------------

class TestSanitizeStr(unittest.TestCase):

    def test_basic_string_passthrough(self):
        self.assertEqual(npm_api._sanitize_str("hello"), "hello")

    def test_strips_leading_trailing_whitespace(self):
        self.assertEqual(npm_api._sanitize_str("  hello  "), "hello")

    def test_strips_control_characters(self):
        # null bytes, ESC, BEL should be removed
        self.assertEqual(npm_api._sanitize_str("hel\x00lo\x1b"), "hello")

    def test_keeps_tabs_and_newlines(self):
        result = npm_api._sanitize_str("line1\nline2")
        self.assertIn("line1", result)
        self.assertIn("line2", result)

    def test_accepts_int(self):
        self.assertEqual(npm_api._sanitize_str(42), "42")

    def test_accepts_float(self):
        self.assertEqual(npm_api._sanitize_str(3.14), "3.14")

    def test_rejects_list(self):
        with self.assertRaises(SystemExit):
            npm_api._sanitize_str(["bad"])

    def test_max_length_exceeded(self):
        with self.assertRaises(SystemExit):
            npm_api._sanitize_str("a" * 10, max_len=5)

    def test_exactly_at_max_length(self):
        self.assertEqual(npm_api._sanitize_str("abcde", max_len=5), "abcde")

    def test_empty_string_ok(self):
        self.assertEqual(npm_api._sanitize_str(""), "")


# ---------------------------------------------------------------------------
# Input hardening: _validate_port
# ---------------------------------------------------------------------------

class TestValidatePort(unittest.TestCase):

    def test_valid_port(self):
        self.assertEqual(npm_api._validate_port(80), 80)
        self.assertEqual(npm_api._validate_port("8080"), 8080)
        self.assertEqual(npm_api._validate_port(65535), 65535)
        self.assertEqual(npm_api._validate_port(1), 1)

    def test_zero_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_port(0)

    def test_above_max_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_port(65536)

    def test_negative_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_port(-1)

    def test_non_numeric_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_port("abc")

    def test_none_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_port(None)


# ---------------------------------------------------------------------------
# Input hardening: _validate_domain
# ---------------------------------------------------------------------------

class TestValidateDomain(unittest.TestCase):

    def test_valid_domain(self):
        self.assertEqual(npm_api._validate_domain("example.com"), "example.com")
        self.assertEqual(npm_api._validate_domain("sub.example.com"), "sub.example.com")
        self.assertEqual(npm_api._validate_domain("my-app.example.co.uk"), "my-app.example.co.uk")

    def test_wildcard_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_domain("*.example.com")

    def test_bare_label_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_domain("localhost")

    def test_ip_address_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_domain("192.168.1.1")

    def test_empty_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_domain("")

    def test_trailing_dot_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_domain("example.com.")

    def test_injection_attempt_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_domain("example.com; rm -rf /")

    def test_uppercase_accepted(self):
        # Domain validation should accept mixed case
        result = npm_api._validate_domain("Example.COM")
        self.assertEqual(result, "Example.COM")


# ---------------------------------------------------------------------------
# Input hardening: _validate_scheme
# ---------------------------------------------------------------------------

class TestValidateScheme(unittest.TestCase):

    def test_http_accepted(self):
        self.assertEqual(npm_api._validate_scheme("http"), "http")

    def test_https_accepted(self):
        self.assertEqual(npm_api._validate_scheme("https"), "https")

    def test_uppercase_normalised(self):
        self.assertEqual(npm_api._validate_scheme("HTTP"), "http")

    def test_ftp_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_scheme("ftp")

    def test_empty_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_scheme("")


# ---------------------------------------------------------------------------
# Input hardening: _validate_host_id
# ---------------------------------------------------------------------------

class TestValidateHostId(unittest.TestCase):

    def test_valid_int(self):
        self.assertEqual(npm_api._validate_host_id(5), 5)

    def test_valid_string_int(self):
        self.assertEqual(npm_api._validate_host_id("42"), 42)

    def test_zero_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_host_id(0)

    def test_negative_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_host_id(-1)

    def test_string_rejected(self):
        with self.assertRaises(SystemExit):
            npm_api._validate_host_id("abc")

    def test_float_truncated_correctly(self):
        # int("5.0") raises, but int(5.0) works
        self.assertEqual(npm_api._validate_host_id(5.0), 5)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestConfig(unittest.TestCase):

    def test_loads_valid_conf(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            conf = make_conf(tmp)
            cfg = npm_api.Config(conf)
            self.assertEqual(cfg.nginx_ip, "127.0.0.1")
            self.assertEqual(cfg.nginx_port, 81)
            self.assertEqual(cfg.api_user, "admin@test.local")
            self.assertEqual(cfg.api_pass, "testpass")
            self.assertEqual(cfg.base_url, "http://127.0.0.1:81/api")

    def test_custom_port(self):
        with tempfile.TemporaryDirectory() as td:
            conf = make_conf(Path(td), NGINX_PORT="8181")
            cfg = npm_api.Config(conf)
            self.assertEqual(cfg.nginx_port, 8181)

    def test_missing_conf_dies(self):
        with self.assertRaises(SystemExit):
            npm_api.Config(Path("/nonexistent/npm-api.conf"))

    def test_missing_api_user_dies(self):
        with tempfile.TemporaryDirectory() as td:
            conf = make_conf(Path(td), API_USER="")
            with self.assertRaises(SystemExit):
                npm_api.Config(conf)

    def test_missing_api_pass_dies(self):
        with tempfile.TemporaryDirectory() as td:
            conf = make_conf(Path(td), API_PASS="")
            with self.assertRaises(SystemExit):
                npm_api.Config(conf)

    def test_invalid_port_dies(self):
        with tempfile.TemporaryDirectory() as td:
            conf = make_conf(Path(td), NGINX_PORT="notaport")
            with self.assertRaises(SystemExit):
                npm_api.Config(conf)

    def test_token_paths_scoped_by_ip_port(self):
        with tempfile.TemporaryDirectory() as td:
            conf = make_conf(Path(td))
            cfg = npm_api.Config(conf)
            # Token dir slug should contain IP and port
            self.assertIn("127_0_0_1", str(cfg.token_dir))
            self.assertIn("81", str(cfg.token_dir))

    def test_custom_data_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            custom_data = tmp / "mydata"
            conf = make_conf(tmp, DATA_DIR=str(custom_data))
            cfg = npm_api.Config(conf)
            self.assertTrue(str(cfg.data_dir).endswith("mydata"))

    def test_env_var_conf_path(self):
        with tempfile.TemporaryDirectory() as td:
            conf = make_conf(Path(td))
            with patch.dict(os.environ, {"NPM_CONF": str(conf)}):
                cfg = npm_api.Config()
                self.assertEqual(cfg.nginx_ip, "127.0.0.1")


# ---------------------------------------------------------------------------
# Token validity logic
# ---------------------------------------------------------------------------

class TestTokenValidity(unittest.TestCase):

    def _make_client(self, tmp: Path) -> npm_api.NPMClient:
        conf = make_conf(tmp)
        cfg = npm_api.Config(conf)
        return npm_api.NPMClient(cfg)

    def test_missing_token_files_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            self.assertFalse(client._token_is_valid())

    def test_empty_token_file_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            client.cfg.token_dir.mkdir(parents=True, exist_ok=True)
            client.cfg.token_file.write_text("")
            client.cfg.expiry_file.write_text("")
            self.assertFalse(client._token_is_valid())

    def test_expired_token_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            client.cfg.token_dir.mkdir(parents=True, exist_ok=True)
            client.cfg.token_file.write_text("sometoken")
            # Expiry in the past
            client.cfg.expiry_file.write_text("2020-01-01T00:00:00Z")
            self.assertFalse(client._token_is_valid())

    def test_token_expiring_soon_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            client.cfg.token_dir.mkdir(parents=True, exist_ok=True)
            client.cfg.token_file.write_text("sometoken")
            # Expiry 30 minutes from now (inside the 1-hour buffer)
            future = time.time() + 1800
            from datetime import datetime, timezone
            exp_str = datetime.fromtimestamp(future, tz=timezone.utc).isoformat()
            client.cfg.expiry_file.write_text(exp_str)
            self.assertFalse(client._token_is_valid())

    def test_valid_token_returns_true(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            client.cfg.token_dir.mkdir(parents=True, exist_ok=True)
            client.cfg.token_file.write_text("goodtoken")
            # Expiry 2 hours from now (outside the 1-hour buffer)
            future = time.time() + 7200
            from datetime import datetime, timezone
            exp_str = datetime.fromtimestamp(future, tz=timezone.utc).isoformat()
            client.cfg.expiry_file.write_text(exp_str)
            self.assertTrue(client._token_is_valid())
            self.assertEqual(client._token, "goodtoken")

    def test_unparseable_expiry_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            client.cfg.token_dir.mkdir(parents=True, exist_ok=True)
            client.cfg.token_file.write_text("goodtoken")
            client.cfg.expiry_file.write_text("not-a-date")
            self.assertFalse(client._token_is_valid())


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

class TestFormatHostsTable(unittest.TestCase):

    def test_empty_list(self):
        result = npm_api._fmt_hosts_table([])
        self.assertIn("No proxy hosts", result)

    def test_single_host(self):
        hosts = [{
            "id": 1,
            "domain_names": ["example.com"],
            "enabled": True,
            "certificate_id": None,
            "forward_scheme": "http",
            "forward_host": "mycontainer",
            "forward_port": 8080,
        }]
        result = npm_api._fmt_hosts_table(hosts)
        self.assertIn("example.com", result)
        self.assertIn("mycontainer", result)
        self.assertIn("8080", result)
        self.assertIn("yes", result)   # enabled
        self.assertIn("no", result)    # no SSL
        # GFM table structure
        self.assertIn("|", result)

    def test_host_with_ssl(self):
        hosts = [{
            "id": 2,
            "domain_names": ["secure.example.com"],
            "enabled": True,
            "certificate_id": 5,
            "forward_scheme": "http",
            "forward_host": "appcontainer",
            "forward_port": 3000,
        }]
        result = npm_api._fmt_hosts_table(hosts)
        self.assertIn("5", result)     # cert ID
        self.assertIn("yes", result)   # SSL yes

    def test_disabled_host(self):
        hosts = [{
            "id": 3,
            "domain_names": ["off.example.com"],
            "enabled": False,
            "certificate_id": None,
            "forward_scheme": "http",
            "forward_host": "offcontainer",
            "forward_port": 9000,
        }]
        result = npm_api._fmt_hosts_table(hosts)
        self.assertIn("no", result)

    def test_multiple_domains(self):
        hosts = [{
            "id": 4,
            "domain_names": ["a.com", "b.com"],
            "enabled": True,
            "certificate_id": None,
            "forward_scheme": "http",
            "forward_host": "c",
            "forward_port": 80,
        }]
        result = npm_api._fmt_hosts_table(hosts)
        self.assertIn("a.com", result)
        self.assertIn("b.com", result)


class TestFormatHostDetail(unittest.TestCase):

    def test_detail_contains_all_fields(self):
        h = {
            "id": 7,
            "domain_names": ["app.example.com"],
            "enabled": True,
            "forward_scheme": "https",
            "forward_host": "backend",
            "forward_port": 443,
            "certificate_id": 3,
            "ssl_forced": True,
            "http2_support": True,
            "hsts_enabled": False,
            "allow_websocket_upgrade": True,
            "caching_enabled": False,
            "block_exploits": True,
            "advanced_config": "",
            "access_list_id": None,
        }
        result = npm_api._fmt_host_detail(h)
        self.assertIn("app.example.com", result)
        self.assertIn("backend", result)
        self.assertIn("443", result)
        self.assertIn("https", result)
        self.assertIn("## Proxy host 7", result)
        # GFM table
        self.assertIn("| **Domain(s)**", result)


# ---------------------------------------------------------------------------
# CLI argument parsing (no config needed, parsing only)
# ---------------------------------------------------------------------------

class TestCLIParsing(unittest.TestCase):

    def _parse(self, args):
        parser = npm_api._build_parser()
        return parser.parse_args(args)

    def test_info_flag(self):
        args = self._parse(["--info"])
        self.assertTrue(args.info)

    def test_host_list_flag(self):
        args = self._parse(["--host-list"])
        self.assertTrue(args.host_list)

    def test_host_create_with_required_args(self):
        args = self._parse(["--host-create", "example.com", "-i", "mycontainer", "-p", "8080"])
        self.assertEqual(args.host_create, "example.com")
        self.assertEqual(args.forward_host, "mycontainer")
        self.assertEqual(args.forward_port, 8080)

    def test_host_create_defaults(self):
        args = self._parse(["--host-create", "example.com", "-i", "c", "-p", "80"])
        self.assertEqual(args.scheme, "http")
        self.assertFalse(args.websocket)
        self.assertFalse(args.no_ssl_force)
        self.assertFalse(args.no_http2)
        self.assertFalse(args.hsts)
        self.assertFalse(args.caching)
        self.assertFalse(args.no_block_exploits)
        self.assertEqual(args.access_list_id, 0)

    def test_host_create_all_flags(self):
        args = self._parse([
            "--host-create", "app.example.com",
            "-i", "appcontainer", "-p", "3000",
            "--scheme", "https",
            "--websocket",
            "--no-ssl-force",
            "--no-http2",
            "--hsts",
            "--caching",
            "--no-block-exploits",
            "--access-list-id", "5",
            "--advanced-config", "client_max_body_size 50M;",
        ])
        self.assertEqual(args.scheme, "https")
        self.assertTrue(args.websocket)
        self.assertTrue(args.no_ssl_force)
        self.assertTrue(args.no_http2)
        self.assertTrue(args.hsts)
        self.assertTrue(args.caching)
        self.assertTrue(args.no_block_exploits)
        self.assertEqual(args.access_list_id, 5)
        self.assertEqual(args.advanced_config, "client_max_body_size 50M;")

    def test_host_update_with_fields(self):
        args = self._parse(["--host-update", "3", "forward_port=9000", "forward_host=newcontainer"])
        self.assertEqual(args.host_update, "3")
        self.assertIn("forward_port=9000", args.fields)
        self.assertIn("forward_host=newcontainer", args.fields)

    def test_host_delete(self):
        args = self._parse(["--host-delete", "10"])
        self.assertEqual(args.host_delete, "10")

    def test_backup_flag(self):
        args = self._parse(["--backup"])
        self.assertTrue(args.backup)

    def test_backup_with_dir(self):
        args = self._parse(["--backup", "--backup-dir", "/tmp/mybackup"])
        self.assertEqual(args.backup_dir, "/tmp/mybackup")

    def test_conf_override(self):
        args = self._parse(["--info", "--conf", "/tmp/custom.conf"])
        self.assertEqual(args.conf, "/tmp/custom.conf")

    def test_mutually_exclusive_ops(self):
        with self.assertRaises(SystemExit):
            self._parse(["--info", "--host-list"])

    def test_no_op_exits(self):
        # argparse requires the group, so no args = error
        with self.assertRaises(SystemExit):
            self._parse([])


# ---------------------------------------------------------------------------
# host_update field parsing (the KEY=VALUE loop in main())
# ---------------------------------------------------------------------------

class TestFieldParsing(unittest.TestCase):

    def test_valid_kv_pairs(self):
        # Simulate what main() does with --host-update fields
        raw_fields = ["forward_port=9000", "forward_host=newcontainer"]
        fields = {}
        for item in raw_fields:
            k, _, v = item.partition("=")
            fields[k.strip()] = v.strip()
        self.assertEqual(fields["forward_port"], "9000")
        self.assertEqual(fields["forward_host"], "newcontainer")

    def test_missing_equals_detected(self):
        # The main() loop calls _die on missing "="
        bad = "forward_portNOEQUALS"
        with self.assertRaises(SystemExit):
            if "=" not in bad:
                npm_api._die(f"Invalid field format {bad!r}; expected KEY=VALUE")

    def test_value_with_equals_in_it(self):
        # partition should only split on the first "="
        item = "advanced_config=client_max_body_size=50M"
        k, _, v = item.partition("=")
        self.assertEqual(k, "advanced_config")
        self.assertEqual(v, "client_max_body_size=50M")


# ---------------------------------------------------------------------------
# host_update sanitization in NPMClient
# ---------------------------------------------------------------------------

class TestHostUpdateSanitization(unittest.TestCase):

    def _make_client(self, tmp: Path) -> npm_api.NPMClient:
        conf = make_conf(tmp)
        cfg = npm_api.Config(conf)
        return npm_api.NPMClient(cfg)

    def test_boolean_string_rejected(self):
        """Boolean fields must actually be booleans, not strings."""
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            with self.assertRaises(SystemExit):
                client.host_update(1, {"ssl_forced": "true"})  # string not bool

    def test_bad_port_in_update_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            with self.assertRaises(SystemExit):
                client.host_update(1, {"forward_port": "notaport"})

    def test_bad_scheme_in_update_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            with self.assertRaises(SystemExit):
                client.host_update(1, {"forward_scheme": "ftp"})

    def test_bad_host_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            with self.assertRaises(SystemExit):
                client.host_update(0, {"forward_port": 80})


# ---------------------------------------------------------------------------
# Backup filesystem logic (no network)
# ---------------------------------------------------------------------------

class TestBackup(unittest.TestCase):

    def _make_client_with_mock_request(self, tmp: Path) -> npm_api.NPMClient:
        conf = make_conf(tmp)
        cfg = npm_api.Config(conf)
        client = npm_api.NPMClient(cfg)
        # Inject a mock _ensure_token so backup() can call request() without network
        client._token = "faketoken"
        return client

    def test_backup_creates_timestamped_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            client = self._make_client_with_mock_request(tmp)
            backup_out = tmp / "backups"

            fake_data = {
                "/nginx/proxy-hosts": [{"id": 1}],
                "/users": [{"id": 1}],
                "/settings": {"key": "val"},
                "/nginx/access-lists": [],
                "/nginx/certificates": [],
            }

            def fake_request(method, path, body=None):
                return fake_data.get(path, [])

            client.request = fake_request
            out = client.backup(backup_dir=backup_out)

            self.assertTrue(out.exists())
            self.assertTrue((out / "proxy_hosts.json").exists())
            self.assertTrue((out / "users.json").exists())
            self.assertTrue((out / "settings.json").exists())
            self.assertTrue((out / "manifest.json").exists())

    def test_backup_manifest_structure(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            client = self._make_client_with_mock_request(tmp)
            backup_out = tmp / "backups"

            def fake_request(method, path, body=None):
                return [{"id": 1}, {"id": 2}] if "proxy-hosts" in path else []

            client.request = fake_request
            out = client.backup(backup_dir=backup_out)

            manifest = json.loads((out / "manifest.json").read_text())
            self.assertIn("backup_timestamp", manifest)
            self.assertIn("items", manifest)

    def test_backup_json_files_chmod_600(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            client = self._make_client_with_mock_request(tmp)
            backup_out = tmp / "backups"

            def fake_request(method, path, body=None):
                return []

            client.request = fake_request
            out = client.backup(backup_dir=backup_out)

            for f in out.iterdir():
                mode = oct(f.stat().st_mode)[-3:]
                self.assertEqual(mode, "600", f"{f} should be chmod 600, got {mode}")

    def test_backup_partial_failure_continues(self):
        """If one endpoint fails, backup should still write the others."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            client = self._make_client_with_mock_request(tmp)
            backup_out = tmp / "backups"

            call_count = [0]

            def fake_request(method, path, body=None):
                call_count[0] += 1
                if "access-lists" in path:
                    npm_api._die("Simulated API failure for access-lists")
                return []

            client.request = fake_request
            # Should not raise even though one endpoint fails
            out = client.backup(backup_dir=backup_out)
            self.assertTrue(out.exists())
            # Other files should still be written
            self.assertTrue((out / "proxy_hosts.json").exists())

    def test_backup_dir_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            client = self._make_client_with_mock_request(tmp)
            backup_out = tmp / "backups"

            def fake_request(method, path, body=None):
                return []

            client.request = fake_request
            out = client.backup(backup_dir=backup_out)
            mode = oct(out.stat().st_mode)[-3:]
            self.assertEqual(mode, "700")


# ---------------------------------------------------------------------------
# HTTP error path (mocked urllib)
# ---------------------------------------------------------------------------

class TestHTTPErrorHandling(unittest.TestCase):

    def _make_client(self, tmp: Path) -> npm_api.NPMClient:
        conf = make_conf(tmp)
        cfg = npm_api.Config(conf)
        client = npm_api.NPMClient(cfg)
        client._token = "faketoken"
        return client

    def test_http_error_dies_with_message(self):
        """HTTP 4xx/5xx from NPM raises SystemExit with the structured error message."""
        import requests as req_lib
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            # Build a mock response that raise_for_status() will raise HTTPError on
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.json.return_value = {"error": {"message": "Host not found"}}
            mock_resp.text = json.dumps({"error": {"message": "Host not found"}})
            http_error = req_lib.HTTPError(response=mock_resp)
            mock_resp.raise_for_status.side_effect = http_error

            with patch.object(client._session, "request", return_value=mock_resp):
                with self.assertRaises(SystemExit):
                    client._raw_request("GET", "/nginx/proxy-hosts/999", auth_token="faketoken")

    def test_network_error_dies_with_message(self):
        """Connection-level errors (unreachable host) raise SystemExit."""
        import requests as req_lib
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            with patch.object(
                client._session, "request",
                side_effect=req_lib.ConnectionError("Connection refused"),
            ):
                with self.assertRaises(SystemExit):
                    client._raw_request("GET", "/nginx/proxy-hosts", auth_token="faketoken")

    def test_invalid_json_response_dies(self):
        """A non-JSON body from a 2xx response raises SystemExit."""
        import requests as req_lib
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.content = b"not json at all {"
            mock_resp.text = "not json at all {"
            mock_resp.json.side_effect = req_lib.exceptions.JSONDecodeError("err", "doc", 0)

            with patch.object(client._session, "request", return_value=mock_resp):
                with self.assertRaises(SystemExit):
                    client._raw_request("GET", "/nginx/proxy-hosts", auth_token="faketoken")

    def test_empty_response_returns_empty_dict(self):
        """Empty body (e.g. DELETE 204) returns {}."""
        with tempfile.TemporaryDirectory() as td:
            client = self._make_client(Path(td))
            mock_resp = MagicMock()
            mock_resp.status_code = 204
            mock_resp.raise_for_status.return_value = None
            mock_resp.content = b""

            with patch.object(client._session, "request", return_value=mock_resp):
                result = client._raw_request("DELETE", "/nginx/proxy-hosts/1", auth_token="faketoken")
                self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# Smoke test: --help exits 0 (the canonical sandbox-tester check)
# ---------------------------------------------------------------------------

class TestHelp(unittest.TestCase):

    def test_help_exits_zero(self):
        """--help must exit 0 (argparse default)."""
        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stdout", new_callable=StringIO):
                npm_api._build_parser().parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
