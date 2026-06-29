# Sentinel API Reference (v2026.06.024)

Complete API documentation for plugins, agents, and external integrations.

---

## Authentication

Three authentication methods are supported:

| Method | Header | When to use |
|---|---|---|
| Session cookie | `Cookie: session=...` | Web browser, obtained via `POST /api/login` |
| Bearer token | `Authorization: Bearer <api_key>` | External apps, agents, scripts |
| Basic Auth | `Authorization: Basic base64(user:pass)` | Legacy — agent ingest only |

API keys are created by a `superadmin` in Settings → REST API Keys. Each key carries fine-grained scopes (legacy `read`/`write`/`admin` keys remain valid):

| Scope | Permissions |
|---|---|
| `read:issues` | GET endpoints — issues, agents, analytics, topology |
| `write:actions` | POST — agent ingest, approve/reject actions, create issues |
| `admin:users` | Everything including patterns, reload, user/key management |

**CSRF:** browser-session POST/PUT/DELETE requests require the `X-CSRF-Token` header (the web UI adds it automatically via a global `fetch` wrapper). Bearer-token calls are exempt.

**2FA:** if TOTP is enrolled for the user, `POST /api/login` is followed by a second step with the 6-digit code. Manage via `/api/2fa/status|setup|enable|disable`.

**Brute-force protection:** 5 failed logins → IP banned 300 s. `/api/analyze/*` endpoints are rate-limited to 10 req/min per IP.

---

## Plugin API (internal — `api.py`)

Used by detector plugins running inside the Sentinel process.

### `report_problem(key, data)`

Create or update an incident. Same key = update `last_seen` and reset `missing_count`.

```python
api.report_problem("DISK_FULL|proxmox01|/data", {
    "status": "active",
    "last_line": "Disk /data 92% full",
    "channel_type": "infra",       # infra | security | agents | root
    "severity": "CRITICAL",        # INFO | WARNING | CRITICAL
    "host": "proxmox01",
    "cluster": "proxmox01",
    "log_file": "/var/log/sentinel/logs/capacity.log",
    "last_seen": datetime.now(timezone.utc).isoformat(),
    "missing_count": 0
})
```

### `resolve_problem(key)`

Close an incident. Emits a WebSocket `resolve` event to all connected clients.

```python
api.resolve_problem("DISK_FULL|proxmox01|/data")
```

### `get_problem(key) → dict | None`

Return the current DB row for a key, or `None` if it doesn't exist.

### `enqueue_ai_task(prompt, channel)`

Push a task to the AI worker queue. Non-blocking.

```python
api.enqueue_ai_task(
    f"Analyse this SSH attack: {log_line}",
    channel="security"
)
```

### `save_telemetry_snapshot(metric, value, host)`

Write a time-series data point. Writes are buffered and flushed in batches (and on SIGTERM).

```python
api.save_telemetry_snapshot("cpu_usage", 94.2, "hpc-node-01")
```

### `get_infrastructure_label(file_path) → str`

Extract the `SERVER: <hostname>` context injected by Overhealth, or derive from file path.

### `add_root_audit(server, ip)`

Idempotent root-session audit entry (one active record per server+ip) with reverse DNS lookup.

### `notifier.send_notification(title, message, severity, channel)`

Standalone fan-out to all enabled outbound channels with retry queue and per-severity throttling. See [Programmer Documentation](./sentinel/programming_documentation.md).

---

## REST API (HTTP)

Base URL: `http://<host>:5050`

### Authentication

```http
POST /api/login
Content-Type: application/json

{"username": "admin", "password": "secret"}
```

Response sets `Set-Cookie: session=...` (HMAC-signed; absolute session timeout 12 h). If the account has TOTP enrolled, the response requests a second step with the 6-digit code.

### 2FA / TOTP

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/2fa/status` | session | Enrollment status for current user |
| POST | `/api/2fa/setup` | session | Generate secret + QR code (base64 PNG) |
| POST | `/api/2fa/enable` | session | Confirm with one TOTP code |
| POST | `/api/2fa/disable` | session/admin | Disable (admin can disable for any user) |

---

### Issues

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/issues` | read | Active incidents as JSON array (incl. `plugin_name`) |
| GET | `/api/v1/issues/<key>` | read | Single incident detail |
| DELETE | `/api/v1/issues/<key>` | admin | Hard delete incident |
| POST | `/api/v1/issues/<key>/acknowledge` | admin | Acknowledge (→ yellow badge) |
| POST | `/api/v1/issues/<key>/tag` | admin | `{"tag": "storage"}` — add tag |
| DELETE | `/api/v1/issues/<key>/tag/<tag>` | admin | Remove tag |
| POST | `/api/v1/issues/<key>/comment` | admin | Add timeline comment |
| GET | `/api/v1/issues/<key>/history` | read | Timeline events |
| GET | `/api/issues/<key>/markdown` | read | Issue rendered as Markdown |
| POST | `/api/issues/<key>/postmortem` | read | AI-generated Markdown postmortem |
| POST | `/api/v1/issues/batch_analyse` | admin | Batch AI analysis (up to 50) |
| POST | `/api/analyze/auto_clusters` | read | Algorithmic clustering + optional AI root-cause naming |

