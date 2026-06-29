# Sentinel App — Android klient

**Verze:** 2026.06.022  
**Platforma:** Android 8.0+ (API 26+)  
**Framework:** Flutter 3.22+ / Dart

Nativní Android aplikace pro správu infrastruktury. Poskytuje real-time monitoring, AI Autofix a P2P komunikaci mezi adminy z mobilního telefonu.

---

## Architektura

```
  ┌──────────────────────────────────────────────────┐
  │              Android zařízení                    │
  │                                                  │
  │  Flutter UI Layer (Material 3)                   │
  │  · Reaktivní dashboard · Biometric Vault         │
  │  · Incident Matrix  · AI Chat konzole            │
  │            │                                     │
  │            │ Provider State                      │
  │  ┌─────────▼──────────────────────────────────┐  │
  │  │  Android Foreground Service (Dart Isolate)  │  │
  │  │  WakeLock · WiFi Lock · Socket.IO heartbeat │  │
  │  └─────────────────────────────────────────────┘  │
  └──────────────────────────────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
   REST API        WebSocket
  (HTTP JSON)    (Socket.IO)
  GET/DELETE     live stream
  incidenty      P2P chat
```

---

## Dual-Channel komunikace

Každý HTTP request a WebSocket handshake obsahuje:

- `X-API-Key` — unikátní kryptografický token admina
- `X-Device-ID` — UUID derivované z hardware (zabraňuje echo-loop na více zařízeních)
- `X-Client-User` — ověřená identita uživatele (např. `FoxiK`)

---

## Foreground Service — 24/7

Android by normálně background procesy zabíjel. Sentinel App to obchází pomocí persistentního Android Foreground Service.

```
Start aplikace / biometrické odemčení
  └──► Spawn Dart Isolate
         ├── WakeLock ──── CPU & modem zůstávají vzhůru
         ├── WiFi Lock ─── Wi-Fi modem nezamkne
         └── Socket.IO heartbeat (každých 60 s)
                ├── Přepnutí sítě (Wi-Fi → LTE) → auto-reconnect
                └── Příchozí kritický packet → flutter_local_notifications
                    (nativní push, bez Google FCM)
```

---

## Incident Matrix

4 domény zobrazené jako barevné badges:

| Doména | Popis | Barva |
|---|---|---|
| 🗄️ **LOG ISSUES** | Chyby z journalctl a hraničních systémových logů | Červená/Oranžová |
| 📡 **AGENTS STATUS** | Výpadky agentů nebo telemetrie | Oranžová/Žlutá |
| 🔑 **ROOT SESSIONS** | Aktivní nezmapované root terminály | Červená |
| 🛡️ **SECURITY LOGS** | Fail2ban, port scany, CVE aktualizace | Červená |

### Akce na incidentu

| Akce | Popis |
|---|---|
| 🪄 **AI Autofix** | Odešle incident LLM, zobrazí remediační skript s Execute/Decline |
| 👁 **Ignore** | Skryje incident na serveru i v aplikaci |
| 🗑 **Delete** | Tvrdé smazání z databáze |
| 🔗 **Share** | Zkopíruje hostname, timestamp, původ logu a text chyby do schránky |

---

## Biometrická autentizace

```
Start aplikace
  │
  ▼
Biometrická výzva (otisk / obličej)
  │
  ├── ÚSPĚCH → Odemknutí UI + start foreground service
  │
  └── NEÚSPĚCH / swinutí z task switcheru
        → Okamžité smazání session klíče z RAM
          → Další otevření vyžaduje nové biometrické ověření
```

---

## Vizuální Offline režim

Pokud `provider.isOnline` klesne na `false`:

- Celý widget strom dashboardu dostane greyscale color matrix filtr
- Zobrazí se červený overlay banner: `SPOJENÍ ZTRACENO - OFFLINE`
- Polling dat se zastaví až do obnovení připojení

Od verze **v2026.06.022** se offline stav aktivuje až po **dvou po sobě jdoucích selháních** (30s timeouty požadavků), s jedním hlídaným `_refreshAll()` — bez auto-odhlášení a bez falešného blikání OFFLINE při krátkých výpadcích.

---

## Stabilita připojení (v2026.06.022)

Verze klienta je synchronizována se serverem Sentinel (2026.06.022). Připojení a autentizace byly zpevněny:

- **Auto-provisioning API klíče** — po LLDAP přihlášení si aplikace vyžádá API klíč a přepne se na rychlou cestu `X-API-Key`, bez LDAP bindu při každém požadavku
- **Self-healing zastaralého klíče** — přesměrování `302 → /login` je detekováno jako selhání autentizace (žádný falešný úspěch) a klíč je znovu vyžádán
- **Znovupoužití provideru/socketu** — změna nastavení znovupoužije stávající provider a Socket.IO spojení místo jejich rekonstrukce
- **Lazy načítání záložek** — záložky se načítají na vyžádání, odstraněna startup lavina požadavků
- **Kompletní audit API** — všech 138 endpointů ověřeno proti běžícímu serveru; opraveny dashboard `top_plugins`/`recent_issues`, historie metrik přes `/api/predictions`, statistiky pluginů a opraveny POST payloady (šablony komentářů, patterny)

---

## P2P Admin Chat

Volatile komunikace mezi adminy s **nulovou persistencí v databázi**.

- Zprávy jsou routovány přes Socket.IO room `sentinel_admins` — server je zero-state relay
- Device badge rozlišuje mobilního vs. web UI klienta
- `X-Device-ID` zabraňuje self-messagingu při použití telefonu i prohlížeče zároveň

---

## Technologický stack

| Vrstva | Technologie |
|---|---|
| Framework / Jazyk | Flutter 3.22+ / Dart |
| Správa stavu | Provider + ChangeNotifierProvider |
| Persistence | `shared_preferences` → Android Jetpack Security Crypto |
| Biometrie | `local_auth` (Fingerprint / Face Unlock) |
| Notifikace | `flutter_local_notifications` (bez FCM) |
| Background | `flutter_background_service` (Dart Isolate) |
| REST | `http` package (timeout 10 s) |
| WebSocket | `socket_io_client` (polling → WebSocket upgrade) |
| Build | Nativní ARM binary (bez WebView) |

---

## Build & Deploy

```bash
flutter pub get
flutter pub run flutter_launcher_icons
flutter build apk --release --no-tree-shake-icons
```

Výstup: `build/app/outputs/flutter-apk/app-release.apk`

### Povinná oprávnění AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
```
