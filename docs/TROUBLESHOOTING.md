# Sentinel Ecosystem — Troubleshooting Guide (v2026.06.024)

Common issues and solutions across all Sentinel components.

---

## Sentinel Core (port 5050)

### Service won't start

```bash
journalctl -u sentinel -n 50 --no-pager
```

**Common causes:**

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: sentinel` | Wrong interpreter or venv not activated | Run with `venv/bin/python -m sentinel` |
| `sqlite3.OperationalError: no such table` | DB schema outdated | Delete `sentinel_state.db` and restart (data loss) |
| `pysqlite3 not found` | RHEL/Rocky with old SQLite | `pip install pysqlite3-binary` |
| `Address already in use :5050` | Another process on port | `fuser -k 5050/tcp` |
| `ChromaDB segfault` | SQLite < 3.35 without pysqlite3-binary | See pysqlite3 fix above |

---

### LDAP login fails after config reload

**Symptom:** Login worked before, now returns 401. No error in logs.

**Cause:** `watcher.py` detects config change via `IN_MODIFY` (fires on first byte), reads the file before it's fully written → `ldap_manager` re-initialises with empty config → remains `None`.

**Fix (v2026.06.005 resolved this):** Update to latest version. The fix adds `time.sleep(1.0)` in `ConfigHandler.on_modified()` before reading config. Fallback: direct `ldap3` bind works even if `ldap_manager` is `None`.

**Manual workaround (older versions):**
```bash
sudo systemctl restart sentinel
```

---

### LDAP login fails on OpenLDAP

**Symptom:** Works with lldap, fails with OpenLDAP.

**Cause:** OpenLDAP uses `ldaps://` prefix in the host field and may require a different `user_object_filter`.

**Fix:**
```yaml
ldap:
  host: "ldaps://ldap.example.com"
  base_dn: "dc=example,dc=com"
  user_object_filter: ""   # leave empty for OpenLDAP
```

---

### AI / Autofix produces no response

**Symptom:** Autofix button does nothing, AI chat returns empty.

**Steps:**

1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Check queue depth: `GET /api/status` → `queue_depth`
3. Check AI errors: `GET /api/status` → `ai_errors`
4. Check worker logs: `journalctl -u sentinel | grep "AI Worker"`

**Common causes:**

| Cause | Fix |
|---|---|
| Ollama not running | `systemctl start ollama` |
| Model not pulled | `ollama pull llama3.2` |
| External API 400 error | Fixed in v2026.06.004 — update. The `messages` parameter was ignored, causing empty responses. |
| Config `workers: 0` | Set `workers: 1` minimum |

---

### Socket.IO shows "offline" badge behind reverse proxy

**Symptom:** Dashboard shows red "offline" badge despite server running. Seen after adding Nginx/Cloudflare.

**Cause (pre-v2026.06.004):** Transport was `['websocket']` only — fails when proxy doesn't support WebSocket upgrade.

**Fix (v2026.06.004):** Updated to `['polling', 'websocket']` with `upgrade: true`. Update to latest version.

