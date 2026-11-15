# Sentinel Commander — Documentation (v2026.11.010)

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
                    v2026.11.010
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

As of v2026.11.010 the system has accumulated **1 261 automated tests** and **80/100 AI roadmap items** across 24 new AI modules covering diagnostics, verification, remediation planning, correlation, baselining, forecasting, and knowledge management.

---

## What's New in v2026.11.009 – v2026.11.010 (2026-11-15)

| Feature | Detail |
|---|---|
| **Detectors are a separate package** | Sentinel now keeps only the base: `base.py` (the source of `api.BaseDetector`) and the two detectors it makes no sense to run without — `system_detector` and `services_detector`. The other ten moved to the `sentinel-plugins` repository and install from their own `.deb`/`.rpm`. A detector fix no longer means releasing all of Sentinel, and a Sentinel release no longer overwrites detectors somebody added. See [Sentinel Plugins](./sentinel-plugins.md) |
| **`plugin_dir` may be a list** | It used to be a single directory, which is what forced site-specific detectors to be copied **into** Sentinel's directory — the arrangement behind two production incidents. Directories are now searched in the order given; a plain string behaves as before |
| **Hailo: JSON tasks return JSON** | `hailo-ollama` ignores both `format` and `response_format`, so remediation and severity classification came back wrapped in markdown and `process_ai_proposal()` could not parse them. A system message keyed on `context.source` is the only lever that works; it has to be single-line, because an LF in `content` breaks hailo-ollama's internal rendering. Measured with the production prompt: three cases out of three returned no JSON without it, valid JSON — and faster — with it |
| **Control tokens stripped** | Small models occasionally leak their own control markers into the reply (`<turn\|>`, `<\|im_end\|>`). They are now removed from every response, not just the Hailo path. The filter is narrow, so ordinary `<br>` survives |
| **Packages for six components** | `.deb` and `.rpm` for Sentinel, agent, alert, overhealth, console and plugins, published as releases and into a Debian/RPM registry. See [Deployment](./DEPLOYMENT.md) |
| **Tests: 1 260 → 1 261** | Plus 10 in `sentinel-plugins`, which now has its own suite, and 102 in `sentinel-agent` |

!!! warning "Upgrade order"
    Install `sentinel-plugins` **before** upgrading to v2026.11.010. A detector that `config.yaml` requires but whose file is nowhere in `plugin_dir` raises `SENTINEL|detectors_missing` (critical).

---

## What Was New in v2026.11.005 – v2026.11.008 (2026-11-13)

| Feature | Detail |
|---|---|
| **`read:root` scope — full view without write access** | The role is derived from the **key's scope**, not from its owner. But only scopes that also grant writing mapped to `admin`/`superadmin`, so a read-only tool had to choose between the complete picture and a smaller blast radius if the key leaked. The new `read:root` stays in the `viewer` role and handles ROOT visibility as a separate permission. An `admin` may issue it — they already see ROOT in the UI, so a read-only key with the same reach is not an escalation |
| **Server version in `status_check`** | `GET /api/status_check` now returns `version`. Until then clients guessed the server's capabilities from whether a particular field was present — it worked, but it was detection by touch |
| **Raw fields in `/api/v1/issues`** | `first_seen`, `occurrence_count`, `plugin_name`, `db_severity`, `acknowledged_by` and `snoozed_until`. Without them a client could not compute a problem's age or sort by real severity, and had to fetch them with a second call. `severity` stays derived from the channel for the mobile app; the real DB value sits beside it as `db_severity` |
| **`?include_ignored=1`** | Returns ignored issues too, marked with an `ignored` flag. Deliberately opt-in: without the parameter nothing changes, so existing clients do not suddenly show items their user has hidden |
| **Two buttons on issue cards did nothing** | The "add inline comment" icon and the colour-label dot rendered `onclick` handlers for functions that did not exist in the frontend at all. The click ended in a console error — no message, no request to the server — while both backends were finished. A new test now walks every `on*="fn(…)"` attribute and checks that the function exists |
| **Comments shown on the card** | They could only be read by opening the badge, so anyone scanning the list did not know somebody had already written something. They now render on the card in their own colour: the last three, the rest behind a link to the modal. Loaded with a single query for the whole list |
| **A comment being typed survives the refresh** | The modal re-renders every 3 seconds and the comment row renders closed, so the refresh closed it along with the text. More than three seconds of typing was impossible. The refresh now remembers open rows, their contents, the caret position and focus |
| **Tests: 1 229 → 1 260** | Covering the `read:root` scope (above all that it cannot write), the raw fields and `include_ignored`, comments on the card, and the existence of functions behind `onclick` |

