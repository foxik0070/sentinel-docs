# Sentinel Ecosystem — Deployment Guide (v2026.06.024)

Complete guide for deploying the entire Sentinel monitoring ecosystem in production.

---

## Architecture Overview

```
  ┌─────────────────────────────────────────────────┐
  │              Central Server                     │
  │  Sentinel Core :5050  +  Overhealth (cron)      │
  │  sentinel-plugins (co-located)                  │
  └──────────────────────────┬──────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │ SSH pull         │ Push (HTTPS)      │ optional
          ▼                  ▼                   ▼
   Monitored nodes    Agent nodes         sentinel-alert :5056
   (Overhealth)       (sentinel-agent)    sentinel-hw :5055
```

---

## Recommended Deployment Order

| Step | Component | Where |
|---|---|---|
| 1 | **Sentinel** (core server) | Central monitoring server |
| 2 | **sentinel-plugins** | Same server as Sentinel |
| 3 | **sentinel-overhealth** | Same server as Sentinel |
| 4 | **sentinel-agent** | Every monitored node |
| 5 | **sentinel-alert** | Any machine (optional, standalone) |
| 6 | **sentinel-hw** | Raspberry Pi Zero 2W (optional) |
| 7 | **sentinel-app** | Android device (optional) |
| 8 | **sentinel-console** | Admin workstations (optional) |
| 9 | **sentinel-docs** | Internal docs server (optional) |

---

## 1. Sentinel — Central Server

### Requirements

- Python 3.13+, Debian 11+ / Ubuntu 22.04+ / RHEL 8/9/10 / Rocky Linux
- Ollama running with `nomic-embed-text` model (for RAG embeddings)
- 4 GB RAM minimum, 8 GB recommended
- 10 GB disk for DB + ChromaDB

### Installation

```bash
git clone git@github.com:foxik0070/Sentinel.git /opt/Sentinel
sudo bash /opt/Sentinel/install.sh
sudo python3 /opt/Sentinel/sentinel_init.py   # interactive wizard
sudo systemctl enable --now sentinel
```

### Key configuration (`/etc/sentinel/config.yaml`)

```yaml
web:
  host: 0.0.0.0
  port: 5050
  # bcrypt hash preferred over plaintext password — generate via
  # Settings → "Hash password" or POST /api/config/hash_password
  password_hash: "$2b$12$..."

security:
  login_max_attempts: 5
  login_ban_time: 300
  session_max_hours: 12

ollama:
  url: "http://localhost:11434"
  model: "llama3.2"
  workers: 3

teams_channels:
  webhooks:
    security: "https://outlook.office.com/webhook/..."

prometheus:
  enabled: true
  scrape_token: "{SECRET:PROM_TOKEN}"   # env-var substitution supported

telemetry_alerts:
  cpu_critical: 95
  disk_critical: 95
  temp_critical: 85

fim:
  enabled: true
  paths: [/etc/passwd, /etc/shadow, /etc/ssh/sshd_config]
```

The setup wizard (`sentinel_init.py`) refuses default passwords, creates `/var/lib/sentinel`, and generates the systemd unit with `WatchdogSec=900` plus a WAL-checkpoint `ExecStartPre`. Config files are validated with `jsonschema` — invalid critical keys are rejected at load.

### Verify

```bash
systemctl status sentinel
curl -s http://localhost:5050/api/health
# → {"status": "ok"}
curl -s http://localhost:5050/healthz
# → {"status": "ok", "db": "ok"}   (HTTP 503 on DB failure — for K8s/UptimeKuma)
```

---

## 2. sentinel-plugins

Plugins ship with Sentinel but can also be deployed from the separate repository for custom detectors.

```bash
# Deploy from separate repo
git clone git@github.com:foxik0070/sentinel-plugins.git \
  /opt/Sentinel/sentinel/plugins/external

# Register in config.yaml
detectors:
  plugins_dir: /opt/Sentinel/sentinel/plugins/external
```

Plugins hot-reload — no restart needed after adding a new detector.

---

## 3. sentinel-overhealth

```bash
git clone git@github.com:foxik0070/sentinel-overhealth.git \
  /opt/sentinel-overhealth
cd /opt/sentinel-overhealth

# SSH key for remote access
ssh-keygen -t ed25519 -f conf/id_ed25519 -N ""
# Copy public key to all monitored nodes:
ssh-copy-id -i conf/id_ed25519.pub root@<node>
```

### Cron deployment

```bash
# /etc/cron.d/sentinel-overhealth
*/5 * * * * root /opt/sentinel-overhealth/sentinel_orchestrator.py \
  --clean --workers 25 \
  >> /var/log/sentinel/orchestrator.log 2>&1
```

### Systemd timer deployment

```bash
sudo cp sentinel-collector.service sentinel-collector.timer \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sentinel-collector.timer
```

### Verify

```bash
/opt/sentinel-overhealth/sentinel_orchestrator.py --workers 5
ls -la /var/log/sentinel/logs/
# should show: availability.log capacity.log services.log ...
```

---

## 4. sentinel-agent (on each monitored node)

```bash
# On the monitored node
git clone git@github.com:foxik0070/sentinel-agent.git /opt/sentinel-agent
cd /opt/sentinel-agent

# Interactive install (generates config + systemd service)
sudo ./sentinel_agent_init.py -l en

# Verify
systemctl status sentinel-agent
journalctl -u sentinel-agent -f
```

