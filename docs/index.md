# Sentinel Commander — Documentation (v2026.06.024)

```
                   ##
               ++########++
              ++++###+++++++
             +++++++++++-++-.
            ++++++#++++++-+-
             ++######+++++--
             +++  ####+  -+-
              ++++######++-
              ++++#######+-#
               ++++######++-+.-+
              ++++++###+++##+---++#
            +++++++++###+#######++++++++
         -+++++++++++###+#####+#+++++----..-
      ++-++++++++#######+######++++++++--..  .
     ---++++##+++#####++####++++#++++---.....
    --+++++############++###++++#+++---........
   --++++++##++##########++++++++++----.........
   --+++++#####++#####+#+++++++++++++-.-.........
   --++++#####+########++++++-+++++-++--------.-..
   ++++##########+####++++++-+++++++-+++---------.

        S E N T I N E L   C O M M A N D E R
                    v2026.06.024
```

**Hybrid AI Log Monitor & Analyzer for HPC & Enterprise Linux Infrastructure**

---

## Quick Navigation

- **[Deployment Guide](./DEPLOYMENT.md)** — Production deployment of the entire system
- **[API Reference](./API.md)** — Plugin and integration API
- **[Troubleshooting](./TROUBLESHOOTING.md)** — Common issues and solutions

---

## What is Sentinel?

Sentinel Commander is an advanced hybrid monitoring system with artificial intelligence designed for HPC (High-Performance Computing) and enterprise Linux infrastructure. It combines a **Pull** approach (inotify log tailing) with a **Push** approach (remote Python agents POSTing telemetry). The key feature is integration with Hailo AI HAT 2+ NPU (hailo-ollama), local/external Ollama LLM, and ChromaDB (RAG).

Since v2026.06.005 the project went through 17 release iterations focused on **security hardening** (2FA/TOTP, bcrypt, CSRF, API scopes), **enterprise integrations** (Discord, Telegram, Opsgenie, Zabbix, Gitea, Grafana, S3), **analytics** (health score, issue forecast, SLA reports) and **engineering quality** (CI pipeline, 181 automated tests, extracted `notifier.py`/`scheduler.py` modules).

---

## What's New in v2026.06.024 (since v2026.06.005)

### Latest in v2026.06.023 → v2026.06.024

| Feature | Detail |
|---|---|
| **Public `/status` dashboard** | Auth-free status page: CPU/RAM/Disk telemetry, anonymized recent incidents, online/offline agent table, infra/agent/security category breakdown, fully responsive grid |
| **Mobile responsivity** | Issue cards switch from inline styles to CSS classes (`issue-row-inner`/`issue-content-area`/`issue-actions`); secondary actions collapse under 480 px; modal overlay `flex-start` + `overflow-y:auto` so dialogs are always reachable; header bar no longer overflows |
| **CSRF session fix** | CSRF token now seeded into the session at render time — fixes chat returning 403 on mobile and desktop |
| **Category cleanup** | `UNKNOWN` category normalized to `OSTATNÍ` / Other in issue cards and groups (DB migration of existing records) |

### Security Hardening

| Feature | Detail |
|---|---|
| **2FA / TOTP** | Full stack: pyotp (RFC 6238), QR code enrollment (Google Authenticator / Authy), two-step login flow, `user_totp` DB table, admin can disable 2FA per user |
| **bcrypt password hashing** | `web.password_hash: "$2b$12$..."` takes priority over plaintext; "Hash password" button in Settings generates the hash; viewer password analogous |
| **CSRF protection** | Token in session + SameSite=Strict cookie + global `fetch` wrapper adds `X-CSRF-Token` to every POST/PUT/DELETE |
| **Brute-force protection** | Form login + Basic auth: IP ban after 5 failed attempts for 300 s; auto-register rate limit 10/min per IP |
| **XSS hardening** | All AI replies escaped via `html.escape()` before `innerHTML` — log content is attacker-controlled |
| **SSH hardening** | `ssh_utils.py`: `accept-new` + `UserKnownHostsFile` instead of `StrictHostKeyChecking=no`; `ssh-keyscan` on agent registration; known_hosts UI (view / rescan / delete keys) |
| **API key scopes** | Fine-grained: `read:issues`, `write:actions`, `admin:users` — with backwards compatibility |
| **Secrets handling** | `{SECRET:ENV_VAR}` substitution in config.yaml (vars deleted from `os.environ` after use); `/api/config/view` masks password/token/secret/api_key as `***` |
| **Session control** | Absolute 12 h timeout (`security.session_max_hours`), role refresh from DB every 5 min, revoked sessions persisted in DB |
| **Audit trail** | `config_audit` table (who, when, IP, which keys), 403/401 access audit, audit trail viewer in Settings |
| **SSRF + input validation** | `/api/admin/validate_url` rejects private IP ranges; hostname regex validation on all SSH/ingest endpoints; `int_param()` bounds-checking on 20+ endpoints |
| **Security self-check** | `/api/admin/security_check` returns security grade A/B/C/D |

