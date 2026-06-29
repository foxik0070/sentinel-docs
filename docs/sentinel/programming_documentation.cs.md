# Sentinel Commander — Programátorská dokumentace (v2026.06.024)

Určeno pro vývojáře a DevOps inženýry píšící vlastní detekční pluginy, integrující Sentinel s externími nástroji nebo upravující jádro systému.

---

## Architektura pluginů

Sentinel načítá pluginy dynamicky ze složky `plugins/`. Každý plugin musí dědit z `BaseDetector`.

```
Log soubor (disk)
    │ inotify on_modified / on_moved
    ▼
watcher.py ──řádky──▶ plugin_manager.py ──match(regex)──▶ MyDetector.process(lines)
                                                                │
                                              api.report_problem(key, payload)
                                                                │
                                                            state.py (SQLite)
```

### Napsání vlastního detektoru

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

            # Volitelně: zařadit AI analýzu
            api.enqueue_ai_task(f"Analyzuj: {line.strip()}", channel="infra")
```

Registrace v `config.yaml`:

```yaml
detectors:
  my_detector:
    enabled: true
    file_mask: "myapp.log"
    threshold: 5
    notify: true        # per-detektor notifikační toggle
```

---

## Core API (`api.py`)

| Metoda | Popis |
|---|---|
| `report_problem(key, data)` | Vytvoří nebo aktualizuje incident. Stejný klíč = update `last_seen` + `missing_count`. |
| `resolve_problem(key)` | Uzavře incident (auto-heal). Spustí WebSocket event `resolve`. |
| `get_problem(key)` | Vrátí aktuální DB řádek pro klíč, nebo `None`. |
| `enqueue_ai_task(prompt, channel)` | Vloží task do fronty AI workerů. Neblokující. |
| `save_telemetry_snapshot(metric, value, host)` | Zapíše time-series bod (bufferovaný/dávkový zápis). |
| `get_infrastructure_label(file_path)` | Extrahuje `SERVER: <hostname>` kontext z prefixu log řádky. |
| `add_root_audit(server, ip)` | Idempotentní audit root relace s reverzním DNS. |
| `notify_teams(message, channel)` | Pošle Teams webhook zprávu přímo (mimo frontu). |

### Notifier (`notifier.py`)

Odchozí notifikace byly extrahovány z `ChatService` do samostatného modulu:

```python
from sentinel.notifier import send_notification
send_notification(title, message, severity="critical", channel="security")
```

- Fan-out na všechny zapnuté kanály: Teams, Slack, PagerDuty, Discord, Telegram, Opsgenie, ntfy.sh, Gotify, SMTP, Matrix, Home Assistant, MQTT, obecný Webhook
- Každý kanál běží přes `_with_retry()` — selhání jdou do retry fronty (deque maxlen 200), kterou vlákno `NotifierRetry` zkouší znovu s backoffem 30 s/120 s/300 s (max 3 pokusy)
- Throttle per severity: `critical/security/root` 15 min · `high` 1 h · `medium/low/agent/infra` 4 h
- Respektuje per-detektor (`notify:` v YAML) a per-kanál toggles
- Jméno instance v prefixu všech titulků: `[Instance] CHANNEL alert`

### Scheduler (`scheduler.py`)

Background maintenance smyčka extrahovaná z `ChatService`, tři úrovně — minutová (FIM, heartbeat URL, self-metriky), hodinová (session GC, geo-IP cache, joke log), noční (prune, VACUUM, týdenní digest).

---

## Hot-reload pluginů

Pluginy lze reloadovat bez restartu daemona:

**Z Web UI:** Settings → tlačítko Plugin hot-reload
**Přes API:** `POST /api/plugins/reload` (vyžaduje `superadmin` API klíč nebo session)
**Signálem:** `kill -HUP <pid>` — reloaduje config + watcher patterns + pluginy

Plugin Manager používá `importlib.util` k načtení každého modulu do izolovaného `sys.modules` namespace, kompiluje regex patterny a instancuje nové detektory.

---

## Pattern Editor (patterny z UI)

Vlastní patterny definované v UI se ukládají do tabulky `custom_patterns` a Plugin Manager je načítá vedle Python pluginů:

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

Tyto patterny fungují jako lehké inline detektory — bez Python kódu. Dostupné přes `GET /api/patterns` a `POST /api/patterns`. Editor obsahuje live regex tester a **AI návrhy patternů** (`/api/patterns/suggest`) generované z historických issues.

---

## REST API (externí integrace)

Všechny endpointy vyžadují autentizaci. Metody přijímající JSON potřebují `Content-Type: application/json`. CSRF token (`X-CSRF-Token`) je vyžadován pro browser-session POST/PUT/DELETE; Bearer-token API volání jsou vyjmuta.

### Možnosti autentizace

1. **Session cookie** — získaná přes `POST /api/login` (+ volitelný TOTP krok)
2. **Bearer token** — `Authorization: Bearer <api_key>` s jemnými scopes: `read:issues`, `write:actions`, `admin:users`
3. **Basic Auth** — `Authorization: Basic base64(user:pass)` (pouze agent ingest)

### Klíčové endpointy

| Metoda | Cesta | Auth scope | Popis |
|---|---|---|---|
| POST | `/api/login` | — | `{username, password}` → session cookie (TOTP krok pokud aktivní) |
| GET/POST | `/api/2fa/status\|setup\|enable\|disable` | session | Lifecycle TOTP enrollmentu |
| GET | `/api/v1/issues` | read:issues | Aktivní incidenty jako JSON (vč. `plugin_name`) |
| POST | `/api/v1/agent/ingest` | write | Push telemetrie agenta (+ `metrics` → kontrola thresholdů) |
| POST | `/api/v1/ingest/bulk` | write | Pole alertů v jednom requestu |
| GET | `/api/issues/<key>/markdown` | read:issues | Issue vyrenderované jako Markdown |
| POST | `/api/issues/<key>/postmortem` | read:issues | AI generovaný Markdown postmortem |
| GET | `/api/v1/actions` | read:issues | Seznam pending akcí |
| POST | `/api/v1/actions/<id>/approve` | write:actions | Schválit a SSH-vykonat |
| POST | `/api/v1/actions/<id>/reject` | write:actions | Zamítnout návrh |
| GET | `/api/v1/actions/<id>/output` | read:issues | Stream výstupu (SSE) |
| POST | `/api/ssh/batch` | admin | Paralelní SSH na až 50 hostů |
| POST | `/api/agents/<hostname>/packages` | admin | Inventář balíčků přes SSH |
| GET | `/api/agents/<hostname>/cve_scan` | admin | Čekající security aktualizace |
| GET | `/api/agents/<hostname>/hw_metrics` | admin | net/GPU/SMART/UPS přes SSH |
| GET | `/api/agents/<hostname>/health_score` | read:issues | Kompozitní 0–100 + známka A–D |
| GET/POST/DELETE | `/api/agents/<hostname>/ssh_keys` | admin | Správa known_hosts |
| POST | `/api/agents/rotate_all_tokens` | superadmin | Hromadná rotace tokenů agentů |
| GET | `/api/analytics/resolution_time` | read:issues | SLA statistiky |
| GET | `/api/analytics/flapping` | read:issues | Nejčastěji se opakující issues |
| GET | `/api/analytics/alert_fatigue` | read:issues | False positive statistiky per plugin |
| GET | `/api/analytics/forecast` | read:issues | 7denní předpověď lineární regresí |
| POST | `/api/analyze/auto_clusters` | read:issues | Algoritmické clusterování + AI root cause |
| POST | `/api/reports/capacity_plan` | read:issues | AI kapacitní plánování |
| GET | `/api/predictions/capacity` | read:issues | TTC pro disk/RAM |
| POST | `/api/ansible/run` | admin | Validovaný běh playbooku se streamovaným výstupem |
| GET | `/api/topology/data` | read:issues | Topologie agentů — nodes + edges |
| POST | `/api/plugins/reload` | admin | Hot-reload všech pluginů |
| GET/POST | `/api/patterns` | read/admin | CRUD vlastních patternů |
| POST | `/api/patterns/suggest` | admin | AI návrhy regex patternů |
| POST | `/api/apikeys` | superadmin | Vytvořit API klíč (`{name, scope}`) |
| DELETE | `/api/apikeys/<id>` | superadmin | Revokovat API klíč |
| POST | `/api/config/hash_password` | superadmin | Vygenerovat bcrypt hash |
| GET | `/api/config/history/diff?from=X&to=Y` | superadmin | Diff dvou config snapshotů |
| GET | `/api/admin/backup/download` | superadmin | tar.gz záloha |
| POST | `/api/admin/backup/s3` | superadmin | Upload zálohy na S3/MinIO |
| GET/POST | `/api/admin/log_level` | superadmin | Runtime log level |
| GET | `/api/admin/audit_trail` | superadmin | Config + SSH + action audit |
| GET | `/api/admin/security_check` | superadmin | Bezpečnostní známka A/B/C/D |
| GET | `/api/admin/db_stats` | superadmin | Velikost DB + počty záznamů |
| GET | `/api/timezone/info` · `/api/timezone/convert` | read | Pomocníci pro časovou zónu |
| GET | `/metrics` | scrape_token | Prometheus metrics endpoint |
| GET | `/healthz` | — | K8s/UptimeKuma probe (503 při chybě DB) |
| GET | `/api/docs` | — | Swagger UI |
| GET | `/api/openapi.json` | — | OpenAPI 3.0 spec |
| GET | `/api/kb/reindex` | admin | Spustit RAG reindex |

---

## Příchozí webhooky (Grafana / Alertmanager / Zabbix)

Sentinel přijímá příchozí webhooky z externích monitorovacích nástrojů na třech dedikovaných endpointech:

| Endpoint | Formát |
|---|---|
| `POST /api/inbound/grafana` | Grafana legacy **i** unified alerting payloady |
| `POST /api/inbound/alertmanager` | Formát Prometheus Alertmanager webhooku |
| `POST /api/inbound/zabbix` | Zabbix Media Type flat JSON |

```http
POST /api/inbound/grafana
Authorization: Bearer <api_key>
Content-Type: application/json

