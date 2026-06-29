# Sentinel Commander — Uživatelská příručka (v2026.06.024)

Určeno pro operátory, administrátory a bezpečnostní techniky pracující se Sentinelem přes webové rozhraní nebo mobilní aplikaci.

---

## Přístup a role (RBAC)

Webové rozhraní běží na portu **5050** a vyžaduje autentizaci. LDAP je podporován (lldap i OpenLDAP).

| Role | Oprávnění |
|---|---|
| **viewer** | Čtení incidentů a telemetrie, AI chat (RAG dotazy) |
| **admin** | Vše výše + Schválit/Zamítnout Autofix, SSH modal, batch SSH, správa agentů |
| **superadmin** | Vše výše + Settings, API klíče, hromadné mazání, audit trail, správa DB |

### Přihlášení

Standardně: formulář jméno + heslo.
LDAP: stejný formulář — přihlašovací údaje se ověřují proti nakonfigurovanému LDAP serveru.

**Dvoufaktorová autentizace (2FA/TOTP):** pokud je pro váš účet zapnutá, druhý krok vyžaduje 6místný kód z Google Authenticatoru / Authy. Aktivace se provádí v **Settings → 2FA** — naskenujte QR kód autentizační aplikací a potvrďte jedním kódem. Admin může 2FA deaktivovat uživateli, který ztratil zařízení.

**Ochrana proti brute-force:** 5 neúspěšných pokusů → IP ban na 5 minut (konfigurovatelné). Platí pro login formulář, Basic auth i auto-registraci agentů.

**Session:** absolutní timeout 12 h; role se každých 5 minut znovu načítá z databáze, takže změna role se projeví bez nového přihlášení.

Přihlašovací stránka odkazuje na veřejnou stránku **/status** (read-only přehled flotily, auto-refresh každých 30 s, bez přihlášení).

---

## Přehled dashboardu

```
┌──────────────────────────────────────────────────────────────────┐
│  SENTINEL COMMANDER v2026.06  [CS/EN] [🌙] [?] (Uživatel) (Alerty)│
├─────────────────────┬────────────────────────────────────────────┤
│  SYSTEM MONITOR     │  AKTIVNÍ INCIDENTY                         │
│  CPU ████── 45%     │  [!] security  brute-force na hpc-gw       │
│  RAM █████─ 75%     │      [🪄] [👁] [🗑] [✓✓] [#tag] [🔔]      │
│  Disk 20%           │  [!] infra  DISK_FULL proxmox01:/data 92%  │
│  AI latence 1.2s    │      acknowledged ● [#storage]             │
│  RAG: Ready         │  ▙ flapping widget ▟  ▙ health trend ▟     │
├─────────────────────┴────────────────────────────────────────────┤
│  AI CHAT   [návrh: "Co se změnilo přes noc?"] [LIVE]             │
│  Sentinel: Detekována chyba paměti na node-01.                   │
│  > Zadejte dotaz, příkaz, nebo přetáhněte log soubor...          │
└──────────────────────────────────────────────────────────────────┘
```

### UI panely

| Panel | Obsah |
|---|---|
| **System Monitor** | CPU/RAM/disk, AI latence, hloubka fronty, stav RAG, počet agentů |
| **Aktivní incidenty** | Karty per kanál: security · infra · agents · root |
| **AI Chat** | RAG dotazy, chat příkazy, chips s navrženými dotazy, LIVE kontext tag, drag&drop upload logu |
| **Health trend** | 7denní line chart health score flotily + počet issues |
| **Flapping widget** | Issues které se opakovaně vrací, seřazené dle frekvence |
| **Topologie** | Force-directed graf agentů (záložka Tools) |
| **Telemetrie** | Interaktivní grafy s min/max/avg, heatmapy, trend charty |

**Grafy:** všechny hlavní grafy (dashboard trend, donut, alert timeline, agent sparklines) jsou interaktivní — hover zobrazí přesné hodnoty, přerušovaná linie značí průměr a min/max/avg badge shrnuje okno.

**i18n:** Přepínání čeština/angličtina tlačítkem `CS/EN` v horní liště. Tmavý/světlý režim ikonou 🌙. Obě preference se ukládají do `localStorage`. Zobrazovanou časovou zónu lze nastavit na serveru (`DISPLAY_TZ`).

