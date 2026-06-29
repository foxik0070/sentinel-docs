# Sentinel Alert — Dashboard pro síťovou bezpečnost

**Verze:** 2026.06.001 (Debian / Ubuntu / Raspbian · RHEL 8 / 9 / 10)  
**Python:** 3.13+

Sentinel Alert je **standalone real-time dashboard pro síťovou bezpečnost** — zcela nezávislý na Sentinel core. Běží na vlastním portu (5056), vlastní SQLite databázi a vlastní systemd službě.

Byl navržen pro jeden účel: okamžitá vizuální odpověď na otázku *„co mě teď útočí a jak je na tom moje síť?"* 3D glóbus zobrazuje živé útoky z celého světa. SSH-based scanner audituje každý Linux host na CVE a misconfigurace. D3.js force graf mapuje topologii LAN. Uptime monitor sleduje všechny vaše služby.

Nasaďte ho na libovolný stroj — nástěnný Raspberry Pi, NOC pracovní stanici nebo vedle Sentinel core. Funguje stejně dobře v home labu (`home` mode) i v kancelářském prostředí (`work` mode).

---

## Přehled funkcí

| Záložka / funkce | Popis | Vyžaduje přihlášení | Další konfigurace |
|---|---|:---:|---|
| **Threat Map** | 3D glóbus — živé útoky, heatmapa zemí, fail2ban záznamy, Top Countries | ne | — |
| **Security Center** | SSH-based matice hostitelů (OS, CVE, firewall, fail2ban) | ano | `security_center.enabled = true` |
| **Proxy Monitor** | Čtení logů sniproxy — propustnost, top domény, živý přenos | ano | `sniproxy.server` nastaven |
| **Network Map** | Interaktivní D3.js topologie — LAN zařízení, přepínače, routery, ISP gateway | ano | `scanner.enabled = true` |
| **Services** | Uptime monitor — HTTP/HTTPS, TCP, Ping, DNS, Heartbeat; SSL cert, grafy | ano (jen home) | — |
| **PiHole** | Statistiky Pi-hole v6 DNS — více instancí, top domény, top blokované, timeline dotazů | ano | nastavené `pihole.hosts` |
| **MikroTik** | RouterOS firewall přes SSH — address-listy, filter/NAT pravidla, block/unblock IP, toggle pravidel | ano | nastavený `mikrotik.host` |
| **Database Viewer** | Procházení, hledání a mazání záznamů z tabulek attacks / bans / devices | ano | — |
| **Settings** | Živý editor konfigurace, stav systému, export konfigurace | ano | — |
| **Report** | Markdown report za posledních 24 h — útoky, bany, zařízení, logy | ano | — |

Další funkce:

- **Globe solo mode** — `/?solo=globe` otevře glóbus přes celou obrazovku v nové záložce
- **Blocked IPs** — vizualizace statického souboru blokovaných IP jako útočných oblouků na glóbusu
- **Sentinel Bridge** — přeposílání událostí na centrální Sentinel server
- **Honeypot** — falešné SSH (port 2222) a HTTP (port 8080) služby zachytávající útoky
- **ISP enrichment** — background úloha doplňuje ISP informace ke stávajícím záznamům přes ip-api.com (plus offline lookup `dbip-asn.mmdb`)
- **MikroTik blokace** — blokace jedním klikem přidá útočníka do address-listu `blocked_ips` na routeru (drop pravidlo na routeru udělá zbytek); volitelný `auto_block` pro honeypot útočníky
- **PiHole multi-instance** — primární + sekundární Pi-hole v6 monitorované přes REST API (session SID auth)

---

## Architektura

```text
  Prohlížeč
     │
     │ HTTP  WebSocket (/ws/live)
     ▼
  app.py (Flask · port 5056)
     │
     ├── collector.py  — SSH polling fail2ban z monitorovaných hostitelů
     ├── honeypot.py   — falešné SSH + HTTP listenery, zachytávání útoků
     ├── scanner.py    — ARP-scan pro průzkum LAN zařízení
     ├── fsc.py        — Security Center SSH scanner (OS, CVE, firewall)
     ├── geoip.py      — MaxMind GeoLite2 + ip-api.com fallback
     ├── bridge.py     — přeposílání událostí na Sentinel server
     └── blocklist.py  — vizualizace statického blocklist souboru
     │
     ├── data/alerts.db (SQLite — attacks, bans, devices, service_checks)
     └── /etc/sentinel/sentinel-alert.conf (INI konfigurace)
```

---

## Požadavky

- Python 3.13+
- `openssh-client`, `nmap` (pro Security Center a collector)
- `GeoLite2-City.mmdb` (bezplatný MaxMind účet — umístit do `data/`)
- `GeoLite2-ASN.mmdb` (volitelné — přesnější ISP lookup; umístit do `data/`)