**Manual Nginx fix (older versions):**
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 86400;
```

---

### Log groups disappear after config reload

**Symptom:** After editing and saving `config.yaml`, custom log groups vanish from the UI.

**Cause (pre-v2026.06.005):** `IN_MODIFY` fires on first written byte. `load_config()` reads an incomplete file → `LOG_GROUPS = {}`.

**Fix:** Update to v2026.06.005. Added `time.sleep(1.0)` delay in config reload handler.

---

### Chat input saved as password by browser

**Symptom:** Browser password manager offers to save the AI chat input as a password.

**Fix (v2026.06.005):** Input type changed to `search` with `autocomplete="new-password"` on all password fields. Update to latest.

---

### AI query hangs forever — only `kill -9` helps

**Symptom:** One AI request (correlate / trend report / active issues) never returns; all subsequent AI calls hang; eventually systemd kills the service on stop timeout.

**Cause (pre-v2026.06.006):** routes acquired `llm_semaphore` *and then* called `execute_ollama()`, which acquires the same `Semaphore(1)` internally — a re-entrant acquire deadlocked the whole AI pipeline.

**Fix (v2026.06.006):** all outer acquires removed; serialisation is owned exclusively by `execute_ollama()`. Ollama HTTP timeout also reduced 600 s → 90 s so a single stuck call cannot hold a worker for 10 minutes.

---

### Web UI goes "offline" under agent ingest load

**Symptom:** Dashboard intermittently unreachable while many agents are pushing; recovers by itself.

**Cause (pre-v2026.06.006):** `get_pending_actions()` performed a DB **write** (prune) on the hot read path of every `/api/status_check` poll; it collided with agent ingest under `db_lock`, request threads piled up, and the accept loop starved.

**Fix (v2026.06.006):** prune moved to the background `action_cleanup_loop`. Also recommended: nginx `limit_conn 10` per IP and serving `/static/` directly (see [Deployment](./DEPLOYMENT.md)).

---

### Watchdog kills the service with SIGABRT

**Symptom:** `systemd: sentinel.service watchdog timeout` followed by SIGABRT, even though the web UI responded.

**Cause (pre-v2026.06.008):** the watchdog's HTTP self-check ran in the main loop and could be blocked by a slow DB operation.

**Fix (v2026.06.008):** persistent socket + HTTP check moved to its own thread + SQLite `busy_timeout`. `faulthandler.enable()` now dumps all thread tracebacks to the journal on abort for diagnosis.

---

### No modal windows open at all

**Symptom:** Every button that should open a modal silently does nothing; browser console shows `SyntaxError ... redeclaration`.

**Cause (pre-v2026.06.012):** a duplicate `const` declaration in `script-modals.js` made the browser reject the entire minified bundle.

**Fix (v2026.06.012):** renamed + ESLint `no-redeclare=error` in CI prevents regressions. `.min.js` artefacts are now built at deploy (`make build`), not committed.

---

### POST/PUT/DELETE requests return 403

**Symptom:** Scripted calls using a **session cookie** fail with 403 after upgrading to ≥ v2026.06.012.

**Cause:** CSRF protection — browser-session mutations require the `X-CSRF-Token` header.

**Fix:** use a Bearer API key for scripts (exempt from CSRF), or read the CSRF cookie and send it back as `X-CSRF-Token`.

---

### Locked out by 2FA

**Symptom:** User lost the TOTP device and cannot log in.

**Fix:** any admin can disable 2FA for the user via Settings → 2FA (or `POST /api/2fa/disable`). Last-resort on the server:

```bash
sqlite3 /var/log/sentinel/logs/sentinel_state.db \
  "DELETE FROM user_totp WHERE username='<user>';"
```

---

### Issues grouped under UNKNOWN category

**Symptom:** Some issues land in an `UNKNOWN` group with wrong colors.

**Cause:** detectors stored `"cluster": "UNKNOWN"` in details, and uppercase channel types (`INFO`, `CLUSTERS`) missed the lowercase color map.

**Fix (v2026.06.008 + v2026.06.012):** values normalised; unknown groups map to `OSTATNÍ`/other. Update to latest.

---

## sentinel-agent

### Agent shows as OFFLINE in Sentinel UI

**Symptom:** Agent is running but shows OFFLINE.

**Steps:**

```bash
# Check agent is posting
journalctl -u sentinel-agent -f

# Test connectivity
curl -s -X POST https://sentinel.example.com/api/v1/agent/ingest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"test","channel":"agents","data":{"test":1}}'
```

**Common causes:**

| Cause | Fix |
|---|---|
| Wrong API key | Re-copy token from Sentinel UI |
| Firewall blocking outbound HTTPS | Check `ufw` / `iptables` on agent node |
| `boot_delay_sec` still running | Wait 90 s after node restart |
| Agent version mismatch | `git pull && systemctl restart sentinel-agent` |

---

### False positives on startup

**Symptom:** Flood of alerts right after node reboot.

**Fix:** Increase `boot_delay_sec` in `agent_config.yaml`:
```yaml
agent:
  boot_delay_sec: 120   # wait 2 min for all services to start
```

---

### Agent issues vanish after Sentinel server restart

**Symptom:** Active agent-reported issues auto-resolve right after the central server restarts, even though the underlying problem persists.

**Cause:** the agent originally pushed only deltas; after a server restart the server "forgot" issues and never received a re-report, so they auto-resolved.

**Fix (2026-06):** the agent now **re-affirms all active issues every cycle**. Update the agent (`git pull && systemctl restart sentinel-agent`).

---

## sentinel-alert

### Globe not displaying attacks

**Symptom:** 3D globe is empty, no attack arcs.

**Causes:**

| Cause | Fix |
|---|---|
| `GeoLite2-City.mmdb` missing | Download from MaxMind, place in `data/` |
| All records have `lat=0` | `collector.py` ran before GeoIP was in place. Re-run collector or wait for ISP enrichment. |
| fail2ban SSH key not distributed | `ssh-copy-id -i conf/id_ed25519.pub root@<host>` |

---

### Work mode — USERS panel empty

**Symptom:** Users panel shows no data after running external WHO collector.

**Cause:** `periodic_who_collector` in `tasks.py` was deleting external data every 60 s.

**Fix (2026-05-26):** Update to latest version. The collector now exits immediately in work mode when a WHO file is configured.

---

### Work mode — TOP COUNTRIES empty

**Symptom:** Top Countries panel shows no data in work mode.

**Cause:** `/api/stats/countries` counted only from `attacks` table; work mode data lives in `ban_history`.

**Fix (2026-05-26):** Update to latest. Added `_computeCountriesFromHistory()` fallback.

---

## sentinel-overhealth

### Logs not updating

```bash
ls -la /var/log/sentinel/logs/
# Check timestamps — should be updated every 5 min

