# Sentinel Commander — Technická dokumentace (v2026.06.024)

Určeno pro systémové architekty, L3 support a infrastrukturní administrátory. Pokrývá interní mechanismy, stabilitu daemona, správu paměti a OS integraci.

---

## Systémové požadavky

- **Python** 3.13+
- **OS:** Debian 11+, Ubuntu 22.04+, RHEL 8/9/10, Rocky Linux, AlmaLinux, Raspberry Pi OS
- **Klíčové knihovny:** Flask, Flask-SocketIO, ChromaDB, paho-mqtt, pyotp, qrcode + pillow, bcrypt, jsonschema
- **Volitelně:** Hailo AI HAT 2+ s hailo-ollama 5.3.0 pro NPU inference

### SQLite Hot-Patch (RHEL/Rocky)

ChromaDB vyžaduje SQLite ≥ 3.35.0. Na starších RHEL systémech `__main__.py` dynamicky nahrazuje import `sqlite3` za `pysqlite3-binary` ještě před jakýmkoliv jiným importem — zabraňuje segfaultům bez překompilování OS.

---

## Struktura souborového systému

```
/opt/Sentinel/
├── sentinel/
│   ├── __main__.py         ← entry point, systemd watchdog, faulthandler, LDAP init
│   ├── chat_service.py     ← Flask app factory, SocketIO, RBAC
│   ├── auth.py             ← autentizace, LDAP, 2FA/TOTP, bcrypt, sessions
│   ├── state.py            ← SQLite WAL orchestrace
│   ├── state_base.py       ← DB připojení, migrace, kompozitní indexy
│   ├── state_agents.py     ← registr agentů, watchdog, allowlist příkazů
│   ├── state_issues.py     ← issue CRUD, tagy, workflow, TOTP store, thresholdy
│   ├── watcher.py          ← inotify, hot-reload configu, LDAP re-init, FIM
│   ├── plugin_manager.py   ← dynamické načítání pluginů, hot-reload
│   ├── ollama_service.py   ← AI worker pool, přepínání modelů, llm_semaphore
│   ├── rag.py              ← ChromaDB, nomic-embed-text, BM25 fallback
│   ├── actions.py          ← lifecycle autofixu, SSH exec, ProxyJump
│   ├── notifier.py         ← 13 odchozích kanálů, retry fronta, throttle per severity
│   ├── scheduler.py        ← background maintenance (minutová/hodinová/noční)
│   ├── ssh_utils.py        ← build_ssh_cmd(), sken host klíčů (accept-new)
│   ├── analytics.py        ← TTC, Mann-Kendall, Z-Score, health score, forecast
│   ├── topology.py         ← topologie agentů, SNMP CDP/LLDP
│   ├── snmp_trap.py        ← SNMP trap receiver
│   ├── syslog_receiver.py  ← Syslog UDP/TCP receiver
│   ├── safety.py           ← klasifikátor příkazů, allowed_commands
│   ├── utils.py            ← rate-limit, IP ban, JSON logging, int_param()
│   ├── routes/             ← Flask Blueprints
│   │   ├── main.py         ← login (2FA flow), dashboard
│   │   ├── issues.py
│   │   ├── agents.py
│   │   ├── actions.py
│   │   ├── system.py
│   │   ├── export.py
│   │   ├── integrations.py ← konfigurace odchozích + příchozí webhooky (Grafana/AM/Zabbix)
│   │   └── chat.py
│   ├── plugins/            ← detektorové moduly
│   ├── static/             ← CSS/JS (gzip, ETag+304, cache 1 rok, defer; .min.js buildí se při deployi)
│   └── templates/          ← Jinja2, i18n stringy
├── build_kb.py             ← builder RAG znalostní báze (interaktivní menu, PDF/DOCX/MD)
├── hailo_models.py         ← Hailo TUI správce modelů
├── sentinel_init.py        ← interaktivní instalační wizard (odmítá výchozí hesla)
├── config.yaml.example
├── Makefile                ← make lint / test / build / ci
├── .gitea/workflows/ci.yml ← CI pipeline (pytest + node --check + build)
└── tests/                  ← 181 testů (route, security, integrační, benchmark)

/etc/sentinel/
└── config.yaml             ← hot-reloadovatelná konfigurace (validace jsonschema)

/var/lib/sentinel/
├── secret_key              ← persistentní Flask SECRET_KEY
├── client_api_key          ← auto-generovaný klientský token (mode 600)
└── config_backups/         ← automatické snapshoty před restore (drží 10)

/var/log/sentinel/
├── logs/
│   ├── sentinel_state.db   ← SQLite WAL (issues, telemetrie, agenti, …)
│   └── sentinel.log
└── chroma_db/              ← ChromaDB vector store
```