**Widgety dashboardu** lze jednotlivě skrýt/zobrazit v nastavení dashboardu; v záhlaví běží živé hodiny.

---

## Karty issues a workflow

Každý detekovaný incident se zobrazí jako karta. Kompletní workflow:

```
active → acknowledged (✓✓) → validating → resolved
```

### Akce karty

| Tlačítko | Akce |
|---|---|
| 🪄 **Autofix** | Vyžádat AI návrh opravy |
| 👁 **Ignorovat** | Potlačit incident (přidá do ignore listu) |
| 🗑 **Smazat** | Tvrdé smazání z DB (objeví se znovu, pokud ho log dál produkuje) |
| ✓✓ **Acknowledge** | Označit jako viděné — karta zežloutne, eskalační timer se resetuje |
| **#tag** | Přidat nebo upravit tagy incidentu |
| 🔔 **Notifikace** | Otevřít nastavení notifikací per detektor/kanál |
| ↕ **Fullscreen** | Otevřít issue přes celou obrazovku (detail + AI analýza + komentáře + podobné incidenty, Esc zavře) |
| **▾ Sbalit** | Sbalit kartu do souhrnu |
| **⋯ Historie** | Otevřít timeline incidentu (komentáře, auto-rem, acknowledge eventy) |

Další funkce karet:

- **Inline komentáře** — komentář píšete přímo na kartě; auto-refresh nikdy nesmaže rozepsaný text.
- **Barevné štítky** — barevné labely pro vizuální triáž.
- **Kopie jako Markdown** — jeden klik zkopíruje Markdown souhrn issue (do ticketů/chatu).
- **Počítadlo výskytů** — opakované detekce zvyšují počítadlo místo vytváření duplikátů.
- **Mobilní swipe** — swipe vpravo = acknowledge, vlevo = delete.
- **Virtual scroll** — dlouhé seznamy se načítají po 50 kartách tlačítkem „Načíst více".

### Hromadné operace a klávesové zkratky

| Zkratka | Akce |
|---|---|
| `Alt+A` | Hromadný acknowledge vybraných issues |
| `Alt+E` | Export vybraných issues do CSV |
| `Alt+F` | Fokus na filtr issues |
| `Esc` | Zavřít nejvrchnější modal |
| `?` | Zobrazit přehled zkratek |

### Tagování issues

Napište `#tag` do tag inputu, nebo definujte auto-tag pravidla v configu:

```yaml
auto_tags:
  - pattern: "DISK_FULL"
    tag: "storage"
  - pattern: "fail2ban"
    tag: "security"
```

Tagy jsou prohledávatelné a zobrazují se v tag cloud panelu.

### Eskalační badge

Pokud issue zůstane nevyřešené déle, než je nakonfigurováno, severity se automaticky zvýší a objeví se timer badge: `⏱ 3h active`. Eskalační pravidla se nastavují per kanál v `config.yaml`. Přechody lifecycle (CREATED / ACKNOWLEDGED / RESOLVED) mohou navíc spouštět **webhooky** a kritické issues lze zrcadlit do **Gitea** jako repository issues.

---

## Autofix — schvalování AI návrhů

1. Klikněte **🪄 Autofix** na kartě incidentu (nebo napište `autofix` do chatu).
2. AI analyzuje kontext logu a vygeneruje bash příkaz.
3. Objeví se modal „Pending Action" s navrženým příkazem, risk score a dry-run náhledem.
4. Klikněte **✅ Schválit** — příkaz se vykoná přes SSH na cílovém nodu.
   Klikněte **❌ Zamítnout** — návrh se zahodí.
5. Při úspěchu: incident přejde do `validating`, poté `resolved`, jakmile detektor potvrdí. Výstup se zobrazí i u tichých příkazů (`exit 0, bez výstupu`) a modal zůstává otevřený, dokud si výsledek nepřečtete.

> Příkazy musí být na allowlistu `allowed_commands` v `config.yaml`. Blokované příkazy jsou automaticky zamítnuty bez ohledu na vstup admina — allowlist se pre-validuje *před* navázáním SSH spojení.

**SSH Jump Host:** Pokud je cílový node za bastionem, Autofix automaticky použije ProxyJump.

---

## SSH modal a Batch SSH (admin+)

Přímý SSH přístup k libovolnému agentovi z Web UI bez Autofix pipeline:

