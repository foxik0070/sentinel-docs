# Sentinel Commander — Programmer Documentation (v2026.06.024)

Intended for developers and DevOps engineers writing custom detection plugins, integrating Sentinel with external tools, or modifying the system core.

---

## Plugin Architecture

Sentinel loads plugins dynamically from the `plugins/` directory. Every plugin must inherit from `BaseDetector`.

```
Log file (disk)
    │ inotify on_modified / on_moved
    ▼
watcher.py ──lines──▶ plugin_manager.py ──match(regex)──▶ MyDetector.process(lines)
                                                                │
                                              api.report_problem(key, payload)
                                                                │
                                                            state.py (SQLite)
```

### Writing a Custom Detector

```python
# plugins/my_detector.py
from datetime import datetime, timezone
from sentinel import api

class Detector(api.BaseDetector):
    def __init__(self, name, config_params=None):
        super().__init__(name, config_params)
        self.threshold = self.config_params.get("threshold", 3)

    def process(self, lines, file_path):
        infra_label = api.get_infrastructure_label(file_path)

        for line in lines:
            if "MY_CRITICAL_EVENT" not in line:
                continue

            key = f"MY_EVENT|{infra_label}|{hash(line)}"

            api.report_problem(key, {
                "status": "active",
                "last_line": line.strip(),
                "channel_type": "infra",
                "severity": "CRITICAL",
                "host": infra_label,
                "cluster": infra_label,
                "log_file": file_path,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "missing_count": 0
            })

            # Optional: queue AI analysis
            api.enqueue_ai_task(f"Analyse: {line.strip()}", channel="infra")
```

Register in `config.yaml`:

```yaml
detectors:
  my_detector:
    enabled: true
    file_mask: "myapp.log"
    threshold: 5
    notify: true        # per-detector notification toggle
```

---

## Core API (`api.py`)

| Method | Description |
|---|---|
| `report_problem(key, data)` | Create or update an incident. Same key = update `last_seen` + `missing_count`. |
| `resolve_problem(key)` | Close an incident (auto-heal). Triggers WebSocket `resolve` event. |
| `get_problem(key)` | Return the current DB row for a key, or `None`. |
| `enqueue_ai_task(prompt, channel)` | Push a task to the AI worker queue. Non-blocking. |
| `save_telemetry_snapshot(metric, value, host)` | Write a time-series data point (buffered/batched). |
| `get_infrastructure_label(file_path)` | Extract `SERVER: <hostname>` context from the log line prefix. |
| `add_root_audit(server, ip)` | Idempotent root-session audit entry with reverse DNS. |
| `notify_teams(message, channel)` | Send a Teams webhook message directly (bypass queue). |

### Notifier (`notifier.py`)

Outbound notifications were extracted from `ChatService` into a standalone module:

```python
from sentinel.notifier import send_notification
send_notification(title, message, severity="critical", channel="security")
```

- Fan-out to all enabled channels: Teams, Slack, PagerDuty, Discord, Telegram, Opsgenie, ntfy.sh, Gotify, SMTP, Matrix, Home Assistant, MQTT, generic Webhook
- Each channel runs through `_with_retry()` — failures enter a retry queue (deque maxlen 200) retried by the `NotifierRetry` thread with 30 s/120 s/300 s backoff (max 3 attempts)
- Throttle per severity: `critical/security/root` 15 min · `high` 1 h · `medium/low/agent/infra` 4 h
- Respects per-detector (`notify:` in YAML) and per-channel toggles
- Instance name prefixed to all titles: `[Instance] CHANNEL alert`

### Scheduler (`scheduler.py`)

Background maintenance loop extracted from `ChatService`, with three tiers — minute (FIM, heartbeat URLs, self-metrics), hourly (session GC, geo-IP cache, joke log), nightly (prune, VACUUM, weekly digest).

---

## Plugin Hot-Reload

Plugins can be reloaded without restarting the daemon:

**From the Web UI:** Settings → Plugin hot-reload button
**Via API:** `POST /api/plugins/reload` (requires `superadmin` API key or session)
**Via signal:** `kill -HUP <pid>` — reloads config + watcher patterns + plugins

The Plugin Manager uses `importlib.util` to load each module into an isolated `sys.modules` namespace, compiles regex patterns, and instantiates new detector objects.

---

## Pattern Editor (UI-driven patterns)

Custom patterns defined in the UI are stored in the `custom_patterns` table and loaded by the Plugin Manager alongside Python plugins:

```sql
CREATE TABLE custom_patterns (
    id INTEGER PRIMARY KEY,
    name TEXT,
    regex TEXT,
    file_mask TEXT,
    channel TEXT,
    severity TEXT,
    enabled INTEGER DEFAULT 1
);
```