{ "alerts": [ { "labels": {"alertname": "DiskFull", "instance": "hpc-node-01"},
                "annotations": {"summary": "disk >90%"}, "status": "firing" } ] }
```

Payload je normalizován a vložen do standardní issue pipeline (stejně jako volání `report_problem()` z detektoru). Auth webhooku podporuje Bearer token i HMAC `X-Hub-Signature-256` s `X-Webhook-Timestamp` replay ochranou.

**Odchozí lifecycle webhooky:** nakonfigurujte URL volané při `CREATED` / `ACKNOWLEDGED` / `RESOLVED`; kritické issues lze navíc synchronizovat do **Gitea** (`GITEA_URL/TOKEN/REPO`) a anotovat v **Grafaně** (`grafana_annotations.url/api_key`).

---

## Schéma databáze — klíčové tabulky

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
    depends_on   TEXT            -- JSON seznam závislých issue klíčů
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

### `issue_history` (archiv)

`_archive_problem()` kopíruje `first_seen` z `problems`, což umožňuje analytiku doby řešení (`/api/analytics/resolution_time`). Scheduler maže po 90 dnech.

---

## RAG znalostní báze (rag.py + build_kb.py)

### Přidávání dokumentů

```bash
# Rebuild z /opt/Sentinel/knowledge_base/ — interaktivní menu, podpora PDF/DOCX/MD
python3 build_kb.py

