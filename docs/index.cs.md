# Sentinel Commander — Dokumentace (v2026.06.024)

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

**Hybridní AI log monitor a analyzátor pro HPC a enterprise Linux infrastrukturu**

---

## Rychlá navigace

- **[Průvodce nasazením](./DEPLOYMENT.md)** — produkční nasazení celého systému
- **[API Reference](./API.md)** — API pro pluginy a integrace
- **[Řešení problémů](./TROUBLESHOOTING.md)** — časté problémy a jejich řešení

---

## Co je Sentinel?

Sentinel Commander je pokročilý hybridní monitorovací systém s umělou inteligencí určený pro HPC (High-Performance Computing) a enterprise Linux infrastrukturu. Kombinuje **Pull** přístup (inotify tailing logů) s **Push** přístupem (vzdálení Python agenti POSTují telemetrii). Klíčovým prvkem je integrace Hailo AI HAT 2+ NPU (hailo-ollama), lokálního/externího Ollama LLM a ChromaDB (RAG).

Od verze v2026.06.005 prošel projekt 17 release iteracemi zaměřenými na **bezpečnostní hardening** (2FA/TOTP, bcrypt, CSRF, API scopes), **enterprise integrace** (Discord, Telegram, Opsgenie, Zabbix, Gitea, Grafana, S3), **analytiku** (health score, předpověď issues, SLA reporty) a **inženýrskou kvalitu** (CI pipeline, 181 automatizovaných testů, extrahované moduly `notifier.py`/`scheduler.py`).

---

## Co je nového ve v2026.06.024 (oproti v2026.06.005)

### Novinky ve v2026.06.023 → v2026.06.024

| Funkce | Detail |
|---|---|
| **Veřejný `/status` dashboard** | Stránka stavu bez přihlášení: telemetrie CPU/RAM/Disk, anonymizované poslední incidenty, tabulka online/offline agentů, rozpad kategorií infra/agent/security, plně responzivní grid |
| **Mobilní responzivita** | Issue karty přešly z inline stylů na CSS třídy (`issue-row-inner`/`issue-content-area`/`issue-actions`); sekundární akce se skryjí pod 480 px; modal overlay `flex-start` + `overflow-y:auto`, aby byl dialog vždy dosažitelný; header bar už nepřetéká |
| **Oprava CSRF session** | CSRF token se nyní vkládá do session už při renderování — opravuje chat vracející 403 na mobilu i desktopu |
| **Úklid kategorií** | Kategorie `UNKNOWN` normalizována na `OSTATNÍ` v issue kartách i skupinách (DB migrace existujících záznamů) |

### Bezpečnostní hardening

| Funkce | Detail |
|---|---|
| **2FA / TOTP** | Kompletní stack: pyotp (RFC 6238), QR enrollment (Google Authenticator / Authy), dvoukrokový login flow, DB tabulka `user_totp`, admin může 2FA komukoliv deaktivovat |
| **bcrypt hashování hesel** | `web.password_hash: "$2b$12$..."` má prioritu před plaintextem; tlačítko „Hash hesla" v Settings vygeneruje hash; viewer heslo analogicky |
| **CSRF ochrana** | Token v session + SameSite=Strict cookie + globální `fetch` wrapper přidává `X-CSRF-Token` ke všem POST/PUT/DELETE |
| **Brute-force ochrana** | Form login i Basic auth: IP ban po 5 selháních na 300 s; auto-registrace agentů limitována na 10/min per IP |
| **XSS hardening** | Všechny AI odpovědi escapovány přes `html.escape()` před `innerHTML` — obsah logů je pod kontrolou útočníka |
| **SSH hardening** | `ssh_utils.py`: `accept-new` + `UserKnownHostsFile` místo `StrictHostKeyChecking=no`; `ssh-keyscan` při registraci agenta; known_hosts UI (zobrazit / rescan / smazat klíče) |
| **API key scopes** | Jemné: `read:issues`, `write:actions`, `admin:users` — se zpětnou kompatibilitou |
| **Práce se secrets** | `{SECRET:ENV_VAR}` substituce v config.yaml (proměnné po použití smazány z `os.environ`); `/api/config/view` maskuje password/token/secret/api_key jako `***` |
| **Kontrola sessions** | Absolutní 12h timeout (`security.session_max_hours`), refresh role z DB každých 5 min, revokované sessions přežijí restart (DB) |
| **Audit trail** | Tabulka `config_audit` (kdo, kdy, IP, jaké klíče), audit 403/401 přístupů, prohlížeč audit trailu v Settings |
| **SSRF + validace vstupů** | `/api/admin/validate_url` odmítá privátní IP rozsahy; regex validace hostname na všech SSH/ingest endpointech; `int_param()` kontrola mezí na 20+ endpointech |
| **Security self-check** | `/api/admin/security_check` vrací bezpečnostní známku A/B/C/D |