---

### Agents

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/agent/ingest` | write | Agent telemetry push (rate-limited; `metrics` checked against per-agent thresholds) |
| POST | `/api/v1/ingest/bulk` | write | Array of alerts in one HTTP request |
| GET | `/api/v1/agents` | read | List registered agents with status |
| GET | `/api/v1/agents/<hostname>` | read | Agent detail (issues, metrics, version) |
| POST | `/api/v1/agents/register` | admin | Register new agent, returns token (+ QR payload) |
| DELETE | `/api/v1/agents/<hostname>` | admin | Unregister agent |
| POST | `/api/agents/rotate_all_tokens` | superadmin | Bulk token rotation |
| GET | `/api/agents/<hostname>/health_score` | read | Composite health 0–100 + grade A–D |
| POST | `/api/agents/<hostname>/packages` | admin | Package inventory via SSH (`dpkg`/`rpm`, filter param) |
| GET | `/api/agents/<hostname>/cve_scan` | admin | Pending security updates via SSH |
| GET | `/api/agents/<hostname>/hw_metrics` | admin | net / GPU / SMART / UPS via SSH |
| GET | `/api/agents/<hostname>/scheduled_actions` | read | Planned actions for this host |
| GET/POST/DELETE | `/api/agents/<hostname>/ssh_keys` | admin | known_hosts view / rescan / delete |

#### Agent ingest payload

```http
POST /api/v1/agent/ingest
Authorization: Bearer <agent_token>
Content-Type: application/json

{
  "hostname": "hpc-node-04",
  "version": "a3f8c12",
  "channel": "agents",
  "ip_addresses": ["10.0.0.4"],
  "timestamp": "2026-06-02T18:42:00+02:00",
  "data": {
    "cpu": 94.2,
    "message": "CPU critical: 94.2%",
    "severity": "CRITICAL"
  },
  "metrics": { "cpu_pct": 94.2, "ram_pct": 61.0, "disk_pct": 72.5 }
}
```

The optional `metrics` object is evaluated against `agent_thresholds` rules — issues are created on breach and auto-resolved on recovery.

---

### Autofix Actions & SSH

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/actions` | read | List pending/recent actions |
| POST | `/api/v1/actions/<id>/approve` | admin | Approve and SSH-execute |
| POST | `/api/v1/actions/<id>/reject` | admin | Reject proposal |
| GET | `/api/v1/actions/<id>/output` | read | Stream execution output (SSE) |
| GET | `/api/v1/actions/<id>/audit` | read | Action lifecycle audit log |
| POST | `/api/ssh/batch` | admin | One allowlisted command on ≤ 50 hosts in parallel (15 s per-host timeout) |
| POST | `/api/ansible/run` | admin | Validated `ansible-playbook` run, streamed output |

---

### Analytics & Reports

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/analytics/resolution_time` | read | SLA — average resolution time per plugin |
| GET | `/api/analytics/flapping` | read | Most frequently re-appearing issues |
| GET | `/api/analytics/alert_fatigue` | read | False positive stats per plugin |
| GET | `/api/analytics/forecast` | read | 7-day linear-regression issue forecast |
| GET | `/api/analytics/changes_since_login` | read | New/resolved issue counts since last session |
| GET | `/api/predictions/capacity` | read | TTC (time-to-full) for disk/RAM |
| POST | `/api/reports/capacity_plan` | read | AI capacity plan (HOST/PROBLEM/RECOMMENDATION/PRIORITY) |

---

### System, Configuration & Admin

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | — | `{"status": "ok"}` — used by watchdog |
| GET | `/healthz` | — | K8s/UptimeKuma JSON probe — DB check, 503 on failure |
| GET | `/status` | — | Public status dashboard (HTML): CPU/RAM/Disk telemetry, anonymized recent incidents, online/offline agent table, infra/agent/security category breakdown |
| GET | `/api/status` | read | Detailed system status (DB size, queue depth, AI latency) |
| POST | `/api/plugins/reload` | admin | Hot-reload all plugins |
| GET | `/api/patterns` | read | List custom detection patterns |
| POST | `/api/patterns` | admin | Add pattern |
| POST | `/api/patterns/suggest` | admin | AI regex suggestions from historical issues |
| PUT | `/api/patterns/<id>` | admin | Update pattern |
| DELETE | `/api/patterns/<id>` | admin | Delete pattern |
| POST | `/api/apikeys` | superadmin | Create API key `{name, scope}` |
| DELETE | `/api/apikeys/<id>` | superadmin | Revoke API key |
| POST | `/api/config/hash_password` | superadmin | Generate bcrypt hash for config.yaml |
| GET | `/api/config/view` | superadmin | Config with secrets masked as `***` |
| GET | `/api/config/history/diff?from=X&to=Y` | superadmin | Diff two config snapshots |
| POST | `/api/config/restore` | superadmin | Restore config (auto-backup first, 10 kept) |
| GET | `/api/admin/backup/download` | superadmin | Full backup as tar.gz |
| POST | `/api/admin/backup/s3` | superadmin | Upload backup to S3/MinIO |
| GET/POST | `/api/admin/log_level` | superadmin | Get/set log level at runtime |
| GET | `/api/admin/audit_trail` | superadmin | Config + SSH + action audit viewer |
| GET | `/api/admin/security_check` | superadmin | Security headers grade A/B/C/D |
| GET | `/api/admin/db_stats` | superadmin | DB size + record counts |
| POST | `/api/admin/aggregate_telemetry` | superadmin | Aggregate old telemetry |
| POST | `/api/admin/validate_url` | superadmin | URL validation (SSRF guard — rejects private ranges) |
| GET | `/api/timezone/info` | read | Configured display timezone |
| GET | `/api/timezone/convert` | read | Convert timestamp to display TZ |
| GET | `/api/kb/reindex` | admin | Trigger RAG knowledge base reindex |

---

### Topology

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/topology/data` | read | Nodes + edges for force-directed graph |

