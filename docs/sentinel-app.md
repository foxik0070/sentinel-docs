# Sentinel App — Android Client

**Version:** 2026.06.022  
**Platform:** Android 8.0+ (API 26+)  
**Framework:** Flutter 3.22+ / Dart

Native Android application for infrastructure management. Provides full real-time monitoring, AI Autofix, and P2P admin communication from a mobile phone.

---

## Architecture

```
  ┌──────────────────────────────────────────────────┐
  │              Android Device                      │
  │                                                  │
  │  Flutter UI Layer (Material 3)                   │
  │  · Reactive dashboard · Biometric Vault          │
  │  · Incident Matrix  · AI Chat Console            │
  │            │                                     │
  │            │ Provider State                      │
  │  ┌─────────▼──────────────────────────────────┐  │
  │  │   Android Foreground Service (Dart Isolate) │  │
  │  │   WakeLock · WiFi Lock · Socket.IO heartbeat│  │
  │  └─────────────────────────────────────────────┘  │
  └──────────────────────────────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
   REST API        WebSocket
  (HTTP JSON)    (Socket.IO)
  GET/DELETE     live stream
  incidents      P2P chat
```

---

## Dual-Channel Communication

Every HTTP request and WebSocket handshake passes:

- `X-API-Key` — unique cryptographic admin token
- `X-Device-ID` — hardware-derived UUID (prevents echo-loop on multi-device)
- `X-Client-User` — verified user identity (e.g. `FoxiK`)

---

## Foreground Service — 24/7

Android's power management would kill background processes. Sentinel App bypasses this with a persistent Android Foreground Service.

```
App start / biometric unlock
  └──► Spawn Dart Isolate
         ├── WakeLock ──── CPU & modem stay awake
         ├── WiFi Lock ─── Wi-Fi modem stays active
         └── Socket.IO heartbeat (60 s)
                ├── Network switch (Wi-Fi → LTE) → auto-reconnect
                └── Critical packet → flutter_local_notifications
                    (native push, no Google FCM)
```

---

## Incident Matrix

4 domains displayed as colour-coded badges:

| Domain | Description | Colour |
|---|---|---|
| 🗄️ **LOG ISSUES** | Faults from journalctl and edge system logs | Red/Orange |
| 📡 **AGENTS STATUS** | Agent outages or telemetry dropouts | Orange/Yellow |
| 🔑 **ROOT SESSIONS** | Active unmapped root terminal sessions | Red |
| 🛡️ **SECURITY LOGS** | Fail2ban, port scans, CVE updates | Red |

### Incident actions

| Action | Description |
|---|---|
| 🪄 **AI Autofix** | Sends incident to LLM, displays remediation script with Execute/Decline |
| 👁 **Ignore** | Suppresses incident on server and in the app |
| 🗑 **Delete** | Hard delete from the database |
| 🔗 **Share** | Copies hostname, timestamp, log origin and error text to clipboard |

---

## Biometric Authentication

```
App start
  │
  ▼
Biometric challenge (fingerprint / face)
  │
  ├── SUCCESS → Unlock UI + start foreground service
  │
  └── FAIL / swipe from task switcher
        → Immediate session key wipe from RAM
          → Next open requires fresh biometric
```

---

## Visual Offline Mode

When `provider.isOnline` drops to `false`:

- Entire dashboard widget tree gets a greyscale colour matrix filter
- Red overlay banner appears: `SPOJENÍ ZTRACENO - OFFLINE`
- Data polling freezes until reconnected

Since **v2026.06.022** the offline state is only entered after **two consecutive failures** (30 s request timeouts), with a single guarded `_refreshAll()` — no auto-logout and no false OFFLINE flicker on transient blips.

---

## Connection Stability (v2026.06.022)

The client version is synced with the Sentinel server (2026.06.022). Connection and auth were hardened:

- **API-key auto-provisioning** — after LLDAP login the app provisions an API key and switches to the fast `X-API-Key` path, avoiding a per-request LDAP bind
- **Stale-key self-healing** — a `302 → /login` redirect is detected as an auth failure (no false success), and the key is re-provisioned
- **Reused provider/socket** — settings changes reuse the existing provider and Socket.IO connection instead of recreating them
- **Lazy tab loading** — tabs load on demand, removing the startup request storm
- **Full API audit** — all 138 endpoints verified against the running server; corrected dashboard `top_plugins`/`recent_issues`, metric history via `/api/predictions`, plugin stats, and fixed POST payloads (comment templates, patterns)

---

## P2P Admin Chat

Volatile admin-to-admin messaging with **zero database retention**.

- Messages route through Socket.IO room `sentinel_admins` — server is a zero-state relay
- Device badge distinguishes mobile vs. web UI clients
- `X-Device-ID` prevents self-messaging when same admin uses both phone and browser

---

## Technology Stack

| Layer | Technology |
|---|---|
| Framework / Language | Flutter 3.22+ / Dart |
| State Management | Provider + ChangeNotifierProvider |
| Persistence | `shared_preferences` → Android Jetpack Security Crypto |
| Biometrics | `local_auth` (Fingerprint / Face Unlock) |
| Notifications | `flutter_local_notifications` (no FCM) |
| Background | `flutter_background_service` (Dart Isolate) |
| REST | `http` package (10 s timeout) |
| WebSocket | `socket_io_client` (polling → WebSocket upgrade) |
| Build | Native ARM binary (no WebView) |

---

## Build & Deploy

```bash
flutter pub get
flutter pub run flutter_launcher_icons
flutter build apk --release --no-tree-shake-icons
```

Output: `build/app/outputs/flutter-apk/app-release.apk`

### Required AndroidManifest.xml permissions

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
```