These patterns work as lightweight inline detectors — no Python code required. Available via `GET /api/patterns` and `POST /api/patterns`. The editor includes a live regex tester and **AI pattern suggestions** (`/api/patterns/suggest`) generated from historical issues.

---

## REST API (External Integration)

All endpoints require authentication. Methods accepting JSON need `Content-Type: application/json`. CSRF token (`X-CSRF-Token`) is required for browser-session POST/PUT/DELETE; Bearer-token API calls are exempt.

### Authentication options

1. **Session cookie** — obtained via `POST /api/login` (+ optional TOTP step)
2. **Bearer token** — `Authorization: Bearer <api_key>` with fine-grained scopes: `read:issues`, `write:actions`, `admin:users`
3. **Basic Auth** — `Authorization: Basic base64(user:pass)` (agent ingest only)

### Key endpoints

| Method | Path | Auth scope | Description |
|---|---|---|---|
| POST | `/api/login` | — | `{username, password}` → session cookie (TOTP step if enrolled) |
| GET/POST | `/api/2fa/status\|setup\|enable\|disable` | session | TOTP enrollment lifecycle |
| GET | `/api/v1/issues` | read:issues | Active incidents as JSON (incl. `plugin_name`) |
| POST | `/api/v1/agent/ingest` | write | Agent telemetry push (+ `metrics` → threshold check) |
| POST | `/api/v1/ingest/bulk` | write | Array of alerts in one request |
| GET | `/api/issues/<key>/markdown` | read:issues | Issue rendered as Markdown |
| POST | `/api/issues/<key>/postmortem` | read:issues | AI-generated Markdown postmortem |
| GET | `/api/v1/actions` | read:issues | List pending actions |
| POST | `/api/v1/actions/<id>/approve` | write:actions | Approve and SSH-execute |
| POST | `/api/v1/actions/<id>/reject` | write:actions | Reject proposal |
| GET | `/api/v1/actions/<id>/output` | read:issues | Stream execution output (SSE) |
| POST | `/api/ssh/batch` | admin | Parallel SSH on up to 50 hosts |
| POST | `/api/agents/<hostname>/packages` | admin | Package inventory via SSH |
| GET | `/api/agents/<hostname>/cve_scan` | admin | Pending security updates |
| GET | `/api/agents/<hostname>/hw_metrics` | admin | net/GPU/SMART/UPS via SSH |
| GET | `/api/agents/<hostname>/health_score` | read:issues | Composite 0–100 + A–D grade |
| GET/POST/DELETE | `/api/agents/<hostname>/ssh_keys` | admin | known_hosts management |
| POST | `/api/agents/rotate_all_tokens` | superadmin | Bulk agent token rotation |
| GET | `/api/analytics/resolution_time` | read:issues | SLA stats |
| GET | `/api/analytics/flapping` | read:issues | Most-repeating issues |
| GET | `/api/analytics/alert_fatigue` | read:issues | False positive stats per plugin |
| GET | `/api/analytics/forecast` | read:issues | 7-day linear-regression forecast |
| POST | `/api/analyze/auto_clusters` | read:issues | Algorithmic clustering + AI root cause |
| POST | `/api/reports/capacity_plan` | read:issues | AI capacity planning |
| GET | `/api/predictions/capacity` | read:issues | TTC for disk/RAM |
| POST | `/api/ansible/run` | admin | Validated playbook run with streamed output |
| GET | `/api/topology/data` | read:issues | Agent topology nodes + edges |
| POST | `/api/plugins/reload` | admin | Hot-reload all plugins |
| GET/POST | `/api/patterns` | read/admin | Custom patterns CRUD |
| POST | `/api/patterns/suggest` | admin | AI regex pattern suggestions |
| POST | `/api/apikeys` | superadmin | Create API key (`{name, scope}`) |
| DELETE | `/api/apikeys/<id>` | superadmin | Revoke API key |
| POST | `/api/config/hash_password` | superadmin | Generate bcrypt hash |
| GET | `/api/config/history/diff?from=X&to=Y` | superadmin | Diff two config snapshots |
| GET | `/api/admin/backup/download` | superadmin | tar.gz backup |
| POST | `/api/admin/backup/s3` | superadmin | Upload backup to S3/MinIO |
| GET/POST | `/api/admin/log_level` | superadmin | Runtime log level |
| GET | `/api/admin/audit_trail` | superadmin | Config + SSH + action audit |
| GET | `/api/admin/security_check` | superadmin | Security grade A/B/C/D |
| GET | `/api/admin/db_stats` | superadmin | DB size + record counts |
| GET | `/api/timezone/info` · `/api/timezone/convert` | read | Display timezone helpers |
| GET | `/metrics` | scrape_token | Prometheus metrics endpoint |
| GET | `/healthz` | — | K8s/UptimeKuma probe (503 on DB failure) |
| GET | `/api/docs` | — | Swagger UI |
| GET | `/api/openapi.json` | — | OpenAPI 3.0 spec |
| GET | `/api/kb/reindex` | admin | Trigger RAG reindex |