# Run manually to see errors
sudo ./sentinel_orchestrator.py --workers 5

# Check cron
crontab -l | grep sentinel
```

**Common causes:**

| Cause | Fix |
|---|---|
| SSH key not distributed | `ssh-copy-id -i conf/id_ed25519.pub root@<node>` |
| Node in blacklist pattern | Check `BLACKLIST_PATTERNS` in script |
| Node offline | Check `availability.log` for HOST_DOWN |
| `/var/log/sentinel/logs/` missing | `mkdir -p /var/log/sentinel/logs/` |

---

### "database is locked" errors

**Symptom:** Overhealth logs show `sqlite3.OperationalError: database is locked`.

**Cause:** Multiple concurrent writes from many workers without WAL mode or adequate timeouts.

**Fix:** Sentinel's `state.py` uses WAL mode with batched writes. If running a custom script directly against the DB, add `PRAGMA journal_mode=WAL` and use `timeout=30`.

---

## sentinel-hw (Raspberry Pi)

### Display not working (ST7789)

```bash
# Check SPI enabled
ls /dev/spidev*   # should show /dev/spidev0.0

# Enable SPI
sudo raspi-config nonint do_spi 0
sudo reboot
```

Ensure CS pin version of the display is used (the display requires an explicit CS pin).

### NeoPixels not working with TTS enabled

**Cause:** GPIO 18 is used by both NeoPixel and I2S BCLK (TTS).

**Fix:** Move NeoPixel to GPIO 12:
```yaml
hardware:
  leds:
    pin: 12    # not 18 when TTS is enabled
  tts:
    enabled: true
```

### Web UI unreachable

```bash
journalctl -u sentinel-hw -f
# Check if port 5055 is in use:
ss -tlnp | grep 5055
```

---

## sentinel-docs (MkDocs)

### Build fails with "Navigation warning"

**Cause:** A file listed in `mkdocs.yml` nav doesn't exist.

```bash
cd sentinel-docs
./venv/bin/mkdocs build --strict 2>&1 | grep -i "warn\|error"
```

Fix: Check `mkdocs.yml` nav entries match actual file names in `docs/`.

### i18n plugin errors

```bash
pip install mkdocs-static-i18n
# Ensure docs have both .md and .cs.md versions for each file
```

### Language switch to /cs adds a port to the URL and breaks

**Symptom:** Clicking the CS/EN switcher navigates to `https://sentinel-docs.example.com:8000/cs/` (internal port leaks into the URL) and the page fails to load. Removing the port manually works.

**Cause:** `/cs` (without trailing slash) triggers a **301 redirect** to `/cs/`. With nginx's default `port_in_redirect on`, the redirect `Location` header includes the port nginx is listening on internally — which is not reachable from outside.

**Fix (nginx vhost serving the docs):**

```nginx
server {
    ...
    port_in_redirect off;      # never put the listen port into redirects
    absolute_redirect off;     # send relative Location headers
}
```

If the docs are reverse-proxied (e.g. to `mkdocs serve` or another nginx), also make sure the proxy passes the original host without port:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;   # NOT $host:$server_port
}
```

Also ensure `site_url` in `mkdocs.yml` matches the public domain (`https://sentinel-docs.example.com/`) — fixed in this repo.

---

## Diagnostic Commands

```bash
# Sentinel health check
curl -s http://localhost:5050/api/health | python3 -m json.tool

# Sentinel detailed status (requires auth)
curl -s -b cookies.txt http://localhost:5050/api/status | python3 -m json.tool

# Check all Sentinel-related services
systemctl list-units 'sentinel*'

# View Sentinel logs (last hour)
journalctl -u sentinel --since "1 hour ago" --no-pager

# Check SQLite WAL mode
sqlite3 /var/log/sentinel/logs/sentinel_state.db "PRAGMA journal_mode;"

# Count active incidents
sqlite3 /var/log/sentinel/logs/sentinel_state.db \
  "SELECT channel_type, severity, count(*) FROM problems \
   WHERE status='active' GROUP BY channel_type, severity;"

# Prometheus metrics
curl -H "Authorization: Bearer <scrape_token>" http://localhost:5050/metrics
```