---

## What Was New in v2026.10.001 – v2026.11.004 (2026-11-12)

| Feature | Detail |
|---|---|
| **Prompt injection: logs as data, not instructions** | `ai_guard.wrap_untrusted()` existed, but only diagnostics, knowledge and incident analysis used it. Chat bypassed it — the log tail, alert lines, the open file's contents and the autofix message all went into the prompt bare, in the same message as the user's question, so an "ignore previous instructions" line from a log was indistinguishable from an instruction. All paths are now fenced, system prompts carry `UNTRUSTED_RULE`, and the reply stored in history goes through `sanitize()` |
| **Fencing applies to every prompt** | After the chat fix about 15 places remained where `last_line` or log content reached the model bare — escalation, remediation, cause chain, pattern suggestions, the daily digest, re-analysis, root cause, bulk analysis, clusters, runbooks, postmortems. All now go through `ai_guard.untrusted()`. Only what does not come from logs stays unfenced: telemetry, trends, comments by signed-in users, and static evals |
| **Warning on risky commands in replies** | `ai_guard.risky_commands()` runs code blocks and inline commands from the reply through `safety.classify()`; risky ones get a warning under the answer. The model runs nothing itself, but the user copies the command — autofix had a risk score, free chat did not |
| **"AI users" overview** | A new view: who runs AI on which machine, with which tool and model, and for how long. It covers interactive CLI agents, local LLM runtimes, MCP servers, and processes holding a connection to a provider API that cannot be recognised by name. The data arrives from the agent outside the issue table, so nothing alerts and nothing lingers |
| **Session identity** | A session is identified by `(host, pid, started_at)`. A pid is recycled after a reboot; a process start time does not change between polls — so a repeated poll only confirms the row. `started_at` is stored as an empty string rather than `NULL`: two `NULL`s are not equal in a `UNIQUE` index, so a session with an unknown start time could not be deduplicated |
| **Collapsible overview by technology** | The modal nests **technology → agent → user → session**, each level carrying a "running / total" count. With hundreds of concurrent processes a flat list is unreadable. What the user collapses stays collapsed across refreshes |
| **Header count did not match the view** | The badge counted every running session, but the endpoint capped rows per host without distinguishing state — a host with hundreds of processes returned only the cap. The cap now applies to finished sessions only; running ones always pass |
| **Sessions left behind by a dead agent** | A session is closed by being absent from its host's next snapshot. If an agent stops reporting altogether, no snapshot arrives and its sessions stay "running" forever. Anything unconfirmed for longer than `ai_sessions_stale_minutes` (30) is now closed |
| **Self-service API keys** | Users manage their own long-lived keys for scripts (`X-API-Key`); the secret is shown once, at creation. Passing a key in the URL is restricted — query strings end up in proxy and browser logs |
| **Request Tracker integration** | Ticket listing with queue and text filters, commenting with the author recorded, taking ownership, and status changes |
| **Less detector noise** | Resolved disk findings disappear, loopback ports are no longer treated as new, container temperature is not measured against the host, and known messages no longer raise issues |
| **Remediation plan for viewers** | The `viewer` role could have a plan generated but not displayed. Plus parameter validation on `logs/view` and a fix to the default role assigned on LDAP login |
| **Tests: 1 188 → 1 229** | New ones cover the AI session store (identity, closing, retention), untrusted-data fencing, and the quieter detectors |