1. Klikněte na agenta v pohledu Agents → otevře se detail agenta.
2. Klikněte tlačítko **SSH** (vyžaduje `admin` nebo `superadmin`).
3. Pište příkazy — výstup streamuje živě do modalu.
4. Všechny příkazy se logují do audit trailu.

**Batch SSH:** modal „Batch SSH" umožní spustit jeden allowlistovaný příkaz na až 50 agentech paralelně (checkbox seznam s online/offline indikátory); výsledky se zobrazí per host s OK/FAIL barvami. Každý host má vlastní 15s timeout, takže jeden zaseknutý node nezablokuje dávku.

**SSH host klíče:** detail agenta zobrazuje zaznamenané `known_hosts` klíče s akcemi **Rescan** a **Delete** — host klíče se pinují (`accept-new`), nedůvěřuje se jim slepě.

---

## Detail agenta

Modal agenta agreguje vše o jednom nodu:

| Sekce | Obsah |
|---|---|
| **Telemetrie** | CPU/RAM/disk sparklines s min/max/avg, markery anomálií |
| **Health score** | Kompozitní skóre 0–100 se známkou A–D |
| **Balíčky** | On-demand inventář balíčků (`dpkg`/`rpm`) s live filtrem |
| **CVE scan** | Čekající bezpečnostní aktualizace přes `apt`/`dnf` po SSH |
| **HW metriky** | Síťová propustnost, GPU (nvidia/rocm), disk SMART, stav UPS |
| **Plánované akce** | Pending/plánované akce pro tento host |
| **Okna údržby** | Per-host snooze okna s předvyplněným hostname |
| **Heartbeat timeout** | Per-agent override (30–86400 s) nebo globální default |
| **Thresholdy** | Per-agent CPU/RAM/disk pravidla s quick-buttons (CPU > 90 %, RAM > 90 %, Disk > 85 %) — vynucováno serverem při každém ingestu |
| **SSH klíče** | Záznamy known_hosts, rescan/delete |
| **Deploy helper** | Generátor instalačního one-lineru |

**Registrace:** token modal zobrazuje token agenta s tlačítkem kopírovat a **QR kódem** (`{hostname, token, ingest_url}`) pro setup přes telefon. Superadmin může hromadně rotovat všechny agent tokeny.

---

## AI chat příkazy

| Příkaz | Role | Akce |
|---|---|---|
| `status` / `stav` | všichni | Kompletní agregovaný přehled incidentů v chatu |
| `sys` | všichni | Live system monitor widget vložený do chatu |
| `pending` | všichni | Seznam Pending Actions (Schválit/Zamítnout z chatu) |
| `show_ignored` | všichni | Seznam potlačených incidentů s tlačítkem Unignore |
| `batch` | admin | Batch AI analýza až 50 aktivních issues |
| `delete_all_issues` | admin+ | Smazat všechny issues a pending actions |
| `delete_key <hash>` | admin+ | Smazat jedno konkrétní issue dle klíče |
| `clear file` | všichni | Uvolnit kontext nahraného souboru, návrat k RAG |
| `?` | všichni | Zobrazit overlay klávesových zkratek |

Chat navíc umí:

- **Navržené dotazy** — kontextové chips pod inputem („Co se změnilo přes noc?", „Shrň security issues"…).
- **LIVE tag** — obohatí váš dotaz o kontext aktuálních aktivních issues před odesláním AI.
- **Markdown rendering** — AI odpovědi renderují tučné písmo, nadpisy, code bloky (highlight.js) a odrážky.
- **Export chatu** — jeden klik uloží konverzaci jako Markdown.

---

## Drag & drop analýza logu

Nahrajte `.log`, `.txt` nebo `.md` soubor do chat oblasti (nebo klikněte na sponku).

- AI kontext se přepne z RAG na obsah nahraného souboru (prvních ~15 000 znaků).
- Ptejte se konkrétně: *„Vypiš všechny DNS chyby a kdy začaly."*
- Příkazem `clear file` se vrátíte do normálního RAG režimu.

---

## Telemetrie, analytika a reporty

Dostupné na dashboardu a v **Tools**:

