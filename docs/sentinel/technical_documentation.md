# Sentinel Commander — Technical Documentation (v2026.08.001)

Intended for system architects, L3 support, and infrastructure administrators. Covers internal mechanisms, daemon stability, memory management, and OS integration.

---

## System Requirements

- **Python** 3.13+
- **OS:** Debian 11+, Ubuntu 22.04+, RHEL 8/9/10, Rocky Linux, AlmaLinux, Raspberry Pi OS
- **Key libraries:** Flask, Flask-SocketIO, ChromaDB, paho-mqtt, pyotp, qrcode + pillow, bcrypt, jsonschema
- **Optional:** Hailo AI HAT 2+ with hailo-ollama 5.3.0 for NPU inference

### SQLite Hot-Patch (RHEL/Rocky)

ChromaDB requires SQLite ≥ 3.35.0. On older RHEL systems, `__main__.py` dynamically replaces the `sqlite3` import with `pysqlite3-binary` before any other import runs — prevents segfaults without OS-level recompilation.

---

## Filesystem Layout

```
/opt/Sentinel/
├── sentinel/
│   ├── __main__.py         ← entry point, systemd watchdog, faulthandler, LDAP init
│   ├── chat_service.py     ← Flask app factory, SocketIO, RBAC
│   ├── auth.py             ← authentication, LDAP, 2FA/TOTP, bcrypt, sessions
│   ├── state.py            ← SQLite WAL orchestration
│   ├── state_base.py       ← DB connection, migrations, composite indexes
│   ├── state_agents.py     ← agent registry, watchdog, command allowlist
│   ├── state_issues.py     ← issue CRUD, tagging, workflow, TOTP store, thresholds
│   ├── watcher.py          ← inotify, config hot-reload, LDAP re-init, FIM
│   ├── plugin_manager.py   ← dynamic plugin loading, hot-reload
│   ├── ollama_service.py   ← AI worker pool, model switching, llm_semaphore
│   ├── rag.py              ← ChromaDB, nomic-embed-text, BM25 fallback
│   ├── actions.py          ← Autofix lifecycle, SSH exec, ProxyJump
│   ├── notifier.py         ← 13 outbound channels, retry queue, per-severity throttle
│   ├── scheduler.py        ← background maintenance (minute/hourly/nightly)
│   ├── ssh_utils.py        ← build_ssh_cmd(), host-key scanning (accept-new)
│   ├── analytics.py        ← TTC, Mann-Kendall, Z-Score, health score, forecast
│   ├── topology.py         ← agent topology, SNMP CDP/LLDP
│   ├── snmp_trap.py        ← SNMP trap receiver
│   ├── syslog_receiver.py  ← Syslog UDP/TCP receiver
│   ├── safety.py           ← command classifier, allowed_commands
│   ├── utils.py            ← rate-limit, IP ban, JSON logging, int_param()
│   ├── ai_guard.py         ← prompt-injection defence, action cap, loop detection
│   ├── ai_verify.py        ← hallucination check against known infra
│   ├── ai_profiles.py      ← context-window profiles per task type
│   ├── ai_runtime.py       ← response cache, consistency, token budget, routing
│   ├── diagnostics.py      ← fixed read-only command catalog (AI picks IDs, not shell)
│   ├── fix_verify.py       ← post-fix verification; failures as anti-patterns
│   ├── remediation.py      ← graduated ladder: observe→reload→restart→reboot
│   ├── remediation_plan.py ← rollback, risk, dry-run, work queue
│   ├── policy.py           ← block explanation, allowlist/auto-execute proposals
│   ├── escalation.py       ← escalation with prior-attempt context
│   ├── correlate.py        ← change correlation, causal chains
│   ├── incident_analysis.py← timeline, cascades, ranked hypotheses
│   ├── trend_detect.py     ← silent degradation, missing signals
│   ├── baseline.py         ← per-host normal profile, seasonality
│   ├── alert_quality.py    ← false-alarm mining
│   ├── playbooks.py        ← procedures from manual fixes
│   ├── foresight.py        ← capacity forecast, weekly outlook
│   ├── unmatched.py        ← sampling of uncaught log lines
│   ├── rag_utils.py        ← hybrid search, citations, chunking
│   ├── knowledge.py        ← runbooks, prevention hints, KB transfer
│   ├── infra_audit.py      ← config drift, zombies, certs, post-reboot check
│   ├── dependencies.py     ← host dependency graph, blast-radius, shutdown sim
│   ├── routes/             ← Flask Blueprints
│   │   ├── main.py         ← login (2FA flow), dashboard
│   │   ├── issues.py
│   │   ├── agents.py
│   │   ├── actions.py
│   │   ├── system.py
│   │   ├── export.py
│   │   ├── integrations.py ← outbound config + inbound webhooks (Grafana/AM/Zabbix)
│   │   └── chat.py
│   ├── plugins/            ← detector modules
│   ├── static/             ← CSS/JS (gzip, ETag+304, cache 1 yr, defer; .min.js built at deploy)
│   └── templates/          ← Jinja2, i18n strings
├── build_kb.py             ← RAG knowledge base builder (interactive menu, PDF/DOCX/MD)
├── hailo_models.py         ← Hailo TUI model manager
├── sentinel_init.py        ← interactive installation wizard (refuses default passwords)
├── config.yaml.example
├── Makefile                ← make lint / test / build / ci
├── .gitea/workflows/ci.yml ← CI pipeline (pytest + node --check + build)
└── tests/                  ← 1050 tests (route, security, integration, AI layer, benchmark)

/etc/sentinel/
└── config.yaml             ← hot-reloadable configuration (jsonschema-validated)

/var/lib/sentinel/
├── secret_key              ← persistent Flask SECRET_KEY
├── client_api_key          ← auto-generated client token (mode 600)
└── config_backups/         ← automatic pre-restore snapshots (10 kept)

/var/log/sentinel/
├── logs/
│   ├── sentinel_state.db   ← SQLite WAL (issues, telemetry, agents, …)
│   └── sentinel.log
└── chroma_db/              ← ChromaDB vector store
```

