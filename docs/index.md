# Sentinel Commander — Documentation (v2026.08.001)

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
                    v2026.08.001
```

**Hybrid AI Log Monitor & Analyzer for Linux Infrastructure**

---

## Quick Navigation

- **[Deployment Guide](./DEPLOYMENT.md)** — Production deployment of the entire system
- **[API Reference](./API.md)** — Plugin and integration API
- **[Troubleshooting](./TROUBLESHOOTING.md)** — Common issues and solutions
- **[Host Setup](./host-setup.md)** — Preparing monitored hosts for AI diagnostics

---

## What is Sentinel?

Sentinel Commander is an advanced hybrid monitoring system with a full AI layer designed for enterprise Linux infrastructure. It combines a **Pull** approach (inotify log tailing) with a **Push** approach (remote Python agents POSTing telemetry). Core integrations: Hailo AI HAT 2+ NPU (hailo-ollama), local/external Ollama LLM, ChromaDB (RAG).

As of v2026.08.001 the system has accumulated **1 050 automated tests** and **80/100 AI roadmap items** across 24 new AI modules covering diagnostics, verification, remediation planning, correlation, baselining, forecasting, and knowledge management.

---

## What's New in v2026.08.001 (2026-08-03)

| Feature | Detail |
|---|---|
| **Tests: 938 → 1050** | 112 new tests covering knowledge base, infra audit, and dependency mapping modules |
| **80/100 AI roadmap items** | Up from 66/100 in v2026.07 |
| **3 critical SSH bugs fixed** | SSH broken July 30–Aug 1 in diagnostics + remediation; fully resolved |
| **`knowledge.py`** | Runbooks, prevention hints, training pairs, KB transfer to/from other instances |
| **`infra_audit.py`** | Config drift detection, zombie process auditing, cert expiry, post-reboot checklist, docs accuracy check |
| **`dependencies.py`** | Inferred host dependency graph, blast-radius calc, simulated shutdown impact |
| **`host-setup.md`** | New guide: preparing monitored hosts for AI diagnostics (sentinel user, sudoers, journal group) |

---

## What's New in v2026.07.001 (2026-07-31)

### AI Layer — 21 New Modules

| Module | What it does |
|---|---|
| `ai_guard.py` | Prompt-injection defence for log content, hourly action cap, loop detection |
| `ai_verify.py` | Hallucination check — validates AI claims against known infrastructure |
| `ai_profiles.py` | Context-window profiles per task type (triage, deep analysis, chat) |
| `ai_runtime.py` | Response cache, consistency guard, token budget, model routing |
| `diagnostics.py` | Fixed read-only command catalog — AI picks command IDs, never writes raw shell; executes and interprets real output |
| `fix_verify.py` | Post-fix verification ~15 min after each remediation attempt; failures fed back as anti-patterns |
| `remediation.py` | Graduated ladder: observe → reload → restart → reboot |
| `remediation_plan.py` | Rollback, contextual risk assessment, dry-run mode, work queue |
| `policy.py` | Block explanation, allowlist/auto-execute proposals |
| `escalation.py` | Escalation with context (what was already tried + why it failed) |
| `correlate.py` | Change correlation, causal chains, cross-host patterns |
| `incident_analysis.py` | Common denominator finder, incident timeline, cascade detection, ranked hypotheses |
| `trend_detect.py` | Silent degradation (regression + r²), missing-signal detection |
| `baseline.py` | Per-host normal profile, seasonality detection, auth-log audit |
| `alert_quality.py` | False-alarm mining from historical data |
| `playbooks.py` | Procedures learned from manual fixes — builds institutional memory |
| `foresight.py` | Capacity forecast, weekly infrastructure outlook |
| `unmatched.py` | Random sampling of log lines that no plugin catches |
| `rag_utils.py` | Compression, hybrid search, citations, chunk management |
| `knowledge.py` | (preview in 07, promoted to stable in 08) |
| `infra_audit.py` | (preview in 07, promoted to stable in 08) |

### Scale

- Tests: **317 → 938** (+621 new tests covering the full AI layer)
- AI roadmap: **66/100** items complete
- Full decision audit trail for every AI action
- All AI modules fully integrated into the Scheduler maintenance loop

---

## What's New in v2026.06.024 (since v2026.06.005)

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
| **Lifecycle webhooks** | Configurable webhooks fired on issue CREATED / ACKNOWLEDGED / RESOLVED |
| **Gitea issue sync** | Critical issues automatically opened in a Gitea repository |
| **Prometheus** | `GET /metrics` scrape endpoint + pushgateway export |

### Analytics, Agent Fleet, Operations

- Health score per host (A–D grade), 7-day issue forecast, SLA & alert-fatigue reports
- Batch SSH (50 hosts, ThreadPoolExecutor), per-agent thresholds, CVE scanner, package inventory
- `/healthz` probe, config backup/restore with snapshots, SIGHUP hot-reload, FIM, Ansible runner
- Composite DB indexes, WAL tuning, HTTP caching (ETag + 304), SocketIO backpressure, virtual scroll

### Engineering Quality

- **181 automated tests** (v2026.06.024 baseline) — now 1 050 in v2026.08.001
- CI pipeline — `pytest` + `node --check` + `make build`, `pre-push` git hook
- Linting — ruff (Python), ESLint, pinned `requirements.txt`

---

## Feature Overview

| Area | Capabilities |
|---|---|
| **AI Inference** | Hailo-10H NPU (hailo-ollama) · CPU Ollama · external API · runtime model switch |
| **RAG Knowledge Base** | ChromaDB + nomic-embed-text · BM25 TF×IDF fallback · custom file upload (.md/.txt/.pdf/.docx/.csv) · one-click reindex |
| **AI Safety** | Prompt-injection defence · hourly action cap · loop detection · hallucination check · full audit trail (`ai_guard.py`, `ai_verify.py`) |
| **AI Diagnostics** | Fixed read-only command catalog — AI picks IDs, never raw shell; executes and interprets real output (`diagnostics.py`) |
| **AI Verification** | Post-fix check ~15 min after each remediation; failures flagged as anti-patterns (`fix_verify.py`) |
| **AI Remediation** | Graduated ladder: observe → reload → restart → reboot · rollback · dry-run · contextual risk (`remediation.py`, `remediation_plan.py`) |
| **AI Correlation** | Causal chains · change correlation · cross-host patterns · cascade detection · incident timelines · ranked hypotheses (`correlate.py`, `incident_analysis.py`) |
| **AI Baselining** | Per-host normal profile · seasonality · silent degradation (regression + r²) · missing signals (`baseline.py`, `trend_detect.py`) |
| **AI Foresight** | Capacity forecast · weekly outlook · false-alarm mining · unmatched log sampling (`foresight.py`, `alert_quality.py`, `unmatched.py`) |
| **Knowledge Base** | Runbooks · prevention hints · training pairs · KB transfer between instances (`knowledge.py`) |
| **Infra Audit** | Config drift · zombie processes · cert expiry · post-reboot checklist · docs accuracy check · dependency blast-radius (`infra_audit.py`, `dependencies.py`) |
| **Hybrid Telemetry** | Pull (inotify logs) + Push (agents via Bearer token) · multiple IPs per agent · agent version tracking (SHA) |
| **Autofix** | AI proposes fix → admin Approve/Reject → SSH exec on mgmt node · allowed-commands allowlist · autonomous exec |
| **Predictive Analytics** | TTC (Time-To-Critical) for disks · Mann-Kendall trend test · linear regression forecast · capacity planning |
| **Security Profiler** | Brute-force, sudo abuse, CVE scan, unauthorised ports, honeypot, FIM, SSL expiry |
| **Notifications** | 13 outbound channels · 3 inbound webhooks · retry queue · per-severity throttle · per-detector/channel toggles |
| **Prometheus** | `GET /metrics` scrape + pushgateway export; auth via scrape_token |
| **Dashboard** | Stat cards · interactive min/max/avg charts · trend chart · donut · health trend · flapping widget · live clock |
| **Auth** | viewer / admin / superadmin · LDAP (lldap + OpenLDAP) · **2FA/TOTP** · **bcrypt** · rate-limit + IP ban · **CSRF** |
| **Issue Workflow** | `active` → `acknowledged` → `validating` → `resolved` · escalation rules · lifecycle webhooks |
| **Auto-Remediation** | One-shot SSH fix · allowed_commands with `auto_execute` · AUTOFAIL issues · SSH jump host (ProxyJump) · Ansible runner |
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

### AI layer modules (v2026.07+)

| File | Responsibility |
|---|---|
| `ai_guard.py` | Prompt-injection defence, action cap, loop detection |
| `ai_verify.py` | Hallucination check against known infrastructure |
| `ai_profiles.py` | Context-window profiles per task type |
| `ai_runtime.py` | Response cache, consistency, token budget, model routing |
| `diagnostics.py` | Fixed read-only command catalog — AI picks IDs, not raw shell |
| `fix_verify.py` | Post-fix verification; failures feed back as anti-patterns |
| `remediation.py` | Graduated remediation ladder with rollback |
| `remediation_plan.py` | Risk assessment, dry-run, work queue |
| `policy.py` | Block explanation, allowlist/auto-execute proposals |
| `escalation.py` | Escalation with prior-attempt context |
| `correlate.py` | Change correlation, causal chains, cross-host patterns |
| `incident_analysis.py` | Timeline, cascade detection, ranked hypotheses |
| `trend_detect.py` | Silent degradation, missing signals |
| `baseline.py` | Per-host normal profile, seasonality, auth-log audit |
| `alert_quality.py` | False-alarm mining from historical data |
| `playbooks.py` | Procedures learned from manual fixes |
| `foresight.py` | Capacity forecast, weekly outlook |
| `unmatched.py` | Sampling of uncaught log lines |
| `rag_utils.py` | Compression, hybrid search, citations, chunking |
| `knowledge.py` | Runbooks, prevention hints, KB transfer |
| `infra_audit.py` | Config drift, zombies, certs, post-reboot check |
| `dependencies.py` | Host dependency graph, blast-radius, shutdown simulation |

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