### Notifikace a integrace

| Funkce | Detail |
|---|---|
| **Odchozí kanály** | MS Teams · Slack · PagerDuty · Discord (embeds) · Telegram bot · Opsgenie (Events API v2) · ntfy.sh · Gotify · SMTP e-mail (STARTTLS 587 / SSL 465) · Matrix · Home Assistant · MQTT · obecný Webhook (HMAC-SHA256 + replay ochrana) |
| **Příchozí webhooky** | `/api/inbound/grafana` (legacy + unified alerting) · `/api/inbound/alertmanager` (Prometheus AM) · `/api/inbound/zabbix` (Media Type flat JSON) |
| **Spolehlivost** | Retry fronta s exponenciálním backoffem (30 s/120 s/300 s, max 3 pokusy); throttling per severity (critical/security/root 15 min, high 1 h, medium/low 4 h) |
| **Granularita** | Per-detektor 🔔 toggle, per-kanál toggle, jméno instance v prefixu všech titulků (`[Instance] CHANNEL alert`) |
| **Lifecycle webhooky** | Konfigurovatelné webhooky při CREATED / ACKNOWLEDGED / RESOLVED |
| **Gitea issue sync** | Kritické issues automaticky zakládány v Gitea repozitáři (`GITEA_URL/TOKEN/REPO`) |
| **Grafana anotace** | `_send_grafana_annotation()` při critical/security alertu |
| **Prometheus** | `GET /metrics` scrape endpoint + pushgateway export self-metrik Sentinelu |

### Analytika a AI

| Funkce | Detail |
|---|---|
| **Health score per host** | `/api/agents/<hostname>/health_score` — kompozitní 0–100 se známkou A–D |
| **Předpověď issues** | `/api/analytics/forecast` — lineární regrese, výhled 7 dní |
| **SLA & fatigue reporty** | Tabulka resolution-time, alert-fatigue graf, widget flapping issues, změny od posledního přihlášení |
| **AI kapacitní plánování** | `/api/reports/capacity_plan` — telemetrie agregovaná per host, AI vrací karty HOST/PROBLÉM/DOPORUČENÍ/PRIORITA |
| **Auto-clustering** | `/api/analyze/auto_clusters` — seskupení issues dle pluginu/hostu v 30min oknech, AI pojmenuje root cause |
| **AI postmortem** | `/api/issues/<key>/postmortem` — AI generovaný Markdown postmortem incidentu |
| **Auto-severity & duplikáty** | Severity přiřazená LLM, automatická detekce duplikátů |
| **Týdenní digest** | Obsahuje flapping issues a průměrnou dobu řešení |

### Správa flotily agentů

| Funkce | Detail |
|---|---|
| **Batch SSH** | `POST /api/ssh/batch` — paralelní SSH přes ThreadPoolExecutor (10 vláken, max 50 hostů, 15 s per-host timeout), allowlist kontrolován |
| **Per-agent thresholdy** | `check_agent_thresholds()` vynucováno při každém ingest payloadu; quick-buttons CPU > 90 %, RAM > 90 %, Disk > 85 % |
| **HW metriky přes SSH** | síť (`/proc/net/dev`), GPU (nvidia-smi/rocm-smi), SMART (smartctl), UPS (apcaccess/upsc) |
| **CVE scanner** | `apt list --upgradable` / `dnf --security check-update` per agent |
| **Inventář balíčků** | `dpkg-query` / `rpm -qa` s live filtrem v detailu agenta |
| **QR registrace** | Token modal generuje QR `{hostname, token, ingest_url}`; kopírování tokenu jedním klikem; hromadná rotace tokenů (`/api/agents/rotate_all_tokens`) |
| **Okna údržby** | Snooze pravidla per host; detail agenta zobrazuje vlastní okna |
| **Version drift alert** | Issue při registraci agenta s buildem starším 30 dní; délka offline trackována v telemetrii |

### Provoz a spolehlivost