---

## Daemon Stability — Self-Watchdog

An internal watchdog in `__main__.py` polls `GET localhost:5050/api/health` every cycle. Since v2026.06.008 the HTTP check runs **in a separate thread** over a **persistent socket**, and the DB uses `busy_timeout` — this removed spurious `SIGABRT` watchdog kills under load.

```
GET /api/health
  │
  ├── 200 OK → reset web_failures=0, systemd WATCHDOG=1
  │
  └── Timeout/Error → web_failures++
        │
        ├── failures == 5  → log RAM/CPU diagnostics
        ├── failures == 9  → dump all thread stacks
        └── failures >= 10 → self-restart + Teams alert
```

**Systemd integration:** unit is generated with `WatchdogSec=900` and a WAL-checkpoint `ExecStartPre`. If `WATCHDOG=1` is not sent in time, systemd issues `SIGKILL` and restarts the daemon.

**Diagnostics:** `faulthandler.enable()` dumps all thread tracebacks to the journal on watchdog abort (works even with a held GIL).

**Graceful shutdown:** SIGTERM flushes the telemetry write buffer and publishes MQTT `sentinel/status: offline` before exit.

**Self-monitoring:** a memory watchdog thread warns when RSS > 1.5 GB; self-metrics (RAM, threads, queue depth, issues, agents online, load1) are written to telemetry every minute; AI queue backlog > 50 raises a `SENTINEL_SELF_HEALTH` issue; startup phase durations are profiled and logged.

---

## Config Hot-Reload

`watcher.py` monitors `/etc/sentinel/config.yaml` via inotify. On `IN_MODIFY`:

1. `time.sleep(1.0)` — waits for the file to be fully written (inotify fires on first byte, not on close)
2. `load_config()` — reloads all config sections (with `{SECRET:ENV_VAR}` substitution)
3. `plugin_manager.load_plugins()` — reloads detector modules
4. `_reinit_ldap()` — re-initialises the LDAP manager (required for LDAP login to work after config change)