---

## Instalace

```bash
# 1. Klonování repozitáře
git clone https://github.com/youruser/sentinel-alert.git
cd sentinel-alert

# 2. Plná instalace (systémové balíčky + venv + konfigurace + systemd)
sudo ./setup.sh

# Instalace jen závislostí (konfigurace později):
sudo ./setup.sh --deps

# Překonfigurování existující instalace:
sudo ./setup.sh --reconf

# Odinstalace (odstraní systemd službu, zachová konfiguraci):
sudo ./setup.sh --uninstall
```

Instalační skript provede:

1. Detekci distribuce (Debian / Ubuntu / RHEL / Fedora) a instalaci systémových balíčků
2. Vytvoření `.venv/` a instalaci Python závislostí
3. Interaktivní průvodce konfigurací
4. Zápis do `/etc/sentinel/sentinel-alert.conf`
5. Inicializaci SQLite databáze (`data/alerts.db`)
6. Generování ed25519 SSH klíče pro fail2ban collector
7. Instalaci a aktivaci systemd service

### Manuální / vývojové spuštění

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 db_init.py
SENTINEL_CONF=/etc/sentinel/sentinel-alert.conf .venv/bin/python app.py
```

---

## Autentizace

Dashboard má dvě úrovně přístupu:

| Bez přihlášení | Po přihlášení |
|---|---|
| Threat Map (glóbus, Top Countries, historie útoků) | Všechny záložky |
| — | Settings, Report, Database Viewer |
| — | Panel Systémové logy |
| — | Panel Lokální síť |

Výchozí přihlašovací údaje: **admin / admin** — změňte před zpřístupněním na síti.

Sessions používají HMAC-SHA256 podepsané cookies (platnost 7 dní). Klíč `secret` je automaticky generován při prvním spuštění.

---

## Konfigurace

Veškerá nastavení jsou v `/etc/sentinel/sentinel-alert.conf` (INI formát).

```ini
[auth]
username = admin
password = admin
secret   =

[mode]
# "home" (výchozí) nebo "work"
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
host       =            # IP/hostname RouterOS — prázdné modul vypne
ssh_user   = admin
auto_block = false      # automaticky blokovat honeypot útočníky

[pihole]
hosts    =              # Pi-hole v6 hosty oddělené čárkou — prázdné vypne
primary  =
password =
```

Po úpravách restartujte službu:

```bash
sudo systemctl restart sentinel-alert
```

---

## Home režim vs. Work režim

Work režim přizpůsobí dashboard pro firemní nasazení, kde LAN scanning není dostupný.

| Funkce | Home režim | Work režim |
|---|---|---|
| Threat Map | viditelná pro všechny | viditelná pro všechny |
| Panel Systémové logy | vyžaduje přihlášení | vyžaduje přihlášení |
| Panel Lokální síť | vyžaduje přihlášení | **skryto** |
| Panel Uživatelé | skryto | vyžaduje přihlášení |
| Security Center | přihlášení + konfigurace | **skryto** |
| Proxy Monitor | přihlášení + konfigurace | **skryto** |
| Network Map | přihlášení + konfigurace | **skryto** |
| Settings | vyžaduje přihlášení | **skryto** |

Aktivace: `type = work` v sekci `[mode]`. Kombinujte s `ips_file` (vizualizace blokovaných IP) a `who_file` (CSV seznam uživatelů).

---

## GeoIP databáze

Nutné pro vizualizaci útoků na glóbusu.

```bash
# Stáhnout z maxmind.com (bezplatný účet)
# Umístit do data/
data/GeoLite2-City.mmdb   # povinné — stát, souřadnice
data/GeoLite2-ASN.mmdb    # volitelné — ISP / org
```

Bez `GeoLite2-City.mmdb` glóbus nezobrazí útoky. Existující záznamy bez ISP jsou doplněny přes ip-api.com jako background úloha při startu.

---

## Nastavení SSH klíče

Collector a Security Center používají `conf/id_ed25519` (generovaný setup.sh).

```bash
# Distribuování veřejného klíče na monitorované hostitele:
ssh-copy-id -i conf/id_ed25519.pub root@<HOST>

