# Proxy host default template

Full parameter reference for NPM proxy host creation.

| Parameter | Description | Default |
|-----------|-------------|---------|
| domain_names | Public hostname(s) for the service | (required) |
| forward_host | Backend hostname or container name | (required) |
| forward_port | Port the backend listens on internally | (required) |
| forward_scheme | Protocol NPM uses to reach backend | `http` |
| ssl_forced | Redirect HTTP to HTTPS | `true` |
| http2_support | Enable HTTP/2 | `true` |
| hsts_enabled | Send HSTS header | `false` |
| caching_enabled | NPM-level caching | `false` |
| block_exploits | Block common exploit patterns | `true` |
| allow_websocket_upgrade | Pass WebSocket upgrade headers | `false` |
| access_list_id | NPM access list to apply | `0` (none) |
| advanced_config | Raw nginx config block | (empty) |
| locations | Custom location blocks | `[]` |
| enabled | Host is active | `true` |

## Notes

- Use `forward_scheme: https` only when the container's internal port speaks TLS.
- Enable `allow_websocket_upgrade` for apps that use WebSockets (chat, live dashboards, dev proxies).
- Use `advanced_config` only for nginx-level tuning (e.g. `client_max_body_size 1000M;` for large uploads).
- Always use the Docker container name as `forward_host` for containers on the shared NPM network. Never use container IPs (they change on restart).