---

## Stabilita daemona — self-watchdog

Interní watchdog v `__main__.py` polluje `GET localhost:5050/api/health` každý cyklus. Od v2026.06.008 běží HTTP check **v samostatném vlákně** přes **persistentní socket** a DB používá `busy_timeout` — to odstranilo falešné `SIGABRT` killy watchdogu pod zátěží.

```
GET /api/health
  │
  ├── 200 OK → reset web_failures=0, systemd WATCHDOG=1
  │
  └── Timeout/Error → web_failures++
        │
        ├── failures == 5  → log RAM/CPU diagnostiky
        ├── failures == 9  → dump stacků všech vláken
        └── failures >= 10 → self-restart + Teams alert
```

**Integrace se systemd:** unit se generuje s `WatchdogSec=900` a WAL-checkpoint `ExecStartPre`. Pokud `WATCHDOG=1` nedorazí včas, systemd pošle `SIGKILL` a daemon automaticky restartuje.

**Diagnostika:** `faulthandler.enable()` při watchdog abortu vypíše tracebacky všech vláken do journalu (funguje i při drženém GILu).

**Graceful shutdown:** SIGTERM flushne telemetry write buffer a publikuje MQTT `sentinel/status: offline` před ukončením.

**Self-monitoring:** memory watchdog vlákno varuje při RSS > 1,5 GB; self-metriky (RAM, vlákna, hloubka fronty, issues, agenti online, load1) se zapisují do telemetrie každou minutu; backlog AI fronty > 50 vytvoří issue `SENTINEL_SELF_HEALTH`; trvání init fází se profiluje a loguje.

---

## Hot-reload konfigurace

`watcher.py` sleduje `/etc/sentinel/config.yaml` přes inotify. Při `IN_MODIFY`:

1. `time.sleep(1.0)` — čeká na úplné zapsání souboru (inotify firuje při prvním bajtu, ne při close)
2. `load_config()` — znovu načte všechny sekce configu (se substitucí `{SECRET:ENV_VAR}`)
3. `plugin_manager.load_plugins()` — znovu načte detektorové moduly
4. `_reinit_ldap()` — re-inicializuje LDAP manager (nutné pro funkční LDAP login po změně configu)

**SIGHUP** spouští stejný plný reload — config **i** watcher patterns **i** pluginy (`DETECTORS`, `LOG_GROUPS`). Log level lze měnit za běhu bez reloadu přes `/api/admin/log_level`.

**Validace schématu:** kritické klíče (`web.port`, `worker_threads`, `db_retention_days`, …) se validují přes `jsonschema`; neplatný config je odmítnut místo polovičního aplikování.

---

## SQLite WAL — architektura databáze

Veškerý stav je v `/var/log/sentinel/logs/sentinel_state.db` ve WAL (Write-Ahead Logging) režimu. Klíčové tabulky:

| Tabulka | Účel |
|---|---|
| `problems` | Aktivní incidenty — key, status, severity, channel, host, last_line, missing_count |
| `issue_history` | Archivované incidenty vč. `first_seen` → umožňuje analytiku doby řešení; retence 90 dní |
| `actions` | Lifecycle autofixu — command, status, risk_score, dry_run_output, mode, actor |
| `action_audit` | Append-only compliance log — každý lifecycle event s aktérem a časem |
| `config_audit` | Audit změn configu — kdo, kdy, IP, jaké klíče |
| `task_queue` | Fronta AI workerů — status, worker_id (single-consumer garance) |
| `telemetry` | TSDB — metric, value, timestamp (kompozitní indexy, dávkové zápisy) |
| `agents` | Registr agentů — hostname, token, last_seen, status, ip_addresses, version |
| `active_sessions` | Tracking sessions — user, ip, created_at, last_seen, revokovatelné |
| `revoked_sessions` | Revokace přežívající restart |
| `user_totp` | 2FA/TOTP secrets per uživatel |
| `api_keys` | REST API klíče — SHA-256 hash, jemné scopes |
| `issue_tags` | Mapování tag → issue_key |
| `suppress_rules` | False positive patterny pro auto-potlačení (s hit_count) |
| `snooze_rules` | Okna údržby — globální nebo per host (sloupec `hosts` CSV) |
| `custom_patterns` | Uživatelské regex patterny (Pattern Editor) |
| `ssh_execute_log` | Audit log všech SSH příkazů |
| `root_audit` | Log root relací — server, ip (s reverzním DNS), connected_at, is_active |
| `agent_thresholds` | Per-agent alert thresholdy (vynucované při ingestu) |
| `comment_templates` | Uložené šablony komentářů k issue |

**WAL tuning:** `wal_autocheckpoint=200`, `PRAGMA synchronous=NORMAL`, explicitní checkpoint po prune telemetrie. DB leží **mimo** jakýkoliv inotify-watched adresář (sledovaný DB soubor způsoboval nestabilitu na HPC).

**Garbage collection** (`scheduler.py`): dávkové mazání (LIMIT 1000) proti WAL lock kontenci; `prune_issue_history(days=90)`; `VACUUM` po > 10 000 smazaných řádcích. Výchozí retence: telemetrie 2 dny, vyřešené issues 2 dny, historie issues 90 dní.

**Cachování:** `get_active_issues()` má 5s TTL in-memory cache chráněnou double-checked `threading.Lock` (rychlá čtecí cesta bez locku, rebuild pod lockem); dashboard sparkline dotazy se cachují 5 min.

**Agent watchdog:** background vlákno přepne `status` agenta na `OFFLINE`, pokud heartbeat nedorazí do `agent_heartbeat_timeout` sekund (per-agent nebo globální fallback); délka offline se při reconnectu zaznamená do telemetrie.

---

## Bezpečnostní vrstva

| Mechanismus | Implementace |
|---|---|
| 2FA / TOTP | pyotp (RFC 6238), tabulka `user_totp`, dvoukrokový login flow, QR enrollment (qrcode + pillow) |
| Hashování hesel | bcrypt (detekce prefixu `$2b$` v `_check_password()`); `web.password_hash` má prioritu před plaintextem |
| CSRF | Token v session + SameSite=Strict cookie; globální `fetch` wrapper přidává `X-CSRF-Token` na POST/PUT/DELETE |
| Brute-force | Form login + Basic auth: 5 selhání → 300 s IP ban; auto-registrace 10/min per IP; `/api/analyze/*` 10 req/min |
| XSS | `html.escape()` na všech AI odpovědích před vložením do `innerHTML` (obsah logů kontroluje útočník) |
| SSH | `ssh_utils.build_ssh_cmd()` — `accept-new` + pinovaný `UserKnownHostsFile`; `ssh-keyscan` při registraci; regex validace hostname; pre-validace allowlistu příkazů |
| Ověření API klíčů | Timing-safe `hmac.compare_digest(sha256(submitted), stored_hash)`; scopes `read:issues` / `write:actions` / `admin:users` |
| Sessions | Absolutní 12h timeout, refresh role z DB každých 5 min, revokace persistované v DB |
| Secrets | `{SECRET:ENV_VAR}` substituce v configu (env proměnné po použití smazány); `/api/config/view` maskuje secrets jako `***`; persistentní SECRET_KEY v `/var/lib/sentinel/secret_key` |
| Webhooky | HMAC `X-Hub-Signature-256` + replay ochrana přes `X-Webhook-Timestamp` |
| SSRF | `/api/admin/validate_url` odmítá privátní IP rozsahy |
| Validace vstupů | `int_param(value, default, min, max)` na 20+ endpointech — žádné záporné hodnoty do SQL `datetime()` |
| Reverzní proxy | `get_real_ip()` respektuje `X-Forwarded-For` jen z `TRUSTED_PROXIES` |
| Audit | `config_audit`, `ssh_execute_log`, `action_audit`, audit 403/401 přístupů; UI prohlížeč v Settings |
| FIM | SHA-256 kritických souborů kontrolován každou minutu → security issue při změně |
| Symlink containment | Kontrola `os.path.realpath()` na všech file path vstupech |
| Limity uploadů | Max 5 MB, `secure_filename()`, allowlist přípon |
| CSP hlavičky | Content-Security-Policy na všech odpovědích |
| LDAP | Fallback na přímý `ldap3` bind, pokud manager není dostupný |
| Self-check | `/api/admin/security_check` → známka A/B/C/D |

