# Sentinel Alert — Network Security Dashboard

**Version:** 2026.06.001 (Debian / Ubuntu / Raspbian · RHEL 8 / 9 / 10)  
**Python:** 3.13+

Sentinel Alert is a **standalone real-time network security dashboard** — completely independent of the Sentinel core. It runs on its own port (5056), its own SQLite database, and its own systemd service.

It was designed for one purpose: give you an instant, visual answer to *"what is attacking me right now and how is my network doing?"* A 3D globe shows live attacks from around the world. An SSH-based scanner audits every Linux host for CVEs and misconfigurations. A D3.js force graph maps your LAN topology. An uptime monitor tracks all your services.

Deploy it on any machine — a wall-mounted Raspberry Pi, a NOC workstation, or alongside Sentinel core. It works equally well in a home lab (`home` mode) and an office environment (`work` mode).

---

## Feature Overview

| Tab / Feature | Description | Auth required | Extra config |
|---|---|:---:|---|
| **Threat Map** | 3D globe — live attack arcs, country heatmap, fail2ban bans, top countries, attack history | no | — |
| **Security Center** | SSH-based host matrix (OS, CVEs, firewall, fail2ban status) | yes | `security_center.enabled = true` |
| **Proxy Monitor** | Sniproxy log reader — throughput, top domains, live feed | yes | `sniproxy.server` set |
| **Network Map** | Interactive D3.js topology — LAN devices, switches, routers, ISP gateway | yes | `scanner.enabled = true` |
| **Services** | Uptime monitor — HTTP/HTTPS, TCP, Ping, DNS, Heartbeat; SSL cert check, sparkline graphs | yes (home only) | — |
| **PiHole** | Pi-hole v6 DNS statistics — multiple instances, top domains, top blocked, query timeline | yes | `pihole.hosts` set |
| **MikroTik** | RouterOS firewall over SSH — address-lists, filter/NAT rules, block/unblock IP, rule toggle | yes | `mikrotik.host` set |
| **Database Viewer** | Browse, search and delete records from attacks / bans / devices tables | yes | — |
| **Settings** | Live config editor, system health status, config export | yes | — |
| **Report** | Markdown report of last 24 h — attacks, bans, devices, logs | yes | — |

Additional capabilities:

- **Globe solo mode** — `/?solo=globe` opens a fullscreen globe-only view in a new tab
- **Blocked IPs** — visualise a static blocklist file as attack arcs on the globe
- **Sentinel Bridge** — forward events to a central Sentinel server
- **Honeypot** — fake SSH (port 2222) and HTTP (port 8080) services that capture attacks
- **ISP enrichment** — background task enriches existing records via ip-api.com (plus offline `dbip-asn.mmdb` lookup)
- **MikroTik blocking** — one-click block adds the attacker to the router's `blocked_ips` address-list (a drop rule on the router does the rest); optional `auto_block` for honeypot attackers
- **PiHole multi-instance** — primary + secondary Pi-hole v6 monitored via REST API (session SID auth)

---

## Architecture

```text
  Browser
     │
     │ HTTP  WebSocket (/ws/live)
     ▼
  app.py (Flask · port 5056)
     │
     ├── collector.py  — SSH polling of fail2ban from monitored hosts (every N min)
     ├── honeypot.py   — fake SSH + HTTP listeners, log captured attacks
     ├── scanner.py    — ARP-scan for LAN device discovery
     ├── fsc.py        — Security Center SSH scanner (OS, CVEs, firewall)
     ├── geoip.py      — MaxMind GeoLite2 + ip-api.com fallback
     ├── bridge.py     — forward events to central Sentinel server
     └── blocklist.py  — static IP blocklist visualisation
     │
     ├── data/alerts.db (SQLite — attacks, bans, devices, service_checks)
     └── /etc/sentinel/sentinel-alert.conf (INI config)
```

---

## Requirements

- Python 3.13+
- `openssh-client`, `nmap` (Security Center and collector)
- `GeoLite2-City.mmdb` (free MaxMind account — place in `data/`)
- `GeoLite2-ASN.mmdb` (optional — better ISP lookup; place in `data/`)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/youruser/sentinel-alert.git
cd sentinel-alert

# 2. Full install (system packages + venv + interactive config + systemd)
sudo ./setup.sh

