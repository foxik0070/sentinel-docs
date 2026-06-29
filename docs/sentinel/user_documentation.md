# Sentinel Commander — User Guide (v2026.06.024)

Intended for operators, administrators, and security technicians interacting with Sentinel via the web interface or the mobile app.

---

## Access & Roles (RBAC)

The web interface runs on port **5050** and requires authentication. LDAP is supported (lldap and OpenLDAP).

| Role | Permissions |
|---|---|
| **viewer** | Read incidents and telemetry, use AI chat (RAG queries) |
| **admin** | Everything above + Approve/Reject Autofix, SSH modal, batch SSH, manage agents |
| **superadmin** | Everything above + Settings, API keys, bulk delete, audit trail, DB management |

### Login

Standard: username + password form.
LDAP: same form — credentials are validated against the configured LDAP server.

**Two-factor authentication (2FA/TOTP):** if enabled for your account, a second step asks for a 6-digit code from Google Authenticator / Authy. Enrollment is done in **Settings → 2FA** — scan the QR code with your authenticator app and confirm with one code. An admin can disable 2FA for any user who lost their device.

**Brute-force protection:** 5 failed attempts → IP banned for 5 minutes (configurable). This applies to the login form, Basic auth, and agent auto-registration alike.

**Session:** absolute timeout 12 h; your role is re-checked from the database every 5 minutes, so a role change takes effect without re-login.

The login page links to the public **/status** page (read-only fleet overview, auto-refresh every 30 s, no login required).

---

