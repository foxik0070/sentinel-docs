# Sentinel Overhealth

**Typ:** Centrální pull orchestrátor (SSH-based sběr telemetrie)  
**Spouštění:** Cron `*/5 * * * *` nebo systemd timer  
**Workers:** 20 souběžných (konfigurovatelné přes `--workers N`)

Doplňuje push agenty aktivním sběrem telemetrie ze všech spravovaných nodů přes SSH. Na každý node je injektován jediný monolitický bash payload přes stdin jednoho SSH připojení — žádné vícenásobné shellové sessions, žádný reziduální stav.

---

## Architektura

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

- **Single-session SSH multiplexing** — celý bash payload odeslaný přes stdin (`bash -s`), ne opakované otevírání shellu
- **Fault isolation** — zavěšený nebo offline node neblokuje ostatní workery
- **Filtrování hostitelů** — automaticky parsováno z `/etc/hosts`, inverse regex vylučuje NAS/Mikrotik/QNAP/hypervisory

---

## SSH Payload protokol

```
Overhealth Server                              Remote Node
      │
      │ 1. ICMP pre-flight ping
      │─────────────────────────────────────────────►│
      │ 2. Ping reply (node potvrzen jako UP)
      │◄─────────────────────────────────────────────│
      │
      │ 3. SSH connect + bash payload via stdin
      │─────────────────────────────────────────────►│
      │   [ Node spustí vše lokálně ]
      │   [ Generuje stdout se ===TAG=== markery ]
      │
      │ 4. Vrácení celého stdout
      │◄─────────────────────────────────────────────│
```

### Formát výstupu (wire)

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

Parser používá `^===([A-Z]+)===$` pro rozdělení sekcí.

---

## 11 typů logů

| Log soubor | Zdroj | Co sbírá |
|---|---|---|
| `availability.log` | pre-flight ping | ICMP latence, HOST_DOWN / STATUS: UP |
| `capacity.log` | `df -hl` | Disky nad 85% threshold |
| `storage.log` | `zpool status` | Zdraví ZFS poolů |
| `services.log` | `systemctl --failed` | Crashed/failed systemd units |
| `system.log` | `journalctl -p 0..4` | Kernel chyby, CRIT/ALERT/EMERG |
| `temperature.log` | `/sys/class/thermal` sysfs | CPU teplota (raw millidegrees) |
| `ports.log` | `ss -tuln` | Naslouchající TCP/UDP sockety |
| `security.log` | fail2ban-client | Počty aktivních banů v jailech |
| `secure.log` | `/var/log/auth.log` | SSH auth selhání, chybná hesla |
| `audit.log` | `apt-get -s` / `debsecan` | Čekající security updaty, CVE vektory, reboot flagy |
| `homeassistant.log` | HA REST API (port 8123) | Dump stavu všech HA entit |

---

## Atomický zápis souborů

Zabraňuje race conditions, kdy UI nebo detektory čtou částečně zapsaný log.

```
In-Memory Buffer
      │
      ▼ zápis do staging area
/var/log/sentinel/logs/.collect_tmp/system.tmp
      │
      ▼ os.replace() — POSIX atomická výměna inodu
/var/log/sentinel/logs/system.log
      (čtenáři vidí buď starý nebo nový soubor — nikdy částečný)
```

---

## Nasazení

### Cron (každých 5 minut)

```bash
*/5 * * * * /usr/local/bin/sentinel_orchestrator.py \
  --clean --workers 25 \
  >> /var/log/sentinel/orchestrator.log 2>&1
```

`--clean` odstraní ANSI escape kódy z logu.

### Systemd timer (přesnější)

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

### Manuální diagnostické spuštění

```bash
# Plný barevný TUI výstup, 40 workers
sudo /usr/local/bin/sentinel_orchestrator.py --workers 40

# Ověření výstupu
ls -la /var/log/sentinel/logs/
cat /var/log/sentinel/logs/secure.log
```

---

## Filtrování hostitelů

Overhealth automaticky přeskakuje zařízení, která nepotřebují infrastrukturní monitoring:

```python
BLACKLIST_PATTERNS = [
    r'nas', r'mikrotik', r'qnap', r'synology',
    r'switch', r'ap-', r'unifi', r'idrac', r'ilo'
]
```

Hostitelé z `/etc/hosts` odpovídající těmto vzorům jsou tiše přeskočeni.