# Podporované formáty: .md .txt .pdf .docx .csv
# Nebo upload přímo přes Web UI (Settings → Knowledge Base)
```

### Tok dotazu

1. Dotaz uživatele → `RAGEngine.search(query, top_k=3)`
2. Vektorizace dotazu přes `nomic-embed-text`
3. HNSW nearest-neighbour vyhledávání v ChromaDB
4. Top-K chunky vloženy do system promptu
5. Pokud ChromaDB není dostupná → BM25 TF×IDF fallback přes tokenizované textové bloky

---

## AI worker pool (ollama_service.py)

```
task_queue (DB)
      │
  ┌───┴───────┐
  │ Worker-0  │ ← vyzvedne task, zamkne worker_id
  │ Worker-1  │
  │ Worker-N  │ ← konfigurovatelné přes WORKER_THREADS
  └───────────┘
      │
  Ollama API
  POST /v1/chat/completions   (timeout 90 s)
      │
  Failover: 400 error → legacy /api/chat formát
      │
  Odpověď → připojena k issue v DB
          → emit WebSocket event
```

Workery rotují donekonečna dokud `state.shutdown_event.is_set()`. Tasky se při chybě nikdy automaticky nezařazují znovu (prevence nekonečných retry smyček na špatném vstupu).

> **Pravidlo souběžnosti:** nikdy neberte `llm_semaphore` okolo volání `execute_ollama()` — funkce ho bere interně; re-entrantní acquire trvale zadeadlockuje celou AI pipeline.

---

## Vývojový workflow

```bash
make lint        # ruff + ESLint
make test        # pytest — 181 testů
make ci          # lint + test (stejné jako CI)
make build       # minifikace JS (.min.js nejsou v gitu)
```

- CI běží v Gitea Actions (`.gitea/workflows/ci.yml`): pytest + `node --check` + build
- `pre-push` git hook spouští JS check + pytest lokálně
- Viz `CONTRIBUTING.md` — diagram architektury, vývojový workflow a bezpečnostní pravidla (např. každý nový endpoint potřebuje auth + validaci vstupů + route test)