---

## Inbound Webhooks (Grafana / Alertmanager / Zabbix)

Sentinel accepts inbound webhooks from external monitoring tools on three dedicated endpoints:

| Endpoint | Format |
|---|---|
| `POST /api/inbound/grafana` | Grafana legacy **and** unified alerting payloads |
| `POST /api/inbound/alertmanager` | Prometheus Alertmanager webhook format |
| `POST /api/inbound/zabbix` | Zabbix Media Type flat JSON |

```http
POST /api/inbound/grafana
Authorization: Bearer <api_key>
Content-Type: application/json

{ "alerts": [ { "labels": {"alertname": "DiskFull", "instance": "hpc-node-01"},
                "annotations": {"summary": "disk >90%"}, "status": "firing" } ] }
```

The payload is normalised and injected into the standard issue pipeline (same as a detector `report_problem()` call). Webhook auth supports both Bearer token and HMAC `X-Hub-Signature-256` with `X-Webhook-Timestamp` replay protection.

**Outbound lifecycle webhooks:** configure URLs to be called on issue `CREATED` / `ACKNOWLEDGED` / `RESOLVED`; critical issues can additionally be synced to **Gitea** (`GITEA_URL/TOKEN/REPO`) and annotated in **Grafana** (`grafana_annotations.url/api_key`).

---

## Database Schema — Key Tables

### `problems`

```sql
CREATE TABLE problems (
    key          TEXT PRIMARY KEY,
    status       TEXT,           -- active | acknowledged | validating | resolved
    severity     TEXT,           -- critical | high | medium | low
    channel_type TEXT,
    host         TEXT,
    last_line    TEXT,
    last_seen    TEXT,
    missing_count INTEGER DEFAULT 0,
    acknowledged_by TEXT,
    acknowledged_at TEXT,
    depends_on   TEXT            -- JSON list of dependent issue keys
);
```

### `actions` (Autofix)

```sql
CREATE TABLE actions (
    id           INTEGER PRIMARY KEY,
    command      TEXT,
    status       TEXT,   -- pending | running | completed | failed | rejected
    risk_score   INTEGER,
    risk_reasons TEXT,   -- JSON
    mode         TEXT,   -- dry_run | real
    dry_run_output TEXT,
    actor        TEXT,
    created_at   TEXT,
    executed_at  TEXT,
    stdout       TEXT,
    stderr       TEXT
);
```

### `issue_history` (archive)

`_archive_problem()` copies `first_seen` from `problems`, enabling resolution-time analytics (`/api/analytics/resolution_time`). Pruned after 90 days by the scheduler.

---

## RAG Knowledge Base (rag.py + build_kb.py)

### Adding documents

```bash
# Rebuild from /opt/Sentinel/knowledge_base/ — interactive menu, PDF/DOCX/MD support
python3 build_kb.py

# Supported formats: .md .txt .pdf .docx .csv
# Or upload directly via the Web UI (Settings → Knowledge Base)
```

### Query flow

1. User query → `RAGEngine.search(query, top_k=3)`
2. Vectorise query with `nomic-embed-text`
3. HNSW nearest-neighbour search in ChromaDB
4. Top-K chunks injected into system prompt
5. If ChromaDB unavailable → BM25 TF×IDF fallback over tokenised text blocks

---

## AI Worker Pool (ollama_service.py)

```
task_queue (DB)
      │
  ┌───┴───────┐
  │ Worker-0  │ ← fetches task, locks worker_id
  │ Worker-1  │
  │ Worker-N  │ ← configurable via WORKER_THREADS
  └───────────┘
      │
  Ollama API
  POST /v1/chat/completions   (timeout 90 s)
      │
  Failover: 400 error → legacy /api/chat format
      │
  Response → append to issue in DB
           → emit WebSocket event
```

Workers rotate indefinitely until `state.shutdown_event.is_set()`. Tasks are never automatically requeued on error (prevents infinite retry loops on bad input).

> **Concurrency rule:** never acquire `llm_semaphore` around a call into `execute_ollama()` — the function takes it internally; a re-entrant acquire deadlocks the whole AI pipeline permanently.

---

## Development Workflow

```bash
make lint        # ruff + ESLint
make test        # pytest — 181 tests
make ci          # lint + test (same as CI)
make build       # minify JS (.min.js are not in git)
```

- CI runs in Gitea Actions (`.gitea/workflows/ci.yml`): pytest + `node --check` + build
- A `pre-push` git hook runs the JS check + pytest locally
- See `CONTRIBUTING.md` for the architecture diagram, dev workflow, and security rules (e.g. every new endpoint needs auth + input validation + a route test)
