# Sentinel Console — TUI klient

**Typ:** Terminal User Interface dashboard (TUI v3.0)  
**Framework:** Textual + httpx  
**Auth:** Cookie session + CSRF token, s detekcí fail2ban lockoutu

Real-time terminálový dashboard ve stylu HTOP s **plnou paritou funkcí webového UI** — funguje přes SSH, v `tmux`/`screen` i na systémových konzolích.

---

## Layout

```
┌─ SENTINEL TUI v2026.06.013 ─ [WARNING] ─ INFRA ─ Sort:TIME ─ Issues:65/98 ─ LUKAS ──────┐
│  INFRA ████████████  63   AGENT ░░░░░░░░░░░░   2                                          │
│  ROOT  ░░░░░░░░░░░░   0   SEC   ██░░░░░░░░░░   3    TOTAL: 98                             │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  [ALL]   INFRA   AGENT   ROOT   SEC              Sort: TIME                               │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ RYCHLÉ AKCE    │ ★    ČAS              SEV    CH     HOST           ZPRÁVA                │
│ (l) Log Viewer │ ×3   2026-06-13 23:44  CRIT  INFR   web-01         nginx: connect fail   │
│ (g) Agenti     │ ACK  2026-06-13 23:41  HIGH  AGNT   hpc-node-04    CPU spike >95%        │
│ (n) AI Návrhy  │      2026-06-13 23:38  WARN  ROOT   gateway-01     sudo session opened   │
│ (t) Trendy     │      2026-06-13 23:35  WARN  SEC    fw-01          port scan detected    │
│ (x) AI Souhrn  │                                                                           │
│ (z) AI Korel.  │                                                                           │
│ (i/d/f/a/s)... │                                                                           │
├────────────────┴─────────────────────────────────────────────────────────────────────────┤
│ » ahoj                                                                                     │
│ ◆ Vše je v pořádku. Žádné kritické události za posledních 24h.                             │
│ AI chat > _                                                                               │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ?:Help Enter:Detail Space:Sel i:Ign d:Del f:Fix a:Ack s:Snooze /:Filter q:Quit           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

Header zobrazuje HTOP-style sloupcový ukazatel per kanál (INFRA / AGENT / ROOT / SEC) s živými počty, aktivní kanál/řazení a počítadlo `Issues:filtrované/celkem`. Levý panel **Rychlé akce** (přepínání `p`) spouští prohlížeče a AI nástroje; spodní AI chat panel se přepíná klávesou `c`.

---

## Zobrazovací režimy

### Split Mode (výchozí)

DataTable (2fr) + Chat Container (1fr) — vidíte incidenty i AI log současně.

### Full Chat Mode (`c`)

DataTable zmizí → Chat Container se rozbalí na 100% → focus přesměrován na vstupní pole.

Vhodné pro rychlé AI dotazy:

```
> Proč je nginx down na hpc-node-04?
[AI] Analýza: disk plný na /var/log/nginx (98%)
     Doporučení: logrotate -f /etc/logrotate.d/nginx
```

---

## Klávesové zkratky

### Navigace a zobrazení
| Klávesa | Akce |
|---|---|
| `↑` / `↓` | Navigace v tabulce |
| `Tab` / `Shift+Tab` | Přepnout kanál |
| `1`–`5` | Přímý výběr kanálu (ALL / INFRA / AGENT / ROOT / SEC) |
| `o` | Přepnout řazení (ČAS → SEV → HOST → CH) |
| `/` / `F2` | Live filtr |
| `Esc` | Zrušit filtr / bulk výběr |
| `c` | Skrýt/zobrazit chat panel |
| `p` | Skrýt/zobrazit panel rychlých akcí |
| `r` / `F5` | Okamžitý refresh |
| `q` / `F10` | Ukončit |

### Issue akce
| Klávesa | Akce |
|---|---|
| `Enter` | Detail issue + komentáře |
| `i` | Ignorovat |
| `d` | Smazat |
| `f` | AI Autofix |
| `a` | Acknowledge / Un-acknowledge |
| `s` | Snooze (1h / 4h / 24h / 72h) |

### Bulk operace
| Klávesa | Akce |
|---|---|
| `Space` | Přidat/odebrat z výběru |
| `Ctrl+A` | Vybrat vše (aktuální kanál + filtr) |
| `I` | Bulk Ignore |
| `D` | Bulk Delete |
| `A` | Bulk Acknowledge |

### AI funkce
| Klávesa | Akce |
|---|---|
| chat vstup | Přímý dotaz na Sentinel AI |
| `f` | AI Autofix — analýza a návrh opravy pro vybraný issue |
| `x` | AI Souhrn — přehled všech aktivních issues aktuálního kanálu |
| `z` | AI Korelace — hledá vzory a korelace mezi issues |
| `t` | AI Trend report — predikce a trendy za 7 dní |

### Modaly
| Klávesa | Modal |
|---|---|
| `Enter` | Issue Detail (detaily, komentáře, akce) |
| `s` | Snooze |
| `l` | Log Viewer (prohlížeč log souborů) |
| `g` | Správa agentů (status všech agentů) |
| `n` | AI Návrhy akcí (Execute / Reject čekajících AI příkazů) |
| `?` / `F1` | Nápověda |

---

## Autofix workflow v TUI

```
Stisknutí 'f' na vybraném incidentu
  │
  ▼
[AI] Generuji autofix pro: DISK_FULL|proxmox01|/
[AI] Navrhovaný příkaz:
     find /var/log -name "*.log" -mtime +30 -delete
[AI] Risk: LOW
[?] Schválit? (y/n):
  │
  └── y → approve request → Sentinel SSH-exec na proxmox01
```

---

## Instalace

```bash
git clone git@github.com:foxik0070/sentinel-console.git
cd sentinel-console

# Interaktivní průvodce (generuje config + systemd service)
sudo ./sentinel_client_init.py

# Manuální spuštění
venv/bin/python sentinel_client.py \
  --url http://sentinel.local:5050 \
  --user admin
```

### Konfigurace

```ini
# /etc/sentinel/sentinel_client.conf (mode 0600)
[sentinel]
url      = http://sentinel.local:5050
username = admin
interval = 5
```

### Bezpečnost

- Oprávnění konfiguračního souboru: `0600`
- Při odpovědi 401/403: polling se zmrazí (`auth_locked=True`), zabraňuje fail2ban lockoutu z opakovaných neúspěšných requestů
- Cookie manager persistuje session mezi terminal reconnects

---

## Kdy použít Console vs. Web UI

| Scénář | Doporučení |
|---|---|
| SSH session na serveru | Console — není potřeba prohlížeč |
| tmux / screen | Console — stabilní v multiplexeru |
| Skriptování / automatizace | Console — pipeable AI dotazy |
| Plný dashboard s grafy | Web UI (port 5050) |
| Správa z mobilu | Sentinel App (Android) |