| Funkce | Detail |
|---|---|
| **Health endpointy** | `/healthz` (Kubernetes/UptimeKuma JSON probe, 503 při chybě DB) · přepracovaná veřejná stránka `/status` (auto-refresh 30 s) |
| **Správa konfigurace** | jsonschema validace kritických klíčů · backup/restore s automatickými snapshoty před restore (drží 10) · diff snapshotů endpoint + UI |
| **Hot reload** | SIGHUP reloaduje config **i** watcher patterns **i** pluginy; `/api/admin/log_level` mění log level za běhu |
| **Graceful shutdown** | SIGTERM flushne telemetry buffer + publikuje MQTT `sentinel/status: offline` |
| **Zálohy** | `/api/admin/backup/download` (tar.gz) + `/api/admin/backup/s3` (upload na S3/MinIO) |
| **File Integrity Monitoring** | SHA-256 hash kritických souborů kontrolován každou minutu → security issue při změně |
| **Ansible runner** | `/api/ansible/run` — validovaná cesta playbooku, streamovaný výstup |
| **Syntetické checky** | HTTP health checky (`SYNTHETIC_CHECKS`), heartbeat URL monitoring, expirace SSL certifikátů (< 14 dní → security issue) |
| **Self-monitoring** | Self-metriky RAM/vlákna/fronta/load každou minutu · memory watchdog (RSS > 1,5 GB → warning) · alert na backlog AI fronty · alert na velikost DB · no-agent alert · profilace startu |

### Výkon

- **Issues cache** s TTL 5 s + double-checked `threading.Lock`; invalidace při zápisu
- **Dávkování zápisu telemetrie** (buffer flushovaný periodicky), dashboard sparklines dotaz cachován 5 min
- **Kompozitní DB indexy** (`idx_problems_plugin_ch_ts`, `idx_issue_hist_plugin_ts`, severity + telemetrie)
- **WAL tuning** — `wal_autocheckpoint=200`, `synchronous=NORMAL`, explicitní checkpoint po prune; VACUUM po > 10 k smazaných řádcích; 90denní retence historie issues
- **HTTP cachování** — ETag + `max-age` + 304 conditional GET pro statiku; `defer` + `preload` načítání skriptů; gzip
- **SocketIO backpressure** — omezená fronta na frontend (500, drop-oldest); dedup WS zpráv v 1s okně
- **Virtual scroll** — issues stránkované po 50 s tlačítkem „Načíst více"

### UI / UX

- Tab **Runbooks** v Tools s CRUD + runbook modalem
- **Moderní interaktivní grafy** — min/max/avg badge, přerušovaná průměrová linie, bohaté tooltipy (dashboard trend, donut s celkovým počtem uprostřed, alert timeline, agent sparklines)
- **Fullscreen overlay issue**, inline komentáře, barevné štítky, drag & drop záložky, mobilní swipe (vpravo = acknowledge, vlevo = delete)
- **Kopie issue jako Markdown**, hromadný CSV export (`Alt+E`), hromadný acknowledge (`Alt+A`), export chatu do Markdownu
- **Přístupnost** — ARIA `role="dialog"`, `aria-modal`, `aria-labelledby` na všech modalech, Escape pro zavření
- **DB management panel** v Settings — velikost, počty záznamů, tlačítka „Prune nyní" a „Agregovat telemetrii"
- **Chat** — kontextové chips s navrženými dotazy, LIVE tag (obohacuje prompt o kontext aktivních issues), Markdown rendering
- **Časová zóna** — `DISPLAY_TZ`, `/api/timezone/info`, `/api/timezone/convert`

### Inženýrská kvalita

- **118 automatizovaných testů** — route testy, security testy (brute force, scopes, hostname injection, maskování secrets), integrační testy (celý lifecycle issue na reálné DB), benchmark dashboardu
- **CI pipeline** — Gitea Actions (`pytest` + `node --check` + `make build`), `pre-push` git hook, `make ci`
- **Linting** — ruff (Python), ESLint s `no-redeclare=error` (JS), pinované `requirements.txt`
- **Refaktoring** — `notifier.py` (všechny odchozí kanály), `scheduler.py` (3úrovňová maintenance smyčka) a `ssh_utils.py` extrahovány z `chat_service.py`
- **CONTRIBUTING.md** — diagram architektury, vývojový workflow, bezpečnostní pravidla

---

## Přehled funkcí