## Dashboard Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  SENTINEL COMMANDER v2026.06  [CS/EN] [🌙] [?] (User) (Alerts)   │
├─────────────────────┬────────────────────────────────────────────┤
│  SYSTEM MONITOR     │  ACTIVE INCIDENTS                          │
│  CPU ████── 45%     │  [!] security  brute-force on hpc-gw       │
│  RAM █████─ 75%     │      [🪄] [👁] [🗑] [✓✓] [#tag] [🔔]      │
│  Disk 20%           │  [!] infra  DISK_FULL proxmox01:/data 92%  │
│  AI latency 1.2s    │      acknowledged ● [#storage]             │
│  RAG: Ready         │  ▙ flapping widget ▟  ▙ health trend ▟     │
├─────────────────────┴────────────────────────────────────────────┤
│  AI CHAT   [suggested: "What changed overnight?"] [LIVE]         │
│  Sentinel: Detected memory error on node-01.                     │
│  > Enter query, command, or drag&drop a log file...              │
└──────────────────────────────────────────────────────────────────┘
```

### UI panels

| Panel | Content |
|---|---|
| **System Monitor** | CPU/RAM/disk, AI latency, queue depth, RAG status, agent count |
| **Active Incidents** | Cards per channel: security · infra · agents · root |
| **AI Chat** | RAG queries, chat commands, suggested query chips, LIVE context tag, drag&drop log upload |
| **Health trend** | 7-day line chart of fleet health score + issue count |
| **Flapping widget** | Issues that keep re-appearing, sorted by frequency |
| **Topology** | Force-directed agent graph (Tools tab) |
| **Telemetry** | Interactive charts with min/max/avg, heatmaps, trend charts |

**Charts:** all major charts (dashboard trend, donut, alert timeline, agent sparklines) are interactive — hover shows exact values, a dashed line marks the average, and a min/max/avg badge summarizes the window.

**i18n:** Toggle between Czech and English via the `CS/EN` button in the top bar. Dark/light theme via the 🌙 icon. Both preferences persist in `localStorage`. Display timezone is configurable server-side (`DISPLAY_TZ`).

**Dashboard widgets** can be individually shown/hidden in dashboard settings; a live clock sits in the header.

---

## Issue Cards & Workflow

Every detected incident appears as a card. The full workflow:

```
active → acknowledged (✓✓) → validating → resolved
```

### Card actions

| Button | Action |
|---|---|
| 🪄 **Autofix** | Request AI remediation proposal |
| 👁 **Ignore** | Suppress this incident (adds to ignore list) |
| 🗑 **Delete** | Hard delete from DB (reappears if log still produces it) |
| ✓✓ **Acknowledge** | Mark as seen — card turns yellow, escalation timer resets |
| **#tag** | Add or edit tags on the incident |
| 🔔 **Notifications** | Open per-detector/channel notification settings |
| ↕ **Fullscreen** | Open the issue in a fullscreen overlay (detail + AI analysis + comments + similar incidents, Esc closes) |
| **▾ Collapse** | Collapse card to summary view |
| **⋯ History** | Open incident timeline (comments, auto-rem, acknowledge events) |

Additional card features:

- **Inline comments** — write a comment directly on the card; auto-refresh never wipes text you are typing.
- **Colored labels** — assign color labels for visual triage.
- **Copy as Markdown** — one click copies a Markdown summary of the issue (handy for tickets/chat).
- **Occurrence counter** — repeated detections increment a counter instead of creating duplicates.
- **Mobile swipe** — swipe right = acknowledge, swipe left = delete.
- **Virtual scroll** — long lists load 50 cards at a time with a "Load more" button.

### Bulk operations & keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Alt+A` | Bulk acknowledge selected issues |
| `Alt+E` | Export selected issues to CSV |
| `Alt+F` | Focus the issue filter |
| `Esc` | Close the topmost modal |
| `?` | Show shortcut overlay |

### Issue tagging

Type `#tag` in the tag input, or define auto-tag rules in config:

```yaml
auto_tags:
  - pattern: "DISK_FULL"
    tag: "storage"
  - pattern: "fail2ban"
    tag: "security"
```

Tags are searchable and shown in the tag cloud panel.

### Escalation badges

If an issue stays unresolved beyond the configured time, its severity rises automatically and a timer badge appears: `⏱ 3h active`. Escalation rules are set per channel in `config.yaml`. Issue lifecycle transitions (CREATED / ACKNOWLEDGED / RESOLVED) can additionally fire **webhooks**, and critical issues can be mirrored to **Gitea** as repository issues.

---

## Autofix — Approving AI Proposals

1. Click **🪄 Autofix** on an incident card (or type `autofix` in chat).
2. AI analyses the log context and generates a bash command.
3. A "Pending Action" modal appears with the proposed command, risk score, and dry-run preview.
4. Click **✅ Approve** — command executes via SSH on the target node.
   Click **❌ Reject** — proposal is discarded.
5. On success: incident enters `validating` state, then `resolved` once the detector confirms. Output is shown even for silent commands (`exit 0, no output`) and the modal stays open until you read the result.

> Commands must be on the `allowed_commands` allowlist in `config.yaml`. Blocked commands are automatically rejected regardless of admin input — the allowlist is pre-validated *before* any SSH connection is made.

**SSH Jump Host:** If the target node is behind a bastion, Autofix automatically uses ProxyJump.

---

## SSH Modal & Batch SSH (admin+)

Direct SSH access to any agent from the Web UI without going through the Autofix pipeline:

1. Click any agent in the Agents view → open the agent detail modal.
2. Click **SSH** button (requires `admin` or `superadmin`).
3. Type commands — output streams live in the modal.
4. All commands are logged in the audit trail.

**Batch SSH:** the "Batch SSH" modal lets you run one allowlisted command on up to 50 agents in parallel (checkbox list with online/offline indicators); results are shown per host with OK/FAIL colors. Each host has its own 15 s timeout so one stuck node cannot block the batch.

**SSH host keys:** the agent detail shows the recorded `known_hosts` keys with **Rescan** and **Delete** actions — host keys are pinned (`accept-new`), not blindly trusted.

---

## Agent Detail

The agent modal aggregates everything about one node:

| Section | Content |
|---|---|
| **Telemetry** | CPU/RAM/disk sparklines with min/max/avg, anomaly markers |
| **Health score** | Composite 0–100 score with A–D grade |
| **Packages** | On-demand package inventory (`dpkg`/`rpm`) with live filter |
| **CVE scan** | Pending security updates via `apt`/`dnf` over SSH |
| **HW metrics** | Network throughput, GPU (nvidia/rocm), disk SMART, UPS status |
| **Scheduled actions** | Pending/planned actions for this host |
| **Maintenance windows** | Per-host snooze windows with pre-filled hostname |
| **Heartbeat timeout** | Per-agent override (30–86400 s) or global default |
| **Thresholds** | Per-agent CPU/RAM/disk alert rules with quick-buttons (CPU > 90 %, RAM > 90 %, Disk > 85 %) — enforced server-side on every ingest |
| **SSH keys** | known_hosts entries, rescan/delete |
| **Deploy helper** | One-liner install command generator |

**Registration:** the token modal shows the agent token with a copy button and a **QR code** (`{hostname, token, ingest_url}`) for phone-assisted setup. Superadmin can bulk-rotate all agent tokens.

---

## AI Chat Commands

| Command | Role | Action |
|---|---|---|
| `status` / `stav` | all | Full aggregated incident overview in chat |
| `sys` | all | Live system monitor widget inserted into chat |
| `pending` | all | List Pending Actions (Approve/Reject from chat) |
| `show_ignored` | all | List suppressed incidents with Unignore button |
| `batch` | admin | Batch AI analysis of up to 50 active issues |
| `delete_all_issues` | admin+ | Clear all issues and pending actions |
| `delete_key <hash>` | admin+ | Delete one specific issue by key |
| `clear file` | all | Release uploaded file context, return to RAG |
| `?` | all | Show keyboard shortcuts overlay |

Chat extras:

- **Suggested queries** — contextual chips under the input ("What changed overnight?", "Summarize security issues"…).
- **LIVE tag** — enriches your question with the current active-issue context before sending it to the AI.
- **Markdown rendering** — AI answers render bold, headings, code blocks (highlight.js) and bullet lists.
- **Export chat** — one click saves the conversation as Markdown.

---

## Drag & Drop Log Analysis

Upload a `.log`, `.txt`, or `.md` file into the chat area (or click the paperclip icon).

- AI context switches from RAG to the uploaded file content (first ~15 000 characters).
- Ask specific questions: *"List all DNS errors and when they started."*
- Release with `clear file` command to return to normal RAG mode.

---

## Telemetry, Analytics & Reports

Available on the dashboard and under **Tools**:

- **Sparkline graphs** — top-6 hottest hosts, temperature over time
- **Trend chart** — capacity growth with TTC prediction
- **Host Heatmap** — incident density per host per day
- **Health Score** — composite grade A–D per agent + 7-day fleet health trend chart
- **Anomaly detection** — 3σ spikes flagged with red dot on timeline
- **Analytics tab** — SLA resolution-time table + alert-fatigue chart (false positives per plugin)
- **Issue forecast** — 7-day linear-regression outlook of issue volume
- **Capacity tab** — AI capacity planning: per-host HOST/PROBLEM/RECOMMENDATION/PRIORITY cards + capacity prediction (time-to-full for disk/RAM)
- **Comparison tab** — compare two telemetry time windows (delta + % difference)
- **Alert timeline** — interactive chart of alert volume with min/max/avg
- **Auto-clustering** — "Clusters" button groups related issues (same plugin on N hosts / same host with N issues in a 30 min window); AI names the probable root cause
- **Postmortem** — generate an AI Markdown postmortem for any resolved incident
- **Weekly digest** — includes flapping issues and average resolution time

---

## Runbooks

**Tools → Runbooks** keeps operational procedures next to the incidents:

- CRUD list of runbooks (create, edit, delete)
- Open any runbook in a modal while working on an issue

---

## Topology Map

Available under **Tools → Topology**:

- Force-directed graph of all agents and their network relationships
- Colour by state: green (OK) → yellow (warning) → red (critical) → grey (offline)
- SNMP CDP/LLDP data merged with agent data
- Click a node to open the agent detail modal

---

## Notification Settings

Click any 🔔 icon (issue card, issues toolbar, Plugin Stats):

- **Channels** — enable/disable notifications per channel (infra / agent / security / root)
- **Integrations** — toggle each outbound integration (Teams, Slack, Discord, Telegram, Opsgenie, ntfy, Gotify, SMTP, Matrix, PagerDuty, HA, MQTT, Webhook)
- **Per-detector** — each plugin row in Plugin Stats has its own 🔔 toggle
- Integration credentials are configured inline in the **Notifications & Integrations** modal (Save + Test buttons per tab); secret fields are never displayed back

Notifications are throttled per severity (critical/security/root 15 min, high 1 h, medium/low 4 h) and failed deliveries retry automatically with backoff.

---

## Settings (superadmin)

| Section | What you can configure |
|---|---|
| **Config editor** | Live edit `config.yaml`, save triggers hot-reload; schema validation blocks invalid values |
| **2FA** | Enroll/disable TOTP, QR code provisioning |
| **Hash password** | Generate a bcrypt hash ready to paste into `config.yaml` |
| **REST API keys** | Create/revoke scoped API keys (`read:issues` / `write:actions` / `admin:users`) |
| **Pattern Editor** | Add custom regex detection patterns with live tester + AI pattern suggestions from historical issues |
| **Plugin hot-reload** | Reload all plugins without server restart |
| **Suppress rules** | Define false positive patterns for auto-suppression (with hit counters) |
| **Config diff** | Compare any two config snapshots (selectors + diff view) |
| **Config backup/restore** | Restore creates an automatic backup of the current config first (10 kept) |
| **DB management** | DB size, record counts, "Prune now", "Aggregate telemetry" |
| **Audit trail** | Who changed config, ran SSH commands, approved actions — with IP and timestamp |
| **Log level** | Change server log level at runtime |
| **Changelog** | Git log of recent code changes |

---

## Mobile App

See [Sentinel App documentation](../sentinel-app.md). The app mirrors all dashboard functionality with:

- Biometric authentication (fingerprint / face)
- Push notifications (no Google FCM)
- P2P admin chat (volatile, no DB)
- Visual offline mode (greyscale + red banner)
