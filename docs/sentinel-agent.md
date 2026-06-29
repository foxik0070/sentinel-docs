# Sentinel Agent

**Type:** Push-only monitoring daemon  
**Compatibility:** Debian · Ubuntu · RHEL 8/9/10 · Rocky Linux · AlmaLinux  
**Python:** 3.13+

Sentinel Agent is a **lightweight stateful daemon** that runs as root on each monitored node. It silently collects 21 categories of telemetry — hardware health, services, security events, network state, disk capacity — and pushes only **state changes** (delta) to the central Sentinel server over outbound HTTPS.

The key design principle is **zero inbound exposure**: the agent never opens a listening port, never accepts connections. An attacker who compromises the Sentinel server cannot pivot back to monitored nodes through the agent. Traffic flows in one direction only.

---

## Architecture

```
  ┌──────────────────────────────────────────────────┐
  │                  Monitored Node                  │
  │                                                  │
  │  Kernel Space & Subsystems                       │
  │  /sys/class/thermal · /proc/mdstat · /dev/kmsg   │
  │  netfilter · statvfs · smartctl · dmesg          │
  │            │                                     │
  │            ▼ Raw Metric Ingestion                │
  │  Sentinel Agent Daemon (root)                    │
  │  · 21 collection routines, sequential            │
  │  · Stateful delta filter (in-memory cache)       │
  │  · Retry buffer for offline states               │
  │  · Boot delay (90 s stabilisation)               │
  │            │                                     │
  └────────────│─────────────────────────────────────┘
               │ HTTPS POST — outbound only
               ▼
     Sentinel Core /api/v1/agent/ingest
```

---

## 21 Collection Routines

| Routine | What it monitors | Trigger |
|---|---|---|
| `agent_services_monitor` | systemctl is-active (N-confirm guard) | service state change |
| `agent_mounts_monitor` | ismount() check per configured path | mount disappears |
| `agent_network_port_security` | `ss -tlpn` baseline + new port detection (TCP only — UDP was too noisy) | port added/removed |
| `agent_security_root_monitor` | `who` SSH sessions — IP parsed by regex, ignoreIP list | new root session |
| `agent_security_vulnerability_scan` | `apt-get -s` / `dnf` (security + CVE) | new CVE available |
| `agent_security_firewall_fail2ban` | fail2ban-client status (>50 ban threshold) | ban count rises |
| `agent_temperature_monitor` | `/sys/class/thermal`, `/sys/class/hwmon` | threshold crossed |
| `agent_storage_capacity_monitor` | statvfs() disk % + inode usage | threshold crossed |
| `agent_raid_monitor` | `/proc/mdstat` (degraded/recovery) | array state changes |
| `agent_ssd_wearout_monitor` | `smartctl -A` wearout attribute ≤10% | wearout below limit |
| `agent_kernel_oom_monitor` | `dmesg` OOM counter | OOM event appears |
| `agent_process_zombie_monitor` | `ps -eo state` (Z count) | zombies appear |
| `agent_system_time_sync` | `timedatectl` NTP sync check | sync fails |
| `agent_network_dns_monitor` | `socket.gethostbyname()` test | DNS resolution fails |
| `agent_systemd_global_monitor` | `systemctl list-units --state=failed` | failed unit found |
| `agent_kernel_io_monitor` | `ps -eo state` (D state ≥2) | I/O stall detected |
| `agent_netfilter_monitor` | `/proc/sys/net/netfilter` conntrack % | conntrack fills up |
| `agent_disk_health_monitor` | `smartctl -H` on physical disks (PASSED/FAILED) | disk health fails |
| `agent_kernel_taint_monitor` | `/proc/sys/kernel/tainted` (non-zero) | kernel tainted |
| `agent_ssl_cert_monitor` | `openssl x509 -enddate` (warn ≤14d, crit ≤3d) | cert expires soon |
| `agent_memory_monitor` | `/proc/meminfo` MemAvailable, swap independent | memory low |

---

## Stateful Delta Filter

The agent only transmits data when something **changes**. No spam, no duplicates.

```
[ Collect metrics ]
       │
       ▼
[ Compare with last_reported_states cache ]
       │
       ├── Same as before → discard, no network traffic
       │
       └── Changed → POST JSON to /api/v1/agent/ingest
                      update cache
```

**Active-issue re-affirmation:** one exception to the delta rule — all currently **active** issues are re-sent every cycle. Without this, a Sentinel server restart would "forget" agent issues and auto-resolve them even though the underlying problem persists.

`boot_delay_sec` (default 90 s) suppresses all alerts during node startup to avoid false positives from services that haven't started yet.

---

## Wire Protocol

```http
POST /api/v1/agent/ingest
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "hostname": "hpc-node-04",
  "version": "<git-sha>",
  "channel": "agents",
  "ip_addresses": ["10.0.0.4", "172.16.0.1"],
  "timestamp": "2026-06-02T18:42:00+02:00",
  "data": {
    "cpu": 94.2,
    "ram_used": 87.1,
    "message": "CPU critical: 94.2%",
    "severity": "CRITICAL"
  }
}
```

The server tracks the agent version via the `version` field (git SHA), displayed in the agent detail modal.

---

## Installation

```bash
chmod +x sentinel_agent_init.py

# English prompts
sudo ./sentinel_agent_init.py -l en

# Czech prompts (default)
sudo ./sentinel_agent_init.py

# Help
./sentinel_agent_init.py --help
```

The wizard:

1. Detects OS, installs system packages
2. Creates `.venv/` with `requests` and `pyyaml`
3. Generates `/etc/sentinel/agent_config.yaml`
4. Installs and enables a systemd service

### Manual run

```bash
# Single cycle, verbose output
venv/bin/python sentinel_agent.py --verbose --once

# Normal daemon
venv/bin/python sentinel_agent.py
```

---

## Configuration

```yaml
# /etc/sentinel/agent_config.yaml

sentinel:
  url: "https://sentinel.example.com"
  api_key: "<your-agent-token>"
  interval: 30

agent:
  hostname: "hpc-node-04"
  boot_delay_sec: 90

modules:
  services:
    enabled: true
    watch:
      - name: nginx
        confirm_count: 2
      - name: postgresql
  disk:
    enabled: true
    warn_pct: 85
    crit_pct: 95
  ssl_certs:
    enabled: true
    paths:
      - /etc/ssl/certs/server.crt
  temperature:
    enabled: true
    warn_c: 75
    crit_c: 85
```

---

## Security Model

```
  Monitored Node
  ────────────────────────────────────────
  Agent → HTTPS outbound only

  ✗ No open ports
  ✗ No inbound traffic
  ✗ No SSH back to Sentinel server

  ✓ API key is unidirectional
  ✓ Firewall can block everything
    except outbound HTTPS
```