# Test připojení:
ssh -i conf/id_ed25519 root@<HOST> 'fail2ban-client status'
```

---

## Threat Map — Glóbus

| Ovládání | Akce |
|---|---|
| Tažení | Otočení glóbusu |
| Scroll | Zoom |
| Klik na oblouk nebo bod | Zobrazení útočné karty (IP, stát, ISP, port) |
| Klik na polygon státu | Vycentrování glóbusu na daný stát |
| Tlačítko `⟳ ROT` | Přepnutí auto-rotace |
| Tlačítko `⛶` | Panel přes celou obrazovku |
| Tlačítko `⧉` | Otevřít glóbus solo v nové záložce |

Útočné oblouky mění barvu podle stáří (jasné a tlusté pro nové, blednou za 24 h). Každý nový útok spustí 3-vlnný shockwave na místě původu a 2-vlnný shield hit v místě domova.

---

## Security Center

SSH-based scanner pro každého hostitele v `/etc/hosts` (vyjma `ignore_ips`):

- OS / kernel / distribuce / EOL status
- Využití CPU, RAM, disků
- Čekající aktualizace rozdělené podle závažnosti CVE
- Stav fail2ban a firewallu
- Povolení root SSH loginu / uživatelé bez hesla
- Detekce LXC / VM kontejnerů

Jednotlivé hostitele lze zapínat/vypínat z UI.

---

## Network Map

Interaktivní D3.js force-directed topologie. Kliknutím na zařízení lze editovat jeho typ, způsob připojení, příznak ISP Gateway nebo nastavení notifikací. Změny jsou persistovány do `data/topo.json`.

---

## Services (Uptime Monitor)

Dostupné pouze v home režimu.

| Typ | Co kontroluje |
|---|---|
| HTTP / HTTPS | GET nebo POST — status kód, volitelná kontrola textu, SSL cert |
| TCP | TCP připojení na host:port — ověření otevřenosti portu |
| Ping | ICMP ping — základní dostupnost |
| DNS | Překlad domény, volitelně přes specifický DNS server |
| Heartbeat | Reverzní monitoring — váš skript POSTuje na `/api/heartbeat/{id}` |

Změny stavu služby (nahoru↔dolů) jsou přeposílány na konfigurovaný Sentinel Bridge.

---

## API reference

| Metoda | Cesta | Auth | Popis |
|---|---|:---:|---|
| GET | `/api/config` | ne | Feature flags, home geo, stav sentinelu |
| POST | `/api/login` | ne | `{ username, password }` → nastaví session cookie |
| GET | `/api/attacks` | ne | Nedávné honeypot útoky |
| GET | `/api/bans` | ne | Historie fail2ban banů |
| GET | `/api/stats/countries` | ne | Počty hitů podle státu |
| GET | `/api/blocklist` | ne | Blokované IP s geo daty |
| GET | `/api/devices` | ne | LAN zařízení |
| GET | `/api/fsc/data` | ne | Data Security Center scanu |
| POST | `/api/fsc/scan` | ne | Spustit manuální scan |
| GET | `/api/services` | ne | Seznam service monitoru (uptime + sparkline) |
| POST | `/api/services` | ne | Přidat monitorovanou službu |
| DELETE | `/api/services/{id}` | ne | Odebrat službu |
| POST | `/api/heartbeat/{id}` | ne | Přijmout heartbeat ping |
| GET | `/api/mikrotik/data` | ano | Address-listy, filter + NAT pravidla, souhrn |
| POST | `/api/mikrotik/block` | ano | `{ip, comment, timeout}` → přidat do blocked_ips listu |
| POST | `/api/mikrotik/unblock` | ano | Odebrat IP z blocked_ips listu |
| POST | `/api/mikrotik/rule/toggle` | ano | Zapnout/vypnout filter nebo NAT pravidlo dle indexu |
| GET | `/api/pihole/data` | ano | Statistiky per instance, top domény/blokované, overtime |
| GET | `/api/status` | ano | Stav systému — GeoIP, moduly, DB statistiky |
| GET | `/api/config/full` | ano | Celá INI konfigurace jako JSON |
| POST | `/api/config/update` | ano | Aktualizace konfiguračního souboru |
| GET | `/api/db/{table}` | ano | Procházení DB tabulky |
| DELETE | `/api/db/{table}` | ano | Mazání záznamů dle PK |
| WS | `/ws/live` | ne | Živý proud událostí |

---

## Datové soubory

| Cesta | Popis |
|---|---|
| `data/alerts.db` | SQLite — attacks, bans, devices, service_checks |
| `data/topo.json` | Topologie sítě |
| `data/services.json` | Konfigurace service monitoru + poslední výsledky |
| `data/GeoLite2-City.mmdb` | GeoIP databáze měst (povinné) |
| `data/GeoLite2-ASN.mmdb` | GeoIP ASN/ISP databáze (volitelné) |
| `conf/id_ed25519` | SSH privátní klíč pro vzdálený přístup |
| `/etc/sentinel/sentinel-alert.conf` | Hlavní konfigurace |

---

## Logy a diagnostika

```bash
# Živý log stream
journalctl -u sentinel-alert -f

# Posledních 100 řádků
journalctl -u sentinel-alert -n 100 --no-pager

# Stav služby
systemctl status sentinel-alert

# Restart
sudo systemctl restart sentinel-alert
```

Systémové logy jsou dostupné také v panelu **Systémové logy** v dashboardu (vyžaduje přihlášení).