# Install only dependencies (configure later):
sudo ./setup.sh --deps

# Reconfigure existing installation:
sudo ./setup.sh --reconf

# Uninstall (removes systemd service, keeps config):
sudo ./setup.sh --uninstall
```

The setup script:

1. Detects the distro (Debian / Ubuntu / RHEL / Fedora) and installs system packages
2. Creates `.venv/` and installs Python dependencies
3. Runs an interactive configuration wizard
4. Writes `/etc/sentinel/sentinel-alert.conf`
5. Initialises the SQLite database (`data/alerts.db`)
6. Generates an ed25519 SSH key for the fail2ban collector
7. Installs and enables a systemd service unit

### Manual / development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 db_init.py
SENTINEL_CONF=/etc/sentinel/sentinel-alert.conf .venv/bin/python app.py
```

---

## Authentication

The dashboard is split into two access levels:

| Without login | With login |
|---|---|
| Threat Map (globe, top countries, attack history) | All tabs |
| — | Settings, Report, Database Viewer |
| — | System Logs panel |
| — | Local Network panel |

Default credentials: **admin / admin** — change in the config before exposing to any network.

Sessions use HMAC-SHA256 signed cookies (7-day TTL). The `secret` key is auto-generated on first start if not set.

---

## Configuration

All settings live in `/etc/sentinel/sentinel-alert.conf` (INI format).

```ini
[auth]
username = admin
password = CHANGE_ME
secret   =

[mode]
# "home" (default) or "work"
type     = home
ips_file =
who_file =

[server]
host     = 0.0.0.0
port     = 5056

[home]
lat      = 50.0835
lon      = 14.4341

[sentinel]
url      = https://sentinel.example.com
token    = <64-char-token>
hostname = my-node

[honeypot]
ssh_port  = 2222
http_port = 8080

[collector]
ssh_user      = root
hosts_file    = /etc/hosts
monitor_hosts =

[sniproxy]
server    =
ssh_user  = root
log_files = /var/log/sniproxy/https_access.log,/var/log/sniproxy/http_access.log

[scanner]
enabled = false

[security_center]
enabled    = true
ha_url     =
ha_token   =
ignore_ips = 192.168.2.1

[threat]
blocks_ips_file =

[mikrotik]
host       =            # RouterOS IP/hostname — empty disables the module
ssh_user   = admin
auto_block = false      # auto-block honeypot attackers

[pihole]
hosts    =              # comma-separated Pi-hole v6 hosts — empty disables
primary  =
password =
```

After editing, restart the service:

```bash
sudo systemctl restart sentinel-alert
```

---

## Home mode vs. Work mode

Work mode adapts the dashboard for office deployments where LAN scanning is unavailable or unneeded.

| Feature | Home mode | Work mode |
|---|---|---|
| Threat Map | visible to all | visible to all |
| System Logs panel | auth required | auth required |
| Local Network panel | auth required | **hidden** |
| Users panel | hidden | auth required |
| Security Center | auth + config | **hidden** |
| Proxy Monitor | auth + config | **hidden** |
| Network Map | auth + config | **hidden** |
| Settings | auth required | **hidden** |

Enable with `type = work` in `[mode]`. Pair with `ips_file` (blocked IPs visualised on globe) and `who_file` (CSV user list shown in Users panel).

---

## GeoIP databases

Required for attack visualisation on the globe.

```bash
# Download from maxmind.com (free account required)
# Place both files in data/
data/GeoLite2-City.mmdb   # required — country, coordinates
data/GeoLite2-ASN.mmdb    # optional — ISP / org name
```

Without `GeoLite2-City.mmdb` the globe will not display attacks. Existing records with unknown ISP are enriched via ip-api.com as a background task on startup.

---

## SSH key setup

The collector and Security Center use `conf/id_ed25519` (generated by setup.sh).

```bash
# Distribute public key to all monitored hosts:
ssh-copy-id -i conf/id_ed25519.pub root@<HOST>

# Test connection:
ssh -i conf/id_ed25519 root@<HOST> 'fail2ban-client status'
```

---

## Threat Map — Globe