---

## What Was New in v2026.09.001 – v2026.09.016 (2026-09-08)

| Feature | Detail |
|---|---|
| **Process freeze on DB `close()` (critical)** | An instance with a large database died several times a day and its UI was unreachable in between. `sqlite3.Connection.close()` does **not** release the GIL, and Sentinel held no long-lived DB connection — so every per-request `close()` was the *last* connection and SQLite ran a full WAL checkpoint under it, freezing the whole process. Fix: `state_base._ensure_keeper()` opens one connection at startup and keeps it open. Measured on a 111 MB database: `close()` went from 0.233 s to 0.000 s |
| **One freeze, three symptoms** | The same GIL hold explained all of it: the web thread never reached `accept()` (accept queue grew toward 128, then `Connection refused`), the watchdog thread never sent a ping (SIGABRT after 300 s), and the signal handler never ran (SIGTERM ignored for 91 s → SIGKILL) |
| **File Integrity Monitoring — implemented** | FIM had config, documentation and tests but **no implementation**; its only caller was the dead `scheduler.py` removed in v2026.08.003. `watcher.fim_check()` now hashes watched files (SHA-256) against a baseline in `kv_settings['fim_state']`, runs every minute from the main loop, and raises `FIM_CHANGE\|<path>` issues in the `security` channel with severity `high` |
| **Root audit stops re-inserting** | The agent path closed and re-inserted every active session on **every** report — one host produced 126 rows in 36 minutes and the table reached 105 000 rows. Sessions are now reconciled by `(server, tty, login time)`: an ongoing session is confirmed, a new one inserted, an unreported one closed. Row growth dropped to zero |
| **Session length finally means session length** | `connected_at` used to be reset on every poll, so "duration" showed time since the last report. It now holds the **actual login time** parsed from the agent's message |
| **Stale root sessions expire** | Sessions a detector stops reporting stayed `is_active=1` forever — daily pruning only deletes `is_active=0`, so it skipped them (records 67 days old were still shown as active). New `root_audit.last_seen` plus a per-minute sweep controlled by `root_audit_stale_minutes` (default 30) |
| **Detector vs. agent origin** | Both paths write to `root_audit` but store different things in `server`: a detector writes the cluster name, an agent the hostname. New `root_audit.origin` column tells them apart; for detector records the cluster **is** the `server` value, which also fixed `CS` falling into `INFRA` (the `.cs.` rule never matched the bare `CS`) |
| **History grouped and limited per cluster** | The session history modal groups records into collapsible **cluster → server** sections. The global `LIMIT 100` gave the whole window to one busy cluster; it is now the last `root_audit_history_per_cluster` (default 30) **per cluster**, with active sessions always shown |
| **`ollama_extra_body`** | New config key that merges extra fields into the OpenAI `/v1` request body. Needed for reasoning models: `qwen3-32b` without `chat_template_kwargs.enable_thinking=false` emits `<think>` blocks **inside `content`** (not `reasoning_content`), which would land in chat, in the daily digest and in auto-severity classification |
| **Invented hosts detected without a lead-in word** | `ai_verify` only flagged a hallucinated machine when the model introduced it ("on machine web-server-03"). A bare "check db-master-01" passed, because any hyphenated token without a dot was discarded as a command. Such a token now passes when it has a **numeric segment**; `read-only`, `dry-run` and `self-signed` stay filtered. The hostname regex is Unicode-aware |
| **Plugin log modal** | New `/api/plugins/<name>/log` endpoint and a **Log** button in the Detectors & Plugins table |
| **Agent version badge** | The agent detail modal compares an agent's version against the most common version among online agents and shows ✓ current or ⬆ newer |
| **"Communication error" under a finished answer** | The answer rendered in full and the error appeared **below** it; nginx logged `upstream prematurely closed connection` on `/api/chat/stream`. An SSE generator is evaluated **after the view returns**, when Flask's request context is gone — but right after emitting `done` it called `log_event(..., user=g.username)`, which raises `RuntimeError`, kills the generator and cuts the connection mid-stream. The username is now captured before the generator is defined; the same bug was in the SSH-output stream in `actions.py`. A test walks both generator bodies and fails if they touch `g` |
| **Chat answered from the KB instead of from issues** | The streaming chat path — the one the web UI uses — assembled context from conversation history, knowledge base and the question only: **active issues were not in it at all**. Asked to analyse current problems, the model answered from the only thing it had, KB documents about user accounts and storage quotas. The older non-streaming path did send an alert summary, so the UI had *less* context than the path it replaced. `ChatService.build_alerts_context()` is now shared by both |
| **Request queue showed a different queue** | The modal printed the in-memory counter as "AI queue" but listed rows from the DB `task_queue` — two unrelated things, so it reported "AI queue: 1" above "Queue is empty" while a request really was running. It now lists the actual in-flight AI requests, with `waiting` (queued on the semaphore) distinguished from `processing` |
| **AI queue counter leaked** | `chat_queue_depth` was incremented before `llm_semaphore.acquire()` and decremented after it — any exception in between left the counter up forever. The same `finally` released a semaphore that may never have been acquired, silently raising the concurrency limit |
| **Autofix suggestion shown as raw text** | Models write shell regexes into JSON strings (`"grep -i 'a\|b'"`); `\|` is not a valid JSON escape, so `json.loads` failed and the suggestion appeared verbatim with command `N/A`. `extract_json()` now retries with lone backslashes doubled, leaving valid escapes intact |
| **Tests: 1 087 → 1 165** | Includes 11 long-failing tests that were never green: 9 FIM tests targeted a function that had never existed, 2 `ai_verify` tests covered the detection gap above |