**SIGHUP** triggers the same full reload — config **plus** watcher patterns **plus** plugins (`DETECTORS`, `LOG_GROUPS`). The runtime log level can be changed without any reload via `/api/admin/log_level`.

**Schema validation:** critical keys (`web.port`, `worker_threads`, `db_retention_days`, …) are validated with `jsonschema`; an invalid config is rejected instead of half-applied.

---

## SQLite WAL — Database Architecture

All state is stored in `/var/log/sentinel/logs/sentinel_state.db` in WAL (Write-Ahead Logging) mode. Key tables:

| Table | Purpose |
|---|---|
| `problems` | Active incidents — key, status, severity, channel, host, last_line, missing_count |
| `issue_history` | Archived incidents incl. `first_seen` → enables resolution-time analytics; 90-day retention |
| `actions` | Autofix lifecycle — command, status, risk_score, dry_run_output, mode, actor |
| `action_audit` | Append-only compliance log — every lifecycle event with actor and timestamp |
| `config_audit` | Config change audit — who, when, IP, which keys |
| `task_queue` | AI worker queue — status, worker_id (single-consumer guarantee) |
| `telemetry` | TSDB — metric, value, timestamp (composite indexes, batched writes) |
| `agents` | Agent registry — hostname, token, last_seen, status, ip_addresses, version |
| `active_sessions` | Session tracking — user, ip, created_at, last_seen, revokable |
| `revoked_sessions` | Revocations that survive restart |
| `user_totp` | 2FA/TOTP secrets per user |
| `api_keys` | REST API keys — SHA-256 hash, fine-grained scopes |
| `issue_tags` | Tag → issue_key mapping |
| `suppress_rules` | False positive patterns for auto-suppression (with hit_count) |
| `snooze_rules` | Maintenance windows — global or per-host (`hosts` CSV column) |
| `custom_patterns` | User-defined regex detection patterns (Pattern Editor) |
| `ssh_execute_log` | Audit log of all SSH-executed commands |
| `root_audit` | Root session log — server, ip (with reverse DNS), connected_at, is_active |
| `agent_thresholds` | Per-agent alert thresholds (enforced on ingest) |
| `comment_templates` | Saved comment templates for issue annotations |

**WAL tuning:** `wal_autocheckpoint=200`, `PRAGMA synchronous=NORMAL`, explicit checkpoint after telemetry prune. The DB lives **outside** any inotify-watched directory (a watched DB file caused HPC instability).

**Garbage collection** (`scheduler.py`): batched deletion (LIMIT 1000) to avoid WAL lock contention; `prune_issue_history(days=90)`; `VACUUM` after > 10 000 deleted rows. Default retention: telemetry 2 days, resolved issues 2 days, issue history 90 days.

**Caching:** `get_active_issues()` has a 5 s TTL in-memory cache guarded by a double-checked `threading.Lock` (fast lock-free read path, locked rebuild); dashboard sparkline queries cache for 5 min.

**Agent watchdog**: background thread flips agent `status` to `OFFLINE` if no heartbeat within `agent_heartbeat_timeout` seconds (per-agent or global fallback); offline duration is recorded to telemetry on reconnect.

---

## Security Layer