### Notifications & Integrations

| Feature | Detail |
|---|---|
| **Outbound channels** | MS Teams · Slack · PagerDuty · Discord (embeds) · Telegram bot · Opsgenie (Events API v2) · ntfy.sh · Gotify · SMTP e-mail (STARTTLS 587 / SSL 465) · Matrix · Home Assistant · MQTT · generic Webhook (HMAC-SHA256 + replay protection) |
| **Inbound webhooks** | `/api/inbound/grafana` (legacy + unified alerting) · `/api/inbound/alertmanager` (Prometheus AM) · `/api/inbound/zabbix` (Media Type flat JSON) |
| **Reliability** | Retry queue with exponential backoff (30 s/120 s/300 s, max 3 attempts); per-severity throttling (critical/security/root 15 min, high 1 h, medium/low 4 h) |
| **Granularity** | Per-detector 🔔 toggle, per-channel toggle, instance name prefix in all titles (`[Instance] CHANNEL alert`) |
| **Lifecycle webhooks** | Configurable webhooks fired on issue CREATED / ACKNOWLEDGED / RESOLVED |
| **Gitea issue sync** | Critical issues automatically opened in a Gitea repository (`GITEA_URL/TOKEN/REPO`) |
| **Grafana annotations** | `_send_grafana_annotation()` on critical/security alerts |
| **Prometheus** | `GET /metrics` scrape endpoint + pushgateway export of Sentinel self-metrics |

### Analytics & AI

| Feature | Detail |
|---|---|
| **Health score per host** | `/api/agents/<hostname>/health_score` — composite 0–100 with A–D grade |
| **Issue forecast** | `/api/analytics/forecast` — linear regression, 7-day outlook |
| **SLA & fatigue reports** | Resolution-time table, alert-fatigue chart, flapping issues widget, changes-since-login |
| **AI capacity planning** | `/api/reports/capacity_plan` — telemetry aggregated per host, AI returns HOST/PROBLEM/RECOMMENDATION/PRIORITY cards |
| **Auto-clustering** | `/api/analyze/auto_clusters` — groups issues by plugin/host in 30 min windows, AI names the root cause |
| **AI postmortem** | `/api/issues/<key>/postmortem` — AI-generated Markdown incident postmortem |
| **Auto-severity & duplicates** | LLM-assigned severity, automatic duplicate detection |
| **Weekly digest** | Includes flapping issues and average resolution time |

### Agent Fleet Management

| Feature | Detail |
|---|---|
| **Batch SSH** | `POST /api/ssh/batch` — parallel SSH via ThreadPoolExecutor (10 threads, max 50 hosts, 15 s per-host timeout), allowlist checked |
| **Per-agent thresholds** | `check_agent_thresholds()` enforced on every ingest payload; quick-buttons CPU > 90 %, RAM > 90 %, Disk > 85 % |
| **HW metrics over SSH** | net (`/proc/net/dev`), GPU (nvidia-smi/rocm-smi), SMART (smartctl), UPS (apcaccess/upsc) |
| **CVE scanner** | `apt list --upgradable` / `dnf --security check-update` per agent |
| **Package inventory** | `dpkg-query` / `rpm -qa` with live filter in agent detail |
| **QR registration** | Token modal generates QR `{hostname, token, ingest_url}`; one-click token copy; bulk token rotation (`/api/agents/rotate_all_tokens`) |
| **Maintenance windows** | Per-host snooze rules; agent detail shows its own windows |
| **Version drift alert** | Issue raised when an agent registers with a build older than 30 days; offline duration tracked in telemetry |

### Operations & Reliability

