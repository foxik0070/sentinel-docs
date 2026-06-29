# Sentinel Agent

**Typ:** Push-only monitorovací daemon  
**Kompatibilita:** Debian · Ubuntu · RHEL 8/9/10 · Rocky Linux · AlmaLinux  
**Python:** 3.13+

Sentinel Agent je **odlehčený stavový daemon** běžící jako root na každém monitorovaném nodu. Tiše sbírá 21 kategorií telemetrie — zdraví hardware, stav služeb, bezpečnostní události, stav sítě, kapacitu disků — a posílá na centrální Sentinel server pouze **změny stavu** (delta) přes outbound HTTPS.

Klíčovým principem návrhu je **nulová inbound expozice**: agent nikdy neotevírá naslouchající port, nikdy nepřijímá připojení. Útočník, který zkompromituje Sentinel server, nemůže přes agenta pivotovat zpět na monitorované nody. Provoz teče pouze jedním směrem.

---

## Architektura

```
  ┌──────────────────────────────────────────────────┐
  │                 Monitorovaný node                │
  │                                                  │
  │  Kernel Space & Subsystems                       │
  │  /sys/class/thermal · /proc/mdstat · /dev/kmsg   │
  │  netfilter · statvfs · smartctl · dmesg          │
  │            │                                     │
  │            ▼ Sběr raw metrik                     │
  │  Sentinel Agent Daemon (root)                    │
  │  · 21 sběrových rutin, sekvenčně                │
  │  · Stavový delta filtr (in-memory cache)         │
  │  · Retry buffer pro offline stavy               │
  │  · Boot delay (90 s stabilizace)                │
  │            │                                     │
  └────────────│─────────────────────────────────────┘
               │ HTTPS POST — pouze outbound
               ▼
     Sentinel Core /api/v1/agent/ingest
```

---

## 21 sběrových rutin

| Rutina | Co monitoruje | Spouštěč |
|---|---|---|
| `agent_services_monitor` | systemctl is-active (N-confirm guard) | změna stavu služby |
| `agent_mounts_monitor` | ismount() check dle konfigurace | zmizení mountu |
| `agent_network_port_security` | `ss -tlpn` baseline + detekce nového portu (pouze TCP — UDP byl příliš hlučný) | port přidán/odebrán |
| `agent_security_root_monitor` | `who` SSH sessions — IP parsována regexem, ignoreIP seznam | nová root session |
| `agent_security_vulnerability_scan` | `apt-get -s` / `dnf` (security + CVE) | nové CVE dostupné |
| `agent_security_firewall_fail2ban` | fail2ban-client status (>50 banů threshold) | počet banů roste |
| `agent_temperature_monitor` | `/sys/class/thermal`, `/sys/class/hwmon` | překročení thresholdu |
| `agent_storage_capacity_monitor` | statvfs() disk % + inode usage | překročení thresholdu |
| `agent_raid_monitor` | `/proc/mdstat` (degraded/recovery) | změna stavu pole |
| `agent_ssd_wearout_monitor` | `smartctl -A` atribut opotřebení ≤10% | opotřebení pod limitem |
| `agent_kernel_oom_monitor` | `dmesg` OOM counter | OOM událost |
| `agent_process_zombie_monitor` | `ps -eo state` (počet Z) | zombie procesy |
| `agent_system_time_sync` | `timedatectl` NTP sync check | sync selže |
| `agent_network_dns_monitor` | `socket.gethostbyname()` test | DNS překlad selže |
| `agent_systemd_global_monitor` | `systemctl list-units --state=failed` | failed unit nalezen |
| `agent_kernel_io_monitor` | `ps -eo state` (D stav ≥2) | I/O stall detekován |
| `agent_netfilter_monitor` | `/proc/sys/net/netfilter` conntrack % | conntrack se plní |
| `agent_disk_health_monitor` | `smartctl -H` na fyzických discích (PASSED/FAILED) | zdraví disku selže |
| `agent_kernel_taint_monitor` | `/proc/sys/kernel/tainted` (non-zero) | kernel tainted |
| `agent_ssl_cert_monitor` | `openssl x509 -enddate` (warn ≤14d, crit ≤3d) | certifikát brzy expiruje |
| `agent_memory_monitor` | `/proc/meminfo` MemAvailable, swap nezávisle | nízká paměť |

---

## Stavový delta filtr

Agent přenáší data pouze pokud se něco **změní**. Žádný spam, žádné duplikáty.

```
[ Sběr metrik ]
       │
       ▼
[ Porovnání s cache last_reported_states ]
       │
       ├── Stejné jako dříve → zahazuj, žádný síťový provoz
       │
       └── Změna → POST JSON na /api/v1/agent/ingest
                    aktualizace cache
```

**Re-afirmace aktivních issues:** jediná výjimka z delta pravidla — všechna aktuálně **aktivní** issues se přeposílají každý cyklus. Bez toho by restart Sentinel serveru agentní issues „zapomněl" a auto-resolvnul, přestože problém trvá.

`boot_delay_sec` (výchozí 90 s) potlačí všechny alerty při startu nodu, aby nedocházelo k false positives ze služeb, které ještě nenaběhly.

---

## Wire protokol

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

Server sleduje verzi agenta přes pole `version` (git SHA), zobrazeno v detail modalu agenta.

---

## Instalace

```bash
chmod +x sentinel_agent_init.py

# Česky (výchozí)
sudo ./sentinel_agent_init.py

# Anglicky
sudo ./sentinel_agent_init.py -l en

# Nápověda
./sentinel_agent_init.py --help
```

Průvodce:

1. Detekuje OS, nainstaluje systémové balíčky
2. Vytvoří `.venv/` s `requests` a `pyyaml`
3. Vygeneruje `/etc/sentinel/agent_config.yaml`
4. Nainstaluje a zapne systemd službu

### Manuální spuštění

```bash
# Jeden cyklus, verbose výstup
venv/bin/python sentinel_agent.py --verbose --once

# Normální daemon
venv/bin/python sentinel_agent.py
```

---

## Konfigurace

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

## Bezpečnostní model

```
  Monitorovaný node
  ────────────────────────────────────────
  Agent → pouze HTTPS outbound

  ✗ Žádné otevřené porty
  ✗ Žádný inbound provoz
  ✗ Žádné SSH zpět na Sentinel server

  ✓ API klíč je jednosměrný
  ✓ Firewall může blokovat vše
    kromě outbound HTTPS
```