| Mechanism | Implementation |
|---|---|
| 2FA / TOTP | pyotp (RFC 6238), `user_totp` table, two-step login flow, QR enrollment (qrcode + pillow) |
| Password hashing | bcrypt (`$2b$` prefix detection in `_check_password()`); `web.password_hash` preferred over plaintext |
| CSRF | Session + SameSite=Strict cookie token; global `fetch` wrapper adds `X-CSRF-Token` to POST/PUT/DELETE |
| Brute-force | Form login + Basic auth: 5 failures → 300 s IP ban; auto-register 10/min per IP; `/api/analyze/*` 10 req/min |
| XSS | `html.escape()` on all AI replies before they reach `innerHTML` (log content is attacker-controlled) |
| SSH | `ssh_utils.build_ssh_cmd()` — `accept-new` + pinned `UserKnownHostsFile`; `ssh-keyscan` on registration; hostname regex validation; command allowlist pre-validation |
| API key verify | Timing-safe `hmac.compare_digest(sha256(submitted), stored_hash)`; scopes `read:issues` / `write:actions` / `admin:users` |
| Sessions | Absolute 12 h timeout, role refresh from DB every 5 min, revocations persisted in DB |
| Secrets | `{SECRET:ENV_VAR}` config substitution (env vars wiped after use); `/api/config/view` masks secrets as `***`; persistent SECRET_KEY in `/var/lib/sentinel/secret_key` |
| Webhooks | HMAC `X-Hub-Signature-256` + replay protection via `X-Webhook-Timestamp` |
| SSRF | `/api/admin/validate_url` rejects private IP ranges |
| Input validation | `int_param(value, default, min, max)` on 20+ endpoints — no negative values reaching SQL `datetime()` |
| Reverse proxy | `get_real_ip()` honours `X-Forwarded-For` only from `TRUSTED_PROXIES` |
| Audit | `config_audit`, `ssh_execute_log`, `action_audit`, 403/401 access audit; viewer UI in Settings |
| FIM | SHA-256 of critical files checked every minute → security issue on change |
| Symlink containment | `os.path.realpath()` check on all file path inputs |
| Upload limits | 5 MB max, `secure_filename()`, extension allowlist |
| CSP headers | Content-Security-Policy on all responses |
| LDAP | Fallback to direct `ldap3` bind if manager unavailable |
| Self-check | `/api/admin/security_check` → grade A/B/C/D |

---

## Performance Optimisations

- **Static file caching:** ETag + `max-age` + 304 conditional GET; `Cache-Control: max-age=31536000, immutable` with `?v=<subversion>` fingerprinting
- **Script loading:** all external `<script src>` tags use `defer`; `<link rel="preload">` for critical CSS/JS
- **Gzip compression:** Flask-Compress level 6, min 2 KB — ~75 % transfer reduction
- **Socket.IO transport:** `['polling', 'websocket']` with `upgrade: true` — starts over HTTP long-polling (survives all proxies), upgrades to WebSocket when available
- **Backpressure:** frontend SocketIO queue bounded at 500 with drop-oldest; duplicate WS messages deduplicated in a 1 s window
- **Telemetry batching:** `save_telemetry_snapshot()` writes through a buffer, flushed periodically and on SIGTERM
- **DB indexes:** `idx_problems_plugin_ch_ts`, `idx_issue_hist_plugin_ts`, `idx_problems_severity`, `idx_telemetry_cat_metric_ts` — created automatically on startup
- **AI semaphore:** serialisation handled exclusively inside `execute_ollama()` (an outer re-entrant acquire previously caused a permanent deadlock); Ollama HTTP timeout bounded at 90 s
- **Hot read path:** no writes from `get_pending_actions()` (expiry moved to a background loop) — this removed "UI offline" stalls under agent ingest load
- **Bulk ingest:** `/api/v1/ingest/bulk` accepts an array of alerts in one HTTP request

---

## CI & Test Suite

- **1050 tests**: Flask route tests, security tests (brute force, API scopes, hostname injection, secrets masking), integration tests (full issue lifecycle on a real DB), dashboard performance benchmark
- **CI:** Gitea Actions (`.gitea/workflows/ci.yml`) — pytest + `node --check` + `make build`; local `pre-push` git hook
- **Lint:** ruff (`pyproject.toml`), ESLint with `no-redeclare=error`; `make ci` runs lint + tests
- **Build artefacts:** `.min.js` files are built at deploy time and excluded from git

---

## Hailo AI HAT 2+ Integration

When `hailo_ollama.enabled: true` in config:

- Inference requests route to hailo-ollama at `http://localhost:8000` (NPU)
- CPU Ollama at `:11434` used for embeddings only (nomic-embed-text)
- Runtime model switch via `hailo_models.py` TUI without daemon restart
- `hailo_models.py` — 619-line Unicode TUI: htop-style CPU/Mem bars, RX/TX throughput, NPU architecture + firmware, TPS benchmark graph