| Oblast | Schopnosti |
|---|---|
| **AI inference** | Hailo-10H NPU (hailo-ollama) · CPU Ollama · external API · runtime přepínání modelu |
| **RAG znalostní báze** | ChromaDB + nomic-embed-text · BM25 TF×IDF fallback · vlastní upload (.md/.txt/.pdf/.docx/.csv) · reindex jedním klikem |
| **Hybridní telemetrie** | Pull (inotify logy) + Push (agenti přes Bearer token) · více IP adres na agenta · tracking verze agenta (SHA) |
| **Autofix** | AI navrhne opravu → admin Schválit/Zamítnout → SSH exec na mgmt nodu · allowlist příkazů · autonomní exec |
| **Prediktivní analytika** | TTC (Time-To-Critical) pro disky · Mann-Kendall trend test · předpověď lineární regresí · kapacitní plánování |
| **Bezpečnostní profiler** | Brute-force, sudo abuse, CVE scan, neoprávněné porty, honeypot, FIM, expirace SSL |
| **Notifikace** | 13 odchozích kanálů · 3 příchozí webhooky · retry fronta · throttle per severity · per-detektor/kanál toggles |
| **Prometheus** | `GET /metrics` scrape + pushgateway export; auth přes scrape_token |
| **Dashboard** | Stat karty · interaktivní min/max/avg grafy · trend chart · donut · health trend · flapping widget · live hodiny |
| **Autentizace** | viewer / admin / superadmin · LDAP (lldap + OpenLDAP) · **2FA/TOTP** · **bcrypt** · rate-limit + IP ban · **CSRF** |
| **Issues UI** | Bulk select · filtrování · group-collapse · printable report · CSV export · historie · pravidla potlačení · tagy · severity · počítadlo výskytů · batch AI analýza · fullscreen · štítky · inline komentáře |
| **Workflow issues** | `active` → `acknowledged` → `validating` → `resolved` · eskalační pravidla · lifecycle webhooky |
| **Auto-remediace** | Jednorázová SSH oprava · allowed_commands s `auto_execute` · AUTOFAIL issues · SSH jump host (ProxyJump) · Ansible runner |
| **REST API klíče** | Jemné scopes (`read:issues`, `write:actions`, `admin:users`) · SHA-256 hash v DB · UI v Settings |
| **Plugin hot-reload** | `POST /api/plugins/reload` · SIGHUP plný reload · Pattern Editor s regex testerem + AI návrhy patternů |
| **Telemetrie** | Detekce anomálií (3σ) · pevné thresholdy · per-agent thresholdy · InfluxDB export · heatmap · health score historie |
| **Topologie** | Mapa topologie agentů · graf závislostí pluginů · SNMP CDP/LLDP · Canvas force-directed graf |
| **SSH akce** | Jump host (ProxyJump) · SSH modal (admin+) · streaming výstup (SSE) · **batch SSH** · správa known_hosts |
| **API dokumentace** | `GET /api/docs` — Swagger UI · `GET /api/openapi.json` — OpenAPI 3.0 spec |
| **Hailo TUI** | `hailo_models.py` — Unicode TUI správce modelů: htop-style CPU/Mem bary, RX/TX, NPU arch+FW, TPS benchmark graf |
| **UI i18n** | Čeština (výchozí) · angličtina toggle · `localStorage` persistence · konfigurace časové zóny |
| **Bezpečnost** | Symlink containment · limit uploadů (5 MB) · secure_filename · timing-safe ověření tokenů · CSP hlavičky · maskování secrets · SSRF guard |

---

## Architektura

```
  Log soubory ──inotify──▶ watcher.py ──▶ plugins[] ──▶ api.report_problem()
  Vzdálení agenti ──POST──▶ /api/v1/agent/ingest            │
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
  (NPU :8000)       (:11434)        API        (maintenance)    (13 kanálů)
```

### Hlavní moduly

| Soubor | Zodpovědnost |
|---|---|
| `chat_service.py` | Flask/SocketIO app factory, RBAC, WebSocket |
| `auth.py` | Autentizace, LDAP, 2FA/TOTP, bcrypt, sessions, ověření API klíčů |
| `state.py` (`state_base/issues/agents`) | SQLite WAL orchestrace — issues, telemetrie, agenti |
| `watcher.py` | inotify filesystem eventy, hot config reload, FIM |
| `plugin_manager.py` | Dynamické načítání pluginů, routing patternů, hot-reload |
| `ollama_service.py` | AI worker thread pool, přepínání modelů |
| `rag.py` | ChromaDB, nomic-embed-text, BM25 fallback |
| `actions.py` | Lifecycle autofixu — create, approve, reject, SSH exec |
| `notifier.py` | Všechny odchozí notifikace + retry fronta + throttling |
| `scheduler.py` | Background maintenance (minutová / hodinová / noční úroveň) |
| `ssh_utils.py` | Centrální SSH bezpečnost — `build_ssh_cmd()`, sken host klíčů |
| `analytics.py` | TTC, Mann-Kendall, Z-Score, health score, forecast |
| `topology.py` | Topologie agentů, SNMP CDP/LLDP |
| `routes/` | Flask Blueprints: main, issues, agents, actions, system, export, integrations, chat |

---

## Datové toky

### A. Ingest & detekce