---

### Export, Inbound Webhooks & Integrations

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/export/incidents` | read | CSV export of incidents |
| GET | `/api/export/telemetry` | read | CSV export of telemetry data |
| POST | `/api/inbound/grafana` | write | Grafana webhook (legacy + unified alerting) |
| POST | `/api/inbound/alertmanager` | write | Prometheus Alertmanager webhook |
| POST | `/api/inbound/zabbix` | write | Zabbix Media Type flat JSON |
| GET/POST | `/api/integrations/<name>/status\|toggle\|save\|test` | admin | Per-integration config (Teams, Slack, Discord, Telegram, Opsgenie, ntfy, Gotify, SMTP, Matrix, PagerDuty, HA, MQTT) |
| GET | `/api/channels/notify` | admin | Per-channel notification toggles |
| POST | `/api/channels/<ch>/notify/toggle` | admin | Toggle channel notifications |
| GET | `/metrics` | scrape_token | Prometheus metrics endpoint |

Inbound webhook auth supports Bearer token **or** HMAC `X-Hub-Signature-256` + `X-Webhook-Timestamp` (replay protection).

**Outbound lifecycle webhooks** fire on issue CREATED / ACKNOWLEDGED / RESOLVED; critical issues can sync to Gitea and annotate Grafana dashboards.

#### Prometheus metrics

```
# GAUGE: active incidents per channel
sentinel_issues_total{channel="infra"} 3
sentinel_issues_total{channel="security"} 1

# GAUGE: agents online
sentinel_agents_online 12

# GAUGE: AI worker queue depth
sentinel_queue_depth 2

# GAUGE: AI response latency (seconds)
sentinel_ai_latency_seconds 1.24

# GAUGE: log parser throughput
sentinel_lines_parsed_per_min 1840
```

Self-metrics can also be **pushed** to a Prometheus pushgateway (`prometheus.pushgateway_url`).

---

### API Documentation (auto-generated)

| Path | Description |
|---|---|
| `GET /api/docs` | Swagger UI (interactive browser) |
| `GET /api/openapi.json` | OpenAPI 3.0 JSON spec |

---

## WebSocket Events (Socket.IO)

Connect to `ws://<host>:5050/socket.io/`. Transport order is `['polling', 'websocket']` with upgrade — works behind any reverse proxy. Server-side the frontend queue is bounded (500, drop-oldest) and duplicate messages within 1 s are deduplicated.

| Event (server → client) | Payload | Description |
|---|---|---|
| `new_issue` | `{key, severity, channel, host, message}` | New incident created |
| `resolve` | `{key}` | Incident resolved (auto or manual) |
| `new_action` | `{id, command, risk_score}` | New Autofix pending |
| `action_result` | `{id, status, stdout}` | Autofix completed |
| `agent_status` | `{hostname, status}` | Agent online/offline transition |
| `telemetry_update` | `{metric, value, host}` | Telemetry data point |
| `chat_message` | `{user, text, device_id}` | P2P admin chat message |

| Event (client → server) | Payload | Description |
|---|---|---|
| `chat` | `{message}` | Send chat query to AI |
| `ping_presence` | `{device_id, user}` | Mobile heartbeat (every 60 s) |