| Feature | Detail |
|---|---|
| **Health endpoints** | `/healthz` (Kubernetes/UptimeKuma JSON probe, 503 on DB failure) · redesigned `/status` public page (auto-refresh 30 s) |
| **Config management** | jsonschema validation of critical keys · backup/restore with automatic pre-restore snapshots (10 kept) · snapshot diff endpoint + UI |
| **Hot reload** | SIGHUP reloads config **and** watcher patterns **and** plugins; `/api/admin/log_level` changes log level at runtime |
| **Graceful shutdown** | SIGTERM flushes telemetry buffer + publishes MQTT `sentinel/status: offline` |
| **Backups** | `/api/admin/backup/download` (tar.gz) + `/api/admin/backup/s3` (S3/MinIO upload) |
| **File Integrity Monitoring** | SHA-256 hash of critical files checked every minute → security issue on change |
| **Ansible runner** | `/api/ansible/run` — validated playbook path, streamed output |
| **Synthetic checks** | HTTP health checks (`SYNTHETIC_CHECKS`), heartbeat URL monitoring, SSL certificate expiry (< 14 days → security issue) |
| **Self-monitoring** | RAM/threads/queue/load self-metrics every minute · memory watchdog (RSS > 1.5 GB → warning) · AI queue backlog alert · DB size alert · no-agent alert · startup time profiling |

### Performance

- **Issues cache** with TTL 5 s + double-checked `threading.Lock`; invalidation on write
- **Telemetry write batching** (buffer flushed periodically), dashboard sparklines query cached 5 min
- **Composite DB indexes** (`idx_problems_plugin_ch_ts`, `idx_issue_hist_plugin_ts`, severity + telemetry indexes)
- **WAL tuning** — `wal_autocheckpoint=200`, `synchronous=NORMAL`, explicit checkpoint after prune; VACUUM after >10 k deleted rows; 90-day issue history retention
- **HTTP caching** — ETag + `max-age` + 304 conditional GET for static files; `defer` + `preload` script loading; gzip
- **SocketIO backpressure** — bounded frontend queue (500, drop-oldest); WS message dedup in 1 s window
- **Virtual scroll** — issues paginated by 50 with "Load more"

### UI / UX

- **Runbooks** tab in Tools with CRUD + runbook modal
- **Modern interactive charts** — min/max/avg badges, dashed average line, rich tooltips (dashboard trend, donut with center total, alert timeline, agent sparklines)
- **Issue fullscreen overlay**, inline comments, colored labels, drag & drop tabs, mobile swipe (right = acknowledge, left = delete)
- **Issue copy as Markdown**, bulk CSV export (`Alt+E`), bulk acknowledge (`Alt+A`), chat export to Markdown
- **Accessibility** — ARIA `role="dialog"`, `aria-modal`, `aria-labelledby` on all modals, Escape to close
- **DB management panel** in Settings — size, record counts, "Prune now" and "Aggregate telemetry" buttons
- **Chat** — suggested query chips, LIVE tag (enriches the prompt with active-issue context), Markdown rendering
- **Timezone config** — `DISPLAY_TZ`, `/api/timezone/info`, `/api/timezone/convert`

### Engineering Quality

- **118 automated tests** — route tests, security tests (brute force, scopes, hostname injection, secrets masking), integration tests (full issue lifecycle on a real DB), dashboard benchmark
- **CI pipeline** — Gitea Actions (`pytest` + `node --check` + `make build`), `pre-push` git hook, `make ci`
- **Linting** — ruff (Python), ESLint with `no-redeclare=error` (JS), pinned `requirements.txt`
- **Refactoring** — `notifier.py` (all outbound channels), `scheduler.py` (3-tier maintenance loop) and `ssh_utils.py` extracted from `chat_service.py`
- **CONTRIBUTING.md** — architecture diagram, dev workflow, security rules

---

## Feature Overview