---

## What's New in v2026.08.006 (2026-08-19)

| Feature | Detail |
|---|---|
| **Watchdog ABRT crash fix (critical)** | Sentinel crashed every 5–38 min with `Failed with result 'watchdog'`. Root cause: non-blocking socket for systemd notify — under WebSocket thread load, `EAGAIN` was silently swallowed, all pings lost, systemd sent SIGABRT after 120 s. Fix: `sock.settimeout(1.0)` — send waits max 1 s, then recovers the socket. Pings never get dropped |
| **Configurable cluster detection** | `host_cluster_rules` in config.yaml — list of `{pattern, cluster}` rules for mapping hostnames to clusters. Priority: explicit `cluster` field → `[CLUSTERNAME]` prefix in `last_line` → config rules → `default_cluster`. No hardcoded cluster names |
| **`api.get_cluster_from_host()`** | Shared function in `sentinel/api.py` — plugins call it instead of their own hardcoded `_cluster_from_host()` methods. `detector_icinga` and `detector_who` migrated |
| **`ignored_host_services`** | New param in `detector_icinga` config — suppresses specific services on specific hosts (`service_pattern@host_pattern`). Eliminates false positives for services that don't run on certain node types |
| **Stale ROOT sessions after restart** | `detector_who`: after restart, `_scan_prev` was empty → stale sessions from DB never closed. Fixed by seeding from `api.get_active_keys()` at first scan |
| **Slurmctld debounce** | `detector_cluster`: `Slurmctld ping: DOWN` reported only after `slurmctld_threshold` (default 2) consecutive DOWN scans — transient ping failures no longer create issues |
| **Issue buttons fix** | Delete/ignore buttons in issue modals now call direct REST endpoints (`/api/issues/<key>/delete`, `/api/issues/<key>/ignore`) instead of routing through chat |
| **2-level issue grouping** | Incident Matrix and all modals group issues into CLUSTER → DETECTOR tree. Cluster folders always open, detector folders collapse at ≥5 issues |
| **Folder state preserved** | Modal auto-refresh (3 s) now tracks explicitly closed folders — they stay closed across refreshes |
| **Agent systemd unit names** | `agent_systemd_global_monitor`: `--plain` flag + position `[1]` parsing — shows actual unit names instead of `●, ●, ●` |
| **Missing plugins deployed** | Only 4/15 plugins were deployed. `deploy-auto.sh` now syncs all `detector_*.py` and protects them from deletion |
| **Teams test notifications removed** | `__main__.py` no longer sends to non-existent `tests` channel on startup/shutdown |

