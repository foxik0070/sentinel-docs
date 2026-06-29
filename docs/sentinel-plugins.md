# Sentinel Plugins — Detector Documentation

The `sentinel-plugins` repository ships **11 detectors**, each reading log streams produced by [Sentinel Overhealth](./sentinel-overhealth.md) and reporting incidents to the central Sentinel API.

---

## Detector Overview

| Plugin | Input | Severity | Auto-Heal | AI |
|---|---|---|:---:|:---:|
| **audit_detector** | audit.log | WARNING / CRITICAL | ✗ | ✗ |
| **availability_detector** | availability.log | CRITICAL | **✓** | ✗ |
| **capacity_detector** | capacity.log | WARNING / CRITICAL | ✗ | ✗ |
| **ha_detector** | homeassistant.log (HA JSON) | INFO / CRITICAL | ✗ | ✗ |
| **port_detector** | ports.log (`ss -tuln`) | WARNING / CRITICAL | ✗ | ✗ |
| **security_detector** | security.log (fail2ban) | WARNING | ✗ | ✗ |
| **services_detector** | services.log | CRITICAL | ✗ | ✗ |
| **storage_detector** | storage.log (ZFS) | CRITICAL | **✓** | ✗ |
| **system_detector** | system.log (journalctl) | CRITICAL | ✗ | ✗ |
| **temperature_detector** | temperature.log (sysfs) | WARNING / CRITICAL | **✓** | ✗ |
| **detector_universal_security** | auth.log / syslog | INFO / WARNING / CRITICAL | ✗ | **✓** |

---

## Architecture

```
[ Plugin Manager ]
       │
       ├── Scans /plugins/*.py
       ├── Verifies inheritance from BaseDetector
       └── Routes log lines by file mask
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
 audit_    avail_    capacity_   univ_sec_
 detector  detector  detector   detector
    │          │          │          │
    ▼          ▼          ▼          ▼
  DB write   Auto-heal  DISK_FULL|  AI enqueue
```

Every detector inherits from `BaseDetector` (`base.py`). The Plugin Manager dynamically loads all `*.py` files, validates the interface, and passes log lines by matching file masks.

---

## Auto-Heal Detectors

Three detectors automatically close incidents without admin action:

### availability_detector

```
"HOST_DOWN" → api.report_problem(key)   → UI: 🔴 CRITICAL
"STATUS: UP" → api.resolve_problem(key) → UI: 🟢 OK (auto-closed)
```

### temperature_detector

```
temp_c >= 85 → CRITICAL → api.report_problem()
temp_c >= 75 → WARNING  → api.report_problem()
temp_c < 75  → OK       → api.resolve_problem()  ← Auto-Heal
```

Temperature values above 1000 are assumed to be millidegrees and divided by 1000.

### storage_detector

```
"STATUS: HEALTHY" → api.resolve_problem()  ← Auto-Heal
any other text    → api.report_problem()
```

---

## AI Detector — universal_security

The only detector with direct AI integration. Processes `auth.log` and `syslog`.

```python
if "Failed password" or "Invalid user":
    severity = WARNING      # brute-force activity

elif "sudo: incorrect password":
    severity = CRITICAL     # privilege escalation attempt

elif "COMMAND=" and ("install" or "remove"):
    severity = INFO         # package system modification
```

On each trigger:
1. Write to DB with unique fingerprint (`SEC|server|hash`)
2. Send Teams notification
3. `api.enqueue_ai_task()` — async AI analysis appended to the incident

---

## Cache Key Schema

Unique keys allow multiple simultaneous incidents per server and enable auto-healing:

| Detector | Key format | Example |
|---|---|---|
| capacity | `DISK_FULL\|server\|mount` | `DISK_FULL\|proxmox01\|/data` |
| services | `SERVICE_FAILED\|server\|svc` | `SERVICE_FAILED\|node01\|nginx.service` |
| availability | `HOST_DOWN\|server` | `HOST_DOWN\|node-03` |
| security | `F2B_ACTIVE\|server` | `F2B_ACTIVE\|web01` |
| temperature | `TEMP_HIGH\|server` | `TEMP_HIGH\|node02` |
| storage | `STORAGE_DEGRADED\|server` | `STORAGE_DEGRADED\|nas01` |
| audit | `CVE_HIGH\|server\|cve-id` | `CVE_HIGH\|proxmox01\|CVE-2026-1234` |

Same key = update existing incident. Different key = new independent incident card.

---

## Pattern Editor (Sentinel Web UI)

Custom detection patterns can be added without modifying Python code:

1. Open Settings → Pattern Editor
2. Write a regex pattern against the log source
3. Set severity and channel
4. Use the regex tester to validate against sample log lines
5. Save — plugin hot-reload applies immediately (no restart)

---

## Testing Without Live Sentinel

The repository includes a standalone test harness:

```bash
python test_detectors.py
```

Tests cover parsing edge cases (multi-host log blocks, malformed lines, auto-heal transitions) without requiring a running Sentinel instance.