---

## Výkonnostní optimalizace

- **Cachování statiky:** ETag + `max-age` + 304 conditional GET; `Cache-Control: max-age=31536000, immutable` s `?v=<subversion>` fingerprintingem
- **Načítání skriptů:** všechny externí `<script src>` tagy mají `defer`; `<link rel="preload">` pro kritické CSS/JS
- **Gzip komprese:** Flask-Compress level 6, min 2 KB — ~75% úspora přenosu
- **Socket.IO transport:** `['polling', 'websocket']` s `upgrade: true` — startuje přes HTTP long-polling (projde každou proxy), upgraduje na WebSocket pokud lze
- **Backpressure:** frontend SocketIO fronta omezena na 500 s drop-oldest; duplikátní WS zprávy dedupovány v 1s okně
- **Dávkování telemetrie:** `save_telemetry_snapshot()` zapisuje přes buffer, flush periodicky a při SIGTERM
- **DB indexy:** `idx_problems_plugin_ch_ts`, `idx_issue_hist_plugin_ts`, `idx_problems_severity`, `idx_telemetry_cat_metric_ts` — vytvářeny automaticky při startu
- **AI semafor:** serializaci řeší výhradně `execute_ollama()` (vnější re-entrantní acquire dříve způsoboval trvalý deadlock); Ollama HTTP timeout omezen na 90 s
- **Hot read path:** žádné zápisy z `get_pending_actions()` (expirace přesunuta do background smyčky) — odstranilo „UI offline" zatuhnutí pod zátěží agent ingestu
- **Bulk ingest:** `/api/v1/ingest/bulk` přijímá pole alertů v jednom HTTP requestu

---

## CI a testovací sada

- **181 testů**: Flask route testy, security testy (brute force, API scopes, hostname injection, maskování secrets), integrační testy (celý lifecycle issue na reálné DB), výkonnostní benchmark dashboardu
- **CI:** Gitea Actions (`.gitea/workflows/ci.yml`) — pytest + `node --check` + `make build`; lokální `pre-push` git hook
- **Lint:** ruff (`pyproject.toml`), ESLint s `no-redeclare=error`; `make ci` spouští lint + testy
- **Build artefakty:** `.min.js` soubory se buildí při deployi a v gitu nejsou

---

## Integrace Hailo AI HAT 2+

Při `hailo_ollama.enabled: true` v configu:

- Inference requesty směřují na hailo-ollama na `http://localhost:8000` (NPU)
- CPU Ollama na `:11434` slouží jen pro embeddingy (nomic-embed-text)
- Runtime přepnutí modelu přes `hailo_models.py` TUI bez restartu daemona
- `hailo_models.py` — 619řádkové Unicode TUI: htop-style CPU/Mem bary, RX/TX propustnost, NPU architektura + firmware, TPS benchmark graf