---

## What's New in v2026.08.003 (2026-08-17)

| Feature | Detail |
|---|---|
| **Issue lifecycle auto-close** | Four mechanisms: age cap for event-type issues, detector reconciliation (HA, capacity), periodic auto-recheck, and tighter `system_detector` matching (word-boundary regexes + configurable ignore-list). Production: **47 → 21 active issues** |
| **Reasoning models in chat** | API key detection for v1 interface; `reasoning_content` streamed with a `reasoning` flag and rendered in a muted block above the answer |
| **Mobile UI fixes** | Issue cards and modal on mobile were clipped/unreadable — shared CSS classes, secondary actions hidden under 480 px, `.issue-msg` excluded from badge truncation |
| **Dead `scheduler.py` removed** | Module was never imported; it referenced three non-existent symbols. Two real fixes (retention constant, auto-recheck hookup) were silently stuck inside it. Functional tasks moved to `chat_service.py` loop and new `issue_lifecycle.py` |
| **Three scheduled tasks now actually run** | Hourly joke, DNS check, daily AI digest — all existed but were only scheduled in the dead module |
| **Memory leak fixes** | `_GEO_CACHE` hourly prune and `user_sessions` GC now run (were the only cleanup paths, both stuck in dead scheduler) |
| **Tests: 1 050 → 1 087** | New `test_issue_lifecycle.py` (21 tests); total 1 087 |

---

## What's New in v2026.08.001 (2026-08-03)

| Feature | Detail |
|---|---|
| **Tests: 938 → 1 050** | 112 new tests covering knowledge base, infra audit, and dependency mapping modules |
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
- All AI modules fully integrated into the maintenance loop (`chat_service.py` + `issue_lifecycle.py`)

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

- **1 261 automated tests** (v2026.11.010) — route, security, integration, AI layer, issue lifecycle, benchmark
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
| **Hybrid Telemetry** | Pull (inotify logs) + Push (agents via Bearer token) · multiple IPs per agent · agent version tracking (SHA) · version drift badge in agent detail |
| **Autofix** | AI proposes fix → admin Approve/Reject → SSH exec on mgmt node · allowed-commands allowlist · autonomous exec |
| **Predictive Analytics** | TTC (Time-To-Critical) for disks · Mann-Kendall trend test · linear regression forecast · capacity planning |
| **Security Profiler** | Brute-force, sudo abuse, CVE scan, unauthorised ports, honeypot, FIM, SSL expiry |
| **Notifications** | 13 outbound channels · 3 inbound webhooks · retry queue · per-severity throttle · per-detector/channel toggles |
| **Prometheus** | `GET /metrics` scrape + pushgateway export; auth via scrape_token |
| **Dashboard** | Stat cards · interactive min/max/avg charts · trend chart · donut · health trend · flapping widget · live clock |
| **Auth** | viewer / admin / superadmin · LDAP (lldap + OpenLDAP) · **2FA/TOTP** · **bcrypt** · rate-limit + IP ban · **CSRF** |
| **Issue Workflow** | `active` → `acknowledged` → `validating` → `resolved` · escalation rules · lifecycle webhooks · 2-level CLUSTER→DETECTOR grouping |
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
  hailo-ollama      Ollama CPU      external   issue_lifecycle   notifier.py
  (NPU :8000)       (:11434)        API        + maintenance    (13 channels)
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
| `issue_lifecycle.py` | Issue auto-close: age cap, detector reconciliation, periodic auto-recheck |
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

host_cluster_rules:
  - pattern: node1
    cluster: COMPUTE
  - pattern: storage
    cluster: STORAGE
default_cluster: INFRA
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