| Control | Action |
|---|---|
| Drag | Rotate globe |
| Scroll | Zoom |
| Click arc or point | Show attack card (IP, country, ISP, port/protocol) |
| Click country polygon | Centre globe on that country |
| `⟳ ROT` button | Toggle auto-rotation |
| `⛶` button | Panel fullscreen |
| `⧉` button | Open globe solo in new tab |

Attack arcs use age-based colouring (bright and thick when fresh, fading over 24 h). Each new attack triggers a 3-wave shockwave ring at the origin and a 2-wave shield-hit ring at home.

---

## Security Center

SSH-based scanner for each host in `/etc/hosts` (excluding `ignore_ips`):

- OS / kernel / distro / EOL status
- CPU, RAM, disk usage
- Pending updates split by CVE severity
- fail2ban status and firewall status
- Root SSH login allowed / passwordless users
- LXC / VM container detection

Hosts can be enabled / disabled individually from the UI.

---

## Network Map

Interactive D3.js force-directed topology. Click any device to edit its type, connection type, ISP Gateway flag, or notification settings. Changes are persisted to `data/topo.json`.

---

## Services (Uptime Monitor)

Available in home mode only.

| Type | What it checks |
|---|---|
| HTTP / HTTPS | GET or POST — status code, optional text match, response time, SSL cert validity |
| TCP | TCP connect to host:port — confirms port is open |
| Ping | ICMP ping — basic IP reachability |
| DNS | Domain resolution, optionally against a specific DNS server |
| Heartbeat | Reverse monitoring — your script POSTs to `/api/heartbeat/{id}` |

Service state changes (up→down / down→up) are forwarded to the configured Sentinel Bridge.

---

## API Reference

| Method | Path | Auth | Description |
|---|---|:---:|---|
| GET | `/api/config` | no | Feature flags, home geo, sentinel status |
| POST | `/api/login` | no | `{ username, password }` → sets session cookie |
| GET | `/api/attacks` | no | Recent honeypot attacks |
| GET | `/api/bans` | no | fail2ban ban history |
| GET | `/api/stats/countries` | no | Country hit counts |
| GET | `/api/blocklist` | no | Blocked IPs with geo data |
| GET | `/api/devices` | no | LAN devices |
| GET | `/api/fsc/data` | no | Security Center scan data |
| POST | `/api/fsc/scan` | no | Trigger manual scan |
| GET | `/api/services` | no | Service monitor list (uptime + sparkline) |
| POST | `/api/services` | no | Add monitored service |
| DELETE | `/api/services/{id}` | no | Remove service |
| POST | `/api/heartbeat/{id}` | no | Receive heartbeat ping |
| GET | `/api/mikrotik/data` | yes | Address-lists, filter + NAT rules, summary |
| POST | `/api/mikrotik/block` | yes | `{ip, comment, timeout}` → add to blocked_ips list |
| POST | `/api/mikrotik/unblock` | yes | Remove IP from blocked_ips list |
| POST | `/api/mikrotik/rule/toggle` | yes | Enable/disable a filter or NAT rule by index |
| GET | `/api/pihole/data` | yes | Per-instance stats, top domains/blocked, overtime |
| GET | `/api/status` | yes | System health — GeoIP, modules, DB stats |
| GET | `/api/config/full` | yes | Full INI config as JSON |
| POST | `/api/config/update` | yes | Update config file |
| GET | `/api/db/{table}` | yes | Browse DB table |
| DELETE | `/api/db/{table}` | yes | Delete records by PK list |
| WS | `/ws/live` | no | Live event stream |

---

## Data files

| Path | Description |
|---|---|
| `data/alerts.db` | SQLite — attacks, bans, devices, service_checks |
| `data/topo.json` | Network topology |
| `data/services.json` | Service monitor config + last results |
| `data/GeoLite2-City.mmdb` | GeoIP city database (required) |
| `data/GeoLite2-ASN.mmdb` | GeoIP ASN/ISP database (optional) |
| `conf/id_ed25519` | SSH private key for remote access |
| `/etc/sentinel/sentinel-alert.conf` | Main configuration |

---

## Logs & diagnostics

```bash
# Live log stream
journalctl -u sentinel-alert -f

# Last 100 lines
journalctl -u sentinel-alert -n 100 --no-pager

# Service status
systemctl status sentinel-alert

# Restart
sudo systemctl restart sentinel-alert
```

System logs are also visible in the dashboard **System Logs** panel (requires login).