### Agent registration

Agents authenticate via a Bearer token. Generate tokens in Sentinel Web UI:  
**Settings → Agents → Register new agent → copy token**

Set in `/etc/sentinel/agent_config.yaml`:

```yaml
sentinel:
  url: "https://sentinel.example.com"
  api_key: "<token_from_ui>"
  interval: 30
```

---

## 5. sentinel-alert (optional, standalone)

```bash
git clone git@github.com:foxik0070/sentinel-alert.git /opt/sentinel-alert
cd /opt/sentinel-alert
sudo ./setup.sh
```

Required: `GeoLite2-City.mmdb` in `data/` (free MaxMind account).

Verify: `http://<host>:5056`

---

## 6. sentinel-hw (optional, Raspberry Pi)

```bash
# On the Raspberry Pi
git clone git@github.com:foxik0070/sentinel-hw.git /home/pi/sentinel-hw
cd /home/pi/sentinel-hw
chmod +x install.sh
./install.sh
```

Configure `config.yaml` with Sentinel URL and API key.  
Register device in Sentinel Web UI: **Sentinel Satellites → HW Devices → Register**

---

## Firewall Rules

| Service | Port | Protocol | Direction |
|---|---|---|---|
| Sentinel Web UI | 5050 | TCP | inbound to central server |
| sentinel-alert | 5056 | TCP | inbound to alert server |
| sentinel-hw Web UI | 5055 | TCP | inbound to RPi |
| Agent ingest | 5050 | TCP | outbound from all nodes |
| Overhealth SSH | 22 | TCP | outbound from central server |
| Ollama (local) | 11434 | TCP | loopback only |
| hailo-ollama | 8000 | TCP | loopback only |

---

## Nginx Reverse Proxy (recommended for production)

```nginx
server {
    listen 443 ssl;
    server_name sentinel.example.com;

    ssl_certificate     /etc/ssl/certs/sentinel.crt;
    ssl_certificate_key /etc/ssl/private/sentinel.key;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
        proxy_next_upstream off;
    }

    # Serve static files directly with long cache — protects the app
    # server from connection storms and speeds up asset delivery
    location /static/ {
        alias /opt/Sentinel/sentinel/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Connection limit per client IP
    limit_conn addr 10;
}
```

> **Note:** Socket.IO is configured to start with HTTP long-polling before upgrading to WebSocket — it works correctly behind all proxies including Cloudflare.

> **Trusted proxies:** set `TRUSTED_PROXIES` in config.yaml so `X-Forwarded-For` is honoured only from your proxy — otherwise clients could spoof their IP and bypass IP bans.

---

## Production Checklist

- [ ] Set `web.password_hash` (bcrypt) — Sentinel logs a CRITICAL warning + UI banner on default passwords
- [ ] Enable **2FA/TOTP** for all admin accounts (Settings → 2FA)
- [ ] Set `teams_channels.webhooks` (or Discord/Telegram/Opsgenie/…) for alert notifications
- [ ] Set `prometheus.scrape_token` if Prometheus is used — prefer `{SECRET:ENV_VAR}` syntax
- [ ] Configure `ldap` section if using LDAP auth
- [ ] Deploy SSL certificate (Nginx or `sentinel_init.py`)
- [ ] Set `TRUSTED_PROXIES` when running behind a reverse proxy
- [ ] Set up log rotation for `/var/log/sentinel/`
- [ ] Add monitored nodes to `/etc/hosts` on Overhealth server
- [ ] Distribute Overhealth SSH public key to all nodes
- [ ] Download `GeoLite2-City.mmdb` for sentinel-alert
- [ ] Register all agents in Sentinel Web UI (QR code or copy-token)
- [ ] Configure `allowed_commands` allowlist for Autofix
- [ ] Set `telemetry_alerts` thresholds (+ per-agent thresholds where needed)
- [ ] Test Autofix with a low-risk command before enabling `auto_execute`
- [ ] Schedule backups — `/api/admin/backup/download` or S3/MinIO upload
- [ ] Enable `fim` (File Integrity Monitoring) for critical system files
- [ ] Run `/api/admin/security_check` — aim for grade A
- [ ] Point your uptime monitor (UptimeKuma/K8s) at `/healthz`

---

## Updating

```bash
# Sentinel core
cd /opt/Sentinel
git pull
make build          # builds .min.js artefacts (not stored in git)
sudo systemctl restart sentinel
# or hot-reload config+patterns+plugins without restart:
sudo systemctl kill -s HUP sentinel

# Agents (manual)
cd /opt/sentinel-agent
git pull
sudo systemctl restart sentinel-agent

# Overhealth + plugins
git -C /opt/sentinel-overhealth pull
git -C /opt/Sentinel/sentinel/plugins pull
# Plugins hot-reload via Web UI: Settings → Plugin hot-reload
```

---

## Rocky Linux / RHEL — Notes

- Python 3.13+ may need to be installed separately: `dnf install python3.13`
- Run Sentinel with explicit interpreter: `python3.13 -m sentinel -e`
- SELinux: may need `setsebool -P httpd_can_network_connect 1` if using Nginx
- firewalld: `firewall-cmd --add-port=5050/tcp --permanent && firewall-cmd --reload`