1. Log řádek zapsán do `/var/log/sentinel/logs/` → inotify event
2. `watcher.py` čte nové řádky přes `mmap`
3. `PluginManager` routuje řádky na odpovídající detektory dle masky souboru
4. Detektor generuje unikátní klíč (např. `DISK_FULL|proxmox01|/data`)
5. Stav zapsán do tabulky `problems` → task vložen do `task_queue`
6. Push cesta: agenti POSTují `/api/v1/agent/ingest` (nebo `/api/v1/ingest/bulk` pro dávky); pole `metrics` se kontroluje proti per-agent thresholdům

### B. AI inference + RAG

1. AI worker vyzvedne task z `task_queue`
2. Načte prompt šablonu dle kanálu (security, clusters, infra, root, icinga)
3. RAG: ChromaDB dotaz → relevantní kontext vložen do system promptu
4. Prompt odeslán do Ollama (NPU/CPU/external)
5. Pokud odpověď obsahuje remediation skript → `actions.py` vytvoří `pending` akci

### C. Zpětnovazební smyčka remediace

1. `actions.py` vytvoří DB záznam s navrženým SSH příkazem
2. Frontend dostane WebSocket event `new_action`
3. Admin s rolí `admin` nebo `superadmin` klikne Schválit nebo Zamítnout
4. Při schválení: SSH připojení na management node → vykonání příkazu (allowlist pre-validován)
5. STDOUT/STDERR zalogován → incident přechází do stavu `validating`

### D. Notifikační pipeline

1. Issue uloženo → `notifier.send_notification()` fan-out na všechny zapnuté kanály
2. Nejdřív se kontrolují per-detektor a per-kanál toggles
3. Aplikuje se throttle per severity (critical 15 min … low 4 h)
4. Selhání jdou do retry fronty (backoff 30 s → 120 s → 300 s)
5. Lifecycle webhooky se spouští při CREATED / ACKNOWLEDGED / RESOLVED

---

## Workflow issues

```
  detekováno ──▶  active  ──▶  acknowledged (tlačítko ✓✓)
                    │                │
                    │           validating ──▶ resolved
                    │
                    └──▶ (auto-resolved detektorem nebo expiry pravidlem)
```

**Eskalační pravidla:** Pokud issue zůstane `active` nebo `acknowledged` déle než N hodin bez vyřešení, severity se automaticky zvýší na další úroveň.

**Lifecycle webhooky** mohou notifikovat externí systémy při každém přechodu a kritické issues lze zrcadlit do **Gitea**.

---

## Instalace

```bash
git clone <repo> /opt/Sentinel
sudo bash /opt/Sentinel/install.sh        # Debian/Ubuntu/RHEL/Rocky/Pi OS
sudo python3 /opt/Sentinel/sentinel_init.py   # interaktivní konfigurační wizard
sudo systemctl enable --now sentinel
```

Setup wizard odmítá výchozí hesla, generuje systemd unit s `WatchdogSec=900` a WAL-checkpoint `ExecStartPre` a vytváří `/var/lib/sentinel`.

### Klíčová konfigurace (config.yaml)

```yaml
web:
  port: 5050
  password_hash: "$2b$12$..."      # bcrypt — má prioritu před plaintext `password`

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
  scrape_token: "{SECRET:PROM_TOKEN}"   # substituce z env proměnné

telemetry_alerts:
  cpu_critical: 95
  disk_critical: 95
  temp_critical: 85

fim:
  enabled: true
  paths: [/etc/passwd, /etc/shadow, /etc/ssh/sshd_config]
```

---

## Požadavky

- Python 3.13+ · Flask · Flask-SocketIO · ChromaDB · paho-mqtt
- `pyotp` (2FA) · `qrcode` + `pillow` (QR enrollment) · `bcrypt` · `jsonschema`
- Ollama s `nomic-embed-text` (pro embeddingy)
- **Volitelně:** Hailo AI HAT 2+ s hailo-ollama 5.3.0 pro NPU inferenci

---

## Ekosystém komponent

| Komponenta | Popis | Port |
|---|---|---|
| **Sentinel** | Centrální server (tato dokumentace) | 5050 |
| **sentinel-agent** | Push agent na každém monitorovaném nodu | — |
| **sentinel-overhealth** | SSH pull orchestrátor (cron) | — |
| **sentinel-plugins** | 11 detektorových pluginů | — |
| **sentinel-alert** | Standalone síťový bezpečnostní dashboard (vč. MikroTik + PiHole) | 5056 |
| **sentinel-hw** | Fyzický RPi robot | 5055 |
| **sentinel-app** | Android mobilní klient | — |
| **sentinel-console** | TUI terminálový klient | — |
