# Sentinel Console — TUI Client

**Type:** Terminal User Interface dashboard (TUI v3.0)  
**Framework:** Textual + httpx  
**Auth:** Cookie session + CSRF token, with fail2ban lockout detection

Real-time HTOP-style terminal dashboard with **full feature parity with the web UI** — works over SSH, in `tmux`/`screen`, and on system consoles.

---

## Layout

```
┌─ SENTINEL TUI v2026.06.013 ─ [WARNING] ─ INFRA ─ Sort:TIME ─ Issues:65/98 ─ LUKAS ──────┐
│  INFRA ████████████  63   AGENT ░░░░░░░░░░░░   2                                          │
│  ROOT  ░░░░░░░░░░░░   0   SEC   ██░░░░░░░░░░   3    TOTAL: 98                             │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  [ALL]   INFRA   AGENT   ROOT   SEC              Sort: TIME                               │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ QUICK ACTIONS  │ ★    TIME             SEV    CH     HOST           MESSAGE               │
│ (l) Log Viewer │ ×3   2026-06-13 23:44  CRIT  INFR   web-01         nginx: connect fail   │
│ (g) Agents     │ ACK  2026-06-13 23:41  HIGH  AGNT   hpc-node-04    CPU spike >95%        │
│ (n) AI Actions │      2026-06-13 23:38  WARN  ROOT   gateway-01     sudo session opened   │
│ (t) Trends     │      2026-06-13 23:35  WARN  SEC    fw-01          port scan detected    │
│ (x) AI Summary │                                                                           │
│ (z) AI Correl. │                                                                           │
│ (i/d/f/a/s)... │                                                                           │
├────────────────┴─────────────────────────────────────────────────────────────────────────┤
│ » hello                                                                                    │
│ ◆ All clear. No critical events in the last 24h.                                           │
│ AI chat > _                                                                               │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ?:Help Enter:Detail Space:Sel i:Ign d:Del f:Fix a:Ack s:Snooze /:Filter q:Quit           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

The header shows an HTOP-style per-channel bar gauge (INFRA / AGENT / ROOT / SEC) with live counts, the active channel/sort, and an `Issues:filtered/total` counter. A left **Quick Actions** panel (toggle with `p`) launches viewers and AI tools; the bottom AI chat panel toggles with `c`.

---

## View Modes

### Split Mode (default)

DataTable (2fr) + Chat Container (1fr) — view incidents while the AI log runs alongside.

### Full Chat Mode (`c`)

DataTable hides → Chat Container expands to 100% → input focus shifts to the query box.

Useful for rapid AI queries:

```
> Why is nginx down on hpc-node-04?
[AI] Analysis: disk full at /var/log/nginx (98%)
     Recommendation: logrotate -f /etc/logrotate.d/nginx
```

---

## Keyboard Shortcuts

### Navigation & view
| Key | Action |
|---|---|
| `↑` / `↓` | Navigate table |
| `Tab` / `Shift+Tab` | Switch channel |
| `1`–`5` | Direct channel select (ALL / INFRA / AGENT / ROOT / SEC) |
| `o` | Toggle sort (TIME → SEV → HOST → CH) |
| `/` / `F2` | Live filter |
| `Esc` | Cancel filter / clear bulk selection |
| `c` | Toggle chat panel |
| `p` | Toggle Quick Actions panel |
| `r` / `F5` | Immediate refresh |
| `q` / `F10` | Quit |

### Issue actions
| Key | Action |
|---|---|
| `Enter` | Issue detail + comments |
| `i` | Ignore |
| `d` | Delete |
| `f` | AI Autofix |
| `a` | Acknowledge / Un-acknowledge |
| `s` | Snooze (1h / 4h / 24h / 72h) |

### Bulk operations
| Key | Action |
|---|---|
| `Space` | Add/remove from selection |
| `Ctrl+A` | Select all (current channel + filter) |
| `I` | Bulk Ignore |
| `D` | Bulk Delete |
| `A` | Bulk Acknowledge |

### AI functions
| Key | Action |
|---|---|
| chat input | Direct question to Sentinel AI |
| `f` | AI Autofix — analysis & fix proposal for the selected issue |
| `x` | AI Summary — overview of all active issues in the current channel |
| `z` | AI Correlation — finds patterns/correlations across issues |
| `t` | AI Trend report — 7-day prediction and trends |

### Modals
| Key | Modal |
|---|---|
| `Enter` | Issue Detail (details, comments, actions) |
| `s` | Snooze |
| `l` | Log Viewer (browse log files) |
| `g` | Agent management (status of all agents) |
| `n` | AI Action suggestions (Execute / Reject pending AI commands) |
| `?` / `F1` | Help |

---

## Autofix Workflow in TUI

```
Press 'f' on selected incident
  │
  ▼
[AI] Generating autofix for: DISK_FULL|proxmox01|/
[AI] Proposed command:
     find /var/log -name "*.log" -mtime +30 -delete
[AI] Risk: LOW
[?] Approve? (y/n):
  │
  └── y → approve request → Sentinel SSH-executes on proxmox01
```

---

## Installation

```bash
git clone git@github.com:foxik0070/sentinel-console.git
cd sentinel-console

# Interactive wizard (generates config + systemd service)
sudo ./sentinel_client_init.py

# Manual run
venv/bin/python sentinel_client.py \
  --url http://sentinel.local:5050 \
  --user admin
```

### Configuration

```ini
# /etc/sentinel/sentinel_client.conf (mode 0600)
[sentinel]
url      = http://sentinel.local:5050
username = admin
interval = 5
```

### Security

- Config file permissions: `0600`
- On 401/403 response: polling freezes (`auth_locked=True`), prevents fail2ban lockout from repeated failed requests
- Cookie manager persists session across terminal reconnects

---

## When to use the Console vs. Web UI

| Scenario | Recommendation |
|---|---|
| SSH session on server | Console — no browser needed |
| tmux / screen | Console — stable in multiplexer |
| Scripting / automation | Console — pipeable AI queries |
| Full dashboard with graphs | Web UI (port 5050) |
| Mobile management | Sentinel App (Android) |
