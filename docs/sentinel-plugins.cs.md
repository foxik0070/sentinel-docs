# Sentinel Plugins — Dokumentace detektorů

Detektory čtou log streamy produkované [Sentinel Overhealth](./sentinel-overhealth.md) a hlásí incidenty do centrálního Sentinel API.

Od **v2026.11.010** už nežijí všechny uvnitř Sentinelu. Sentinel si nechává jen základ — `base.py`, odkud pochází `api.BaseDetector`, a dva detektory, bez kterých nemá smysl běžet: `system_detector` (jádro) a `services_detector` (systemd). Zbylých deset je v repozitáři `sentinel-plugins` a nasazuje se vlastním balíčkem. Úprava detektoru tak už neznamená vydat celý Sentinel a vydání Sentinelu naopak nepřepíše detektory, které si někdo doplnil.

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
| **detector_windows** | windows-*.log | WARNING / CRITICAL | ✗ | ✗ |

`system_detector` a `services_detector` jsou součástí Sentinelu, zbytek přichází z balíčku `sentinel-plugins`.

---

## Kde detektory leží

`plugin_dir` v `config.yaml` smí být **seznam adresářů** (od v2026.11.010):

```yaml
plugin_dir:
  - /opt/Sentinel/sentinel/plugins   # základ dodávaný se Sentinelem
  - /opt/sentinel-plugins            # balíček sentinel-plugins
  - /opt/sentinel-plugins-it4i       # sady pro dané pracoviště, pokud jsou
detectors:
  - plugin: port_detector
    match_pattern: ports.log
```

Hledá se v uvedeném pořadí, takže při shodě jmen vyhraje adresář uvedený dřív. **Jediný řetězec se chová jako dřív**, takže konfigurace, které seznam nepotřebují, se měnit nemusí.

### Instalace z balíčku

```bash
apt install sentinel-plugins     # Debian / Ubuntu
dnf install sentinel-plugins     # RHEL a odvozené
```

!!! warning "Balíček nainstalovat dřív než povýšit Sentinel"
    Detektor, který `config.yaml` vyžaduje a jeho soubor není ani v jednom adresáři, založí `SENTINEL|detectors_missing` (kanál `infra`, severity `critical`). Povýšení na v2026.11.010 bez nainstalovaného balíčku tedy vyrobí critical issue za každý přesunutý detektor.

---

## Detektory v odděleném repozitáři

Detektory specifické pro dané pracoviště — HPC clustery, ECC počítadla, chlazení — patří do vlastního repozitáře. Do v2026.11.010 se musely kopírovat **do adresáře pluginů Sentinelu**, a právě odtud pocházejí obě následující pasti:

- **Žádný deploy balíčku `Sentinel` je tam nedostane.** Potřebují vlastní deploy krok; bez něj můžou soubory prostě chybět, zatímco `config.yaml` je pořád vyjmenovává.
- **Nikdy `rsync --delete` do adresáře pluginů.** Oddělený repozitář neobsahuje pluginy dodávané se Sentinelem, takže `--delete` je smaže.

Obě zmizí, jakmile má sada vlastní adresář v `plugin_dir`: nikdo nezapisuje do cizího adresáře, takže ho nemá jak přepsat ani smazat. Kopírování zůstává jedinou možností pro instance starší než v2026.11.010.

Třetí úskalí není v nástrojích, ale v načasování: běžící proces si naimportované moduly drží v paměti, takže detektory se smazanými zdrojovými soubory **fungují dál až do dalšího restartu**. Mezi smazáním a restartem, který to odhalí, můžou uběhnout dny.

Od v2026.09.013 detektor, který config vyžaduje a nenačte se, založí `SENTINEL|detectors_missing` (kanál `infra`, severity `critical`). Před tou verzí byla tahle situace tichá — config detektory chtěl, nenačetl se žádný, a protože logy neměl kdo číst, stale cleanup do hodiny uklidil jejich issues a zůstala instance, která hlásí OK a přitom nemonitoruje nic.

Pokud v adresáři pluginů leží `__pycache__` se záznamy, ke kterým chybí `.py`, je to ten podpis. Časy `.pyc` navíc říkají, **která verze** naposled běžela — přečtěte si je dřív, než obnovíte z kopie, která může být starší.

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

Každý detektor dědí z `BaseDetector`, který importuje jako `api.BaseDetector`; samotná třída leží v `base.py` uvnitř Sentinelu a `sentinel/api.py` ji re-exportuje. Proto `base.py` zůstává u Sentinelu, i když se detektory odstěhovaly — detektoru v libovolném adresáři stačí `from sentinel import api`.

Plugin Manager načte soubor pojmenovaný v `config.yaml` klíčem `plugin` z prvního adresáře v `plugin_dir`, který ho má, ověří rozhraní a předává log řádky dle odpovídající masky souboru.

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