- **Sparkline grafy** — top-6 nejteplejších hostů, teplota v čase
- **Trend chart** — růst kapacity s TTC predikcí
- **Host Heatmap** — hustota incidentů per host per den
- **Health Score** — kompozitní známka A–D per agent + 7denní health trend flotily
- **Detekce anomálií** — 3σ špičky označené červenou tečkou na timeline
- **Záložka Analytika** — SLA tabulka resolution-time + alert-fatigue graf (false positives per plugin)
- **Předpověď issues** — 7denní výhled objemu issues lineární regresí
- **Záložka Kapacita** — AI kapacitní plánování: karty HOST/PROBLÉM/DOPORUČENÍ/PRIORITA per host + predikce kapacity (čas do zaplnění disku/RAM)
- **Záložka Srovnání** — porovnání dvou časových oken telemetrie (delta + % rozdíl)
- **Alert timeline** — interaktivní graf objemu alertů s min/max/avg
- **Auto-clustering** — tlačítko „Clustery" seskupí související issues (stejný plugin na N hostech / stejný host s N issues v 30min okně); AI pojmenuje pravděpodobnou root cause
- **Postmortem** — vygenerujte AI Markdown postmortem k libovolnému vyřešenému incidentu
- **Týdenní digest** — obsahuje flapping issues a průměrnou dobu řešení

---

## Runbooks

**Tools → Runbooks** drží provozní postupy hned vedle incidentů:

- CRUD seznam runbooků (vytvořit, upravit, smazat)
- Otevření runbooku v modalu během práce na issue

---

## Mapa topologie

Dostupná v **Tools → Topologie**:

- Force-directed graf všech agentů a jejich síťových vztahů
- Barva dle stavu: zelená (OK) → žlutá (warning) → červená (critical) → šedá (offline)
- SNMP CDP/LLDP data sloučená s daty agentů
- Klik na node otevře detail agenta

---

## Nastavení notifikací

Klikněte na libovolnou ikonu 🔔 (karta issue, issues toolbar, Plugin Stats):

- **Kanály** — zapnout/vypnout notifikace per kanál (infra / agent / security / root)
- **Integrace** — toggle každé odchozí integrace (Teams, Slack, Discord, Telegram, Opsgenie, ntfy, Gotify, SMTP, Matrix, PagerDuty, HA, MQTT, Webhook)
- **Per-detektor** — každý plugin v Plugin Stats má vlastní 🔔 toggle
- Přihlašovací údaje integrací se konfigurují inline v modalu **Notifikace & Integrace** (tlačítka Uložit + Test per tab); secret pole se nikdy nezobrazují zpět

Notifikace jsou throttlované per severity (critical/security/root 15 min, high 1 h, medium/low 4 h) a neúspěšná doručení se automaticky opakují s backoffem.

---

## Settings (superadmin)

| Sekce | Co lze konfigurovat |
|---|---|
| **Config editor** | Live editace `config.yaml`, uložení spustí hot-reload; schema validace blokuje neplatné hodnoty |
| **2FA** | Aktivace/deaktivace TOTP, QR provisioning |
| **Hash hesla** | Vygeneruje bcrypt hash připravený k vložení do `config.yaml` |
| **REST API klíče** | Vytvořit/revokovat scoped API klíče (`read:issues` / `write:actions` / `admin:users`) |
| **Pattern Editor** | Vlastní regex detekční patterny s live testerem + AI návrhy patternů z historických issues |
| **Plugin hot-reload** | Reload všech pluginů bez restartu serveru |
| **Suppress pravidla** | Definice false positive patternů pro auto-potlačení (s počítadly zásahů) |
| **Config diff** | Porovnání libovolných dvou config snapshotů (selektory + diff pohled) |
| **Config backup/restore** | Restore nejprve automaticky zazálohuje aktuální config (drží 10) |
| **Správa DB** | Velikost DB, počty záznamů, „Prune nyní", „Agregovat telemetrii" |
| **Audit trail** | Kdo měnil config, spouštěl SSH příkazy, schvaloval akce — s IP a časem |
| **Log level** | Změna log levelu serveru za běhu |
| **Changelog** | Git log posledních změn kódu |

---

## Mobilní aplikace

Viz [dokumentace Sentinel App](../sentinel-app.cs.md). Aplikace zrcadlí veškerou funkčnost dashboardu s:

- Biometrickou autentizací (otisk / obličej)
- Push notifikacemi (bez Google FCM)
- P2P admin chatem (volatilní, bez DB)
- Vizuálním offline režimem (odstíny šedi + červený banner)
