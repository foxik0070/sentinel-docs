# Sentinel Overhealth

**Type:** Central pull orchestrator (SSH-based telemetry collection)  
**Execution:** Cron `*/5 * * * *` or systemd timer  
**Workers:** 20 concurrent (configurable with `--workers N`)

Complements push agents by actively pulling telemetry from every managed node over SSH. A single monolithic bash payload is injected via stdin into one SSH connection per node — no multiple shell sessions, no residual state.

---

## Architecture

```
  ┌────────────────────────────────┐
  │   Sentinel Overhealth Engine   │
  │   (Central Pull Orchestrator)  │
  └────────────┬───────────────────┘
               │
  ┌────────────┼────────────┬──────────────────┐
  │ SSH        │ SSH        │ SSH              │ HTTP
  ▼            ▼            ▼                  ▼
node-01      node-02      node-N          Home Assistant
bash payload bash payload bash payload   REST API
===TAG===    ===TAG===    ===TAG===       JSON states
```

- **Single-session SSH multiplexing** — entire bash payload sent via stdin (`bash -s`), not multiple shell openings
- **Fault isolation** — hung or offline node does not block other workers
- **Host filtering** — auto-parsed from `/etc/hosts`, inverse regex excludes NAS/Mikrotik/QNAP/hypervisor gear

---

## SSH Payload Protocol

```
Overhealth Server                              Remote Node
      │
      │ 1. ICMP pre-flight ping
      │─────────────────────────────────────────────►│
      │ 2. Ping reply (node confirmed UP)
      │◄─────────────────────────────────────────────│
      │
      │ 3. SSH connect + bash payload via stdin
      │─────────────────────────────────────────────►│
      │   [ Node executes all commands locally ]
      │   [ Generates stdout with ===TAG=== markers ]
      │
      │ 4. Full stdout returned
      │◄─────────────────────────────────────────────│
```

### Wire output format

```
===SYSTEM===
May 18 18:14:02 server kernel: Out of memory: Kill process ...
===SERVICES===
nginx.service failed loaded failed The NGINX HTTP Server
===CAPACITY===
/dev/sda1       40G   36G  2.1G  92% /
===TEMPERATURE===
48000
```

The parser uses `^===([A-Z]+)===$` to split sections.

---

## 11 Log Types

| Log file | Source | What it collects |
|---|---|---|
| `availability.log` | pre-flight ping | ICMP latency, HOST_DOWN / STATUS: UP |
| `capacity.log` | `df -hl` | Disks above 85% threshold |
| `storage.log` | `zpool status` | ZFS pool health |
| `services.log` | `systemctl --failed` | Crashed/failed systemd units |
| `system.log` | `journalctl -p 0..4` | Kernel errors, CRIT/ALERT/EMERG |
| `temperature.log` | `/sys/class/thermal` sysfs | CPU temperature (raw millidegrees) |
| `ports.log` | `ss -tuln` | Listening TCP/UDP sockets |
| `security.log` | fail2ban-client | Active jail ban counts |
| `secure.log` | `/var/log/auth.log` | SSH auth failures, password errors |
| `audit.log` | `apt-get -s` / `debsecan` | Pending security upgrades, CVE vectors, reboot flags |
| `homeassistant.log` | HA REST API (port 8123) | Full HA entity state dump |

---

## Atomic File Writes

Prevents race conditions where UI or detectors read a partially written log.

```
In-Memory Buffer
      │
      ▼ write to staging
/var/log/sentinel/logs/.collect_tmp/system.tmp
      │
      ▼ os.replace() — POSIX atomic inode swap
/var/log/sentinel/logs/system.log
      (readers see either old or new — never partial)
```

---

## Deployment

### Cron (every 5 minutes)

```bash
*/5 * * * * /usr/local/bin/sentinel_orchestrator.py \
  --clean --workers 25 \
  >> /var/log/sentinel/orchestrator.log 2>&1
```

`--clean` removes ANSI escape codes from the log.

### Systemd timer (more precise)

```bash
sudo systemctl enable --now sentinel-collector.timer
```

```ini
# sentinel-collector.timer
[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Persistent=true
```

### Manual diagnostic run

```bash
# Full colour TUI output, 40 workers
sudo /usr/local/bin/sentinel_orchestrator.py --workers 40

# Verify output
ls -la /var/log/sentinel/logs/
cat /var/log/sentinel/logs/secure.log
```

---

## Host Filtering

Overhealth auto-excludes devices that don't need infrastructure monitoring:

```python
BLACKLIST_PATTERNS = [
    r'nas', r'mikrotik', r'qnap', r'synology',
    r'switch', r'ap-', r'unifi', r'idrac', r'ilo'
]
```

Hosts matching these patterns in `/etc/hosts` are silently skipped.
