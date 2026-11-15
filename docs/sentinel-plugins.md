# Sentinel Plugins — Detector Documentation

Detectors read log streams produced by [Sentinel Overhealth](./sentinel-overhealth.md) and report incidents to the central Sentinel API.

Since **v2026.11.010** they no longer all live inside Sentinel. Sentinel keeps only the base — `base.py`, which is where `api.BaseDetector` comes from, plus the two detectors it makes no sense to run without: `system_detector` (kernel) and `services_detector` (systemd). The remaining ten live in the `sentinel-plugins` repository and are deployed by their own package, so a change to a detector no longer means releasing all of Sentinel, and a release of Sentinel no longer overwrites detectors somebody added.

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
| **detector_windows** | windows-*.log | WARNING / CRITICAL | ✗ | ✗ |

`system_detector` and `services_detector` ship with Sentinel; the rest come from the `sentinel-plugins` package.

---

## Where Detectors Live

`plugin_dir` in `config.yaml` may be a **list of directories** (v2026.11.010 and later):

```yaml
plugin_dir:
  - /opt/Sentinel/sentinel/plugins   # the base that ships with Sentinel
  - /opt/sentinel-plugins            # the sentinel-plugins package
  - /opt/sentinel-plugins-it4i       # site-specific sets, if any
detectors:
  - plugin: port_detector
    match_pattern: ports.log
```

Directories are searched in the order given, so on a name clash the one listed first wins. **A plain string still behaves as before**, so configurations that do not need a list do not have to change.

### Installing from the package

```bash
apt install sentinel-plugins     # Debian / Ubuntu
dnf install sentinel-plugins     # RHEL and derivatives
```

!!! warning "Install the package before upgrading Sentinel"
    A detector that `config.yaml` requires but whose file is in none of the directories raises `SENTINEL|detectors_missing` (channel `infra`, severity `critical`). Upgrading to v2026.11.010 without the package installed therefore produces a critical issue for every moved detector.

---

## Detectors in a Separate Repository

Site-specific detectors — HPC clusters, ECC counters, cooling — belong in their own repository. Until v2026.11.010 they had to be copied **into Sentinel's plugin directory**, which is where both of the following traps came from:

- **No deploy of the `Sentinel` package will place them.** They need their own deploy step; without it the files can simply be absent while `config.yaml` still lists them.
- **Never `rsync --delete` into the plugin directory.** The separate repository does not contain the plugins that ship with Sentinel, so `--delete` removes them.

Both disappear once the set has its own directory in `plugin_dir`: nothing writes into somebody else's directory, so nothing can overwrite or delete it. Copying remains the only option for instances older than v2026.11.010.

A third hazard is timing rather than tooling: a running process keeps imported modules in memory, so detectors whose source files are deleted **keep working until the next restart**. The gap between the deletion and the restart that exposes it can be days.

Since v2026.09.013 a detector listed in the config that fails to load raises `SENTINEL|detectors_missing` (channel `infra`, severity `critical`). Before that release the situation was silent — the config asked for detectors, none loaded, and with nothing reading the logs the stale cleanup resolved their issues within the hour, leaving an instance that reported OK while monitoring nothing.

If a plugin directory holds `__pycache__` entries whose `.py` counterparts are gone, that is the signature. The `.pyc` timestamps also tell you **which version** was last running — read them before restoring from a copy that may be older.

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

Every detector inherits from `BaseDetector`, which detectors import as `api.BaseDetector`; the class itself lives in `base.py` inside Sentinel and is re-exported by `sentinel/api.py`. That is why `base.py` stays with Sentinel even though the detectors moved out — a detector in any directory only needs `from sentinel import api`.

The Plugin Manager loads the file named by `plugin` in `config.yaml` from the first directory in `plugin_dir` that has it, validates the interface, and passes log lines by matching file masks.

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
