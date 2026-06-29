# Sentinel Plugins — Dokumentace detektorů

Repozitář `sentinel-plugins` obsahuje **11 detektorů**, každý čte log streamy produkované [Sentinel Overhealth](./sentinel-overhealth.md) a hlásí incidenty do centrálního Sentinel API.

---

## Přehled detektorů

| Plugin | Vstup | Závažnost | Auto-Heal | AI |
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

## Architektura

```
[ Plugin Manager ]
       │
       ├── Skenuje /plugins/*.py
       ├── Ověřuje dědičnost z BaseDetector
       └── Routuje log řádky dle masky souboru
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
 audit_    avail_    capacity_   univ_sec_
 detector  detector  detector   detector
    │          │          │          │
    ▼          ▼          ▼          ▼
  DB write   Auto-heal  DISK_FULL|  AI enqueue
```

Každý detektor dědí z `BaseDetector` (`base.py`). Plugin Manager dynamicky načte všechny soubory `*.py`, ověří rozhraní a předává log řádky dle odpovídající masky souboru.

---

## Auto-Heal detektory

Tři detektory zavírají incidenty automaticky bez zásahu admina:

### availability_detector

```
"HOST_DOWN" → api.report_problem(key)   → UI: 🔴 CRITICAL
"STATUS: UP" → api.resolve_problem(key) → UI: 🟢 OK (auto-zavřeno)
```

### temperature_detector

```
temp_c >= 85 → CRITICAL → api.report_problem()
temp_c >= 75 → WARNING  → api.report_problem()
temp_c < 75  → OK       → api.resolve_problem()  ← Auto-Heal
```

Hodnoty teplot nad 1000 jsou považovány za millistupně a vyděleny 1000.

### storage_detector

```
"STATUS: HEALTHY" → api.resolve_problem()  ← Auto-Heal
jakýkoliv jiný text → api.report_problem()
```

---

## AI detektor — universal_security

Jediný detektor s přímou AI integrací. Zpracovává `auth.log` a `syslog`.

```python
if "Failed password" or "Invalid user":
    severity = WARNING      # brute-force aktivita

elif "sudo: incorrect password":
    severity = CRITICAL     # pokus o eskalaci privilegií

elif "COMMAND=" and ("install" or "remove"):
    severity = INFO         # modifikace balíčkového systému
```

Při každém spuštění:
1. Zapis do DB s unikátním otiskem (`SEC|server|hash`)
2. Odeslání Teams notifikace
3. `api.enqueue_ai_task()` — asynchronní AI analýza přidána k incidentu

---

## Schéma cache klíčů

Unikátní klíče umožňují mít více souběžných incidentů na jednom serveru a umožňují auto-healing:

| Detektor | Formát klíče | Příklad |
|---|---|---|
| capacity | `DISK_FULL\|server\|mount` | `DISK_FULL\|proxmox01\|/data` |
| services | `SERVICE_FAILED\|server\|svc` | `SERVICE_FAILED\|node01\|nginx.service` |
| availability | `HOST_DOWN\|server` | `HOST_DOWN\|node-03` |
| security | `F2B_ACTIVE\|server` | `F2B_ACTIVE\|web01` |
| temperature | `TEMP_HIGH\|server` | `TEMP_HIGH\|node02` |
| storage | `STORAGE_DEGRADED\|server` | `STORAGE_DEGRADED\|nas01` |
| audit | `CVE_HIGH\|server\|cve-id` | `CVE_HIGH\|proxmox01\|CVE-2026-1234` |

Stejný klíč = aktualizace existujícího incidentu. Různý klíč = nová nezávislá karta incidentu.

---

## Pattern Editor (Sentinel Web UI)

Vlastní detekční vzory lze přidat bez úpravy Python kódu:

1. Otevřít Settings → Pattern Editor
2. Napsat regex vzor proti zdroji logu
3. Nastavit závažnost a kanál
4. Použít regex tester k ověření na vzorových řádcích
5. Uložit — hot-reload pluginu se aplikuje okamžitě (bez restartu)

---

## Testování bez live Sentinelu

Repozitář obsahuje standalone test harness:

```bash
python test_detectors.py
```

Testy pokrývají edge cases parsování (multi-host log bloky, poškozené řádky, přechody auto-heal) bez potřeby běžící instance Sentinelu.