| Area | Capabilities |
|---|---|
| **AI Inference** | Hailo-10H NPU (hailo-ollama) · CPU Ollama · external API · runtime model switch |
| **RAG Knowledge Base** | ChromaDB + nomic-embed-text · BM25 TF×IDF fallback · custom file upload (.md/.txt/.pdf/.docx/.csv) · one-click reindex |
| **Hybrid Telemetry** | Pull (inotify logs) + Push (agents via Bearer token) · multiple IPs per agent · agent version tracking (SHA) |
| **Autofix** | AI proposes fix → admin Approve/Reject → SSH exec on mgmt node · allowed-commands allowlist · autonomous exec |
| **Predictive Analytics** | TTC (Time-To-Critical) for disks · Mann-Kendall trend test · linear regression forecast · capacity planning |
| **Security Profiler** | Brute-force, sudo abuse, CVE scan, unauthorised ports, honeypot, FIM, SSL expiry |
| **Notifications** | 13 outbound channels · 3 inbound webhooks · retry queue · per-severity throttle · per-detector/channel toggles |
| **Prometheus** | `GET /metrics` scrape + pushgateway export; auth via scrape_token |
| **Dashboard** | Stat cards · interactive min/max/avg charts · trend chart · donut · health trend · flapping widget · live clock |
| **Auth** | viewer / admin / superadmin · LDAP (lldap + OpenLDAP) · **2FA/TOTP** · **bcrypt** · rate-limit + IP ban · **CSRF** |
| **Issue UI** | Bulk select · filter · group-collapse · printable report · CSV export · history · suppression rules · tagging · severity · occurrence counter · batch AI analysis · fullscreen · labels · inline comments |
| **Issue Workflow** | `active` → `acknowledged` → `validating` → `resolved` · escalation rules · lifecycle webhooks |
| **Auto-Remediation** | One-shot SSH fix · allowed_commands with `auto_execute` · AUTOFAIL issues · SSH jump host (ProxyJump) · Ansible runner |
| **REST API Keys** | Fine-grained scopes (`read:issues`, `write:actions`, `admin:users`) · SHA-256 hash in DB · UI in Settings |
| **Plugin Hot-Reload** | `POST /api/plugins/reload` · SIGHUP full reload · Pattern Editor with regex tester + AI pattern suggestions |
| **Telemetry** | Anomaly detection (3σ) · fixed thresholds · per-agent thresholds · InfluxDB export · heatmap · health score history |
| **Topology** | Agent topology map · plugin dependency graph · SNMP CDP/LLDP · Canvas force-directed graph |
| **SSH Actions** | Jump host (ProxyJump) · SSH modal (admin+) · streaming output (SSE) · **batch SSH** · known_hosts management |
| **API Docs** | `GET /api/docs` — Swagger UI · `GET /api/openapi.json` — OpenAPI 3.0 spec |
| **Hailo TUI** | `hailo_models.py` — Unicode TUI model manager: htop-style CPU/Mem bars, RX/TX, NPU arch+FW, TPS benchmark |
| **UI i18n** | Czech (default) · English toggle · `localStorage` persistence · timezone display config |
| **Security** | Symlink containment · upload limit (5 MB) · secure_filename · timing-safe token verify · CSP headers · secrets masking · SSRF guard |

---

## Architecture

```
  Log files ──inotify──▶ watcher.py ──▶ plugins[] ──▶ api.report_problem()
  Remote agents ──POST──▶ /api/v1/agent/ingest              │
  Grafana/AM/Zabbix ──POST──▶ /api/inbound/*                │
                                                            ▼
                                                   state.py (SQLite WAL)
                                                            │
                         ┌──────────────────────────────────┤
                         ▼                                  ▼
               ollama_service.py                   Flask + SocketIO :5050
               (AI worker pool)                    (chat_service.py + routes/)
                         │                                  │
         ┌───────────────┼───────────────┐         ┌────────┴────────┐
         ▼               ▼               ▼         ▼                 ▼
  hailo-ollama      Ollama CPU      external   scheduler.py     notifier.py
  (NPU :8000)       (:11434)        API        (maintenance)    (13 channels)
```

### Core modules

| File | Responsibility |
|---|---|
| `chat_service.py` | Flask/SocketIO app factory, RBAC, WebSocket |
| `auth.py` | Authentication, LDAP, 2FA/TOTP, bcrypt, sessions, API key verify |
| `state.py` (`state_base/issues/agents`) | SQLite WAL orchestration — issues, telemetry, agents |
| `watcher.py` | inotify filesystem events, hot config reload, FIM |
| `plugin_manager.py` | Dynamic plugin loading, pattern routing, hot-reload |
| `ollama_service.py` | AI worker thread pool, model switching |
| `rag.py` | ChromaDB, nomic-embed-text, BM25 fallback |
| `actions.py` | Autofix lifecycle — create, approve, reject, SSH exec |
| `notifier.py` | All outbound notifications + retry queue + throttling |
| `scheduler.py` | Background maintenance (minute / hourly / nightly tiers) |
| `ssh_utils.py` | Central SSH security — `build_ssh_cmd()`, host key scanning |
| `analytics.py` | TTC, Mann-Kendall, Z-Score, health score, forecast |
| `topology.py` | Agent topology builder, SNMP CDP/LLDP |
| `routes/` | Flask Blueprints: main, issues, agents, actions, system, export, integrations, chat |

---

## Data Flow

### A. Ingest & Detection

1. Log line written to `/var/log/sentinel/logs/` → inotify event
2. `watcher.py` reads new lines via `mmap`
3. `PluginManager` routes lines to matching detectors by file mask
4. Detector generates unique key (e.g. `DISK_FULL|proxmox01|/data`)
5. State written to `problems` table → task pushed to `task_queue`
6. Push path: agents POST `/api/v1/agent/ingest` (or `/api/v1/ingest/bulk` for batches); `metrics` payload is checked against per-agent thresholds

### B. AI Inference + RAG

1. AI worker fetches task from `task_queue`
2. Loads prompt template by channel (security, clusters, infra, root, icinga)
3. RAG: ChromaDB query → relevant context injected into system prompt
4. Prompt dispatched to Ollama (NPU/CPU/external)
5. If response contains remediation script → `actions.py` creates `pending` action

### C. Remediation Feedback Loop

1. `actions.py` creates DB record with proposed SSH command
2. Frontend emits `new_action` WebSocket event to Web UI
3. Admin with `admin` or `superadmin` clicks Approve or Reject
4. On Approve: SSH connection to management node → command execution (allowlist pre-validated)
5. STDOUT/STDERR logged → incident enters `validating` state

### D. Notification Pipeline

1. Issue saved → `notifier.send_notification()` fan-out to all enabled channels
2. Per-detector and per-channel toggles checked first
3. Per-severity throttle applied (critical 15 min … low 4 h)
4. Failures enter the retry queue (30 s → 120 s → 300 s backoff)
5. Lifecycle webhooks fired on CREATED / ACKNOWLEDGED / RESOLVED

---

## Issue Workflow

```
  detected ──▶  active  ──▶  acknowledged (✓✓ button)
                   │                │
                   │           validating ──▶ resolved
                   │
                   └──▶ (auto-resolved by detector or expiry rule)
```

**Escalation rules:** If an issue stays `active` or `acknowledged` for more than N hours without resolution, its severity is automatically raised to the next level.

**Lifecycle webhooks** can notify external systems on every transition, and critical issues can be mirrored into **Gitea**.

---

## Installation

```bash
git clone <repo> /opt/Sentinel
sudo bash /opt/Sentinel/install.sh        # Debian/Ubuntu/RHEL/Rocky/Pi OS
sudo python3 /opt/Sentinel/sentinel_init.py   # interactive config wizard
sudo systemctl enable --now sentinel
```

The setup wizard refuses default passwords, generates the systemd unit with `WatchdogSec=900` and a WAL-checkpoint `ExecStartPre`, and creates `/var/lib/sentinel`.

### Key configuration (config.yaml)

```yaml
web:
  port: 5050
  password_hash: "$2b$12$..."      # bcrypt — preferred over plaintext `password`

security:
  login_max_attempts: 5
  login_ban_time: 300
  session_max_hours: 12

ollama:
  url: "http://localhost:11434"
  model: "llama3.2"
  workers: 3

hailo_ollama:
  enabled: false
  url: "http://localhost:8000"

ldap:
  enabled: false
  host: "ldaps://ldap.example.com"
  base_dn: "dc=example,dc=com"

prometheus:
  enabled: true
  scrape_token: "{SECRET:PROM_TOKEN}"   # env-var substitution

telemetry_alerts:
  cpu_critical: 95
  disk_critical: 95
  temp_critical: 85

fim:
  enabled: true
  paths: [/etc/passwd, /etc/shadow, /etc/ssh/sshd_config]
```

---

## Requirements

- Python 3.13+ · Flask · Flask-SocketIO · ChromaDB · paho-mqtt
- `pyotp` (2FA) · `qrcode` + `pillow` (QR enrollment) · `bcrypt` · `jsonschema`
- Ollama with `nomic-embed-text` (for embeddings)
- **Optional:** Hailo AI HAT 2+ with hailo-ollama 5.3.0 for NPU inference

---

## Component Ecosystem

| Component | Description | Port |
|---|---|---|
| **Sentinel** | Central server (this doc) | 5050 |
| **sentinel-agent** | Push agent on each monitored node | — |
| **sentinel-overhealth** | SSH pull orchestrator (cron) | — |
| **sentinel-plugins** | 11 detector plugins | — |
| **sentinel-alert** | Standalone network security dashboard (incl. MikroTik + PiHole) | 5056 |
| **sentinel-hw** | Physical RPi robot | 5055 |
| **sentinel-app** | Android mobile client | — |
| **sentinel-console** | TUI terminal client | — |
