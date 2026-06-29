# AI Autofix & Safe Actions

Autofix is Sentinel's AI-driven remediation pipeline. When a detector raises an incident, the LLM analyses the log context and proposes a concrete bash command to fix the problem. The command is shown to an admin with risk metadata and a dry-run preview. **Nothing executes until an admin explicitly approves it.**

---

## How it actually works

Autofix is not magic — it is a tightly controlled pipeline:

1. **Trigger** — admin clicks 🪄 on an incident card, or the system auto-triggers for configured detectors
2. **AI analysis** — the log context + incident metadata is sent to the Ollama LLM (NPU or CPU)
3. **Safety gate** — `safety.classify()` scores the proposed command against the `allowed_commands` allowlist
4. **Dry-run preview** — `safety.simulate()` runs a read-only preview of what the command would do
5. **Admin approval** — the proposal appears in the Web UI modal with risk score, dry-run output, and Approve/Reject buttons
6. **SSH execution** — only after explicit approval, `actions.py` connects to the target management node and runs the command
7. **Verification** — the incident enters `validating` state; if the detector stops seeing the problem in the next cycle, it auto-resolves

```
Incident detected
   │
   ├─ AI analyses log context
   │      └─ Ollama worker → { command, description, confidence }
   │
   ├─ safety.classify() checks allowlist + risk rules
   │      └─ if BLOCKED → rejected immediately, no modal shown
   │
   ├─ safety.simulate() generates dry-run preview
   │
   ▼
Admin modal (Web UI or mobile app)
   ┌────────────────────────────────────────────┐
   │  Proposed: systemctl restart postgresql    │
   │  Risk: LOW  │  Node: db-node-02            │
   │  Dry-run: would restart PostgreSQL service │
   │                                            │
   │  [✅ Approve]        [❌ Reject]           │
   └────────────────────────────────────────────┘
   │
   └─ Approve → SSH exec → STDOUT/STDERR logged
              → incident status: running → completed
              → detector confirms fix → resolved ✓
```

---

## What Autofix can and cannot do

**Can do:**

- Restart a failed service (`systemctl restart <svc>`)
- Re-mount a filesystem (`mount -a`, `mount /dev/... /mnt/...`)
- Rotate logs (`logrotate -f ...`)
- Run custom diagnostic scripts on the allowlist
- Reach nodes behind a bastion via ProxyJump

**Cannot do (by design):**

- Execute anything not on the `allowed_commands` allowlist
- Run destructive commands (`rm -rf`, `mkfs`, `shutdown`) — automatically blocked
- Execute without admin approval unless `auto_execute: true` is explicitly set
- Bypass the dry-run preview
- Act on nodes that aren't in the `infrastructure` mapping

---

## Safety Classifier

`safety.classify()` evaluates every proposed command before the modal is shown:

| Risk level | Examples | Behaviour |
|---|---|---|
| **LOW** | `systemctl restart nginx`, `logrotate -f` | Green — shown normally |
| **MEDIUM** | `apt-get install`, `mount -a`, `sysctl -w` | Yellow warning |
| **HIGH** | `rm -rf`, `dd if=`, `mkfs`, `iptables -F` | Red warning, extra confirmation required |
| **BLOCKED** | `shutdown`, `reboot`, `halt`, fork bombs | Rejected silently — never reaches admin |

Commands not matching any pattern in `allowed_commands` are also blocked, regardless of risk level.

---

## Configuration

```yaml
# /etc/sentinel/config.yaml

allowed_commands:
  # Restart a specific service — low risk, requires approval
  - pattern: "systemctl restart *"
    auto_execute: false
    risk: low

  # Re-mount filesystems — medium risk, always manual
  - pattern: "mount -a"
    auto_execute: false
    risk: medium

  # Custom diagnostic — auto-execute safe read-only commands
  - pattern: "journalctl -u * --since *"
    auto_execute: true
    risk: low

infrastructure:
  - hostname: "db-node-02"
    ssh_user: root
    management_node: true
    # Route through a bastion:
    ssh_jump_host: "bastion.example.com"
    ssh_jump_user: "jump"
```

---

## Autonomous Execution

When `auto_execute: true`, Sentinel skips the approval modal and executes directly. Use only for safe, idempotent, read-only or known-safe commands.

Failures always create an `AUTOFAIL` issue with a red badge — even when `auto_execute` is on. You always know when something went wrong.

---

## SSH Jump Host (ProxyJump)

Production clusters often place compute nodes behind a bastion. Autofix handles this transparently:

```yaml
infrastructure:
  - hostname: "hpc-node-01"
    ssh_user: root
    management_node: true
    ssh_jump_host: "bastion.example.com"
    ssh_jump_user: "jumpuser"
```

The generated SSH command:

```bash
ssh -J jumpuser@bastion.example.com root@hpc-node-01 'systemctl restart nginx'
```

---

## SSH Modal (admin+)

For situations where Autofix isn't triggered but you need direct access, the SSH Modal lets admins run arbitrary (allowlisted) commands on any agent node from the Web UI:

1. Click an agent → open agent detail modal
2. Click **SSH** (requires `admin` or `superadmin`)
3. Type commands — live output streams via SSE
4. All commands logged in `ssh_execute_log` table with actor, timestamp, STDOUT/STDERR

---

## Action Lifecycle

```
created (pending)
   │
   ├─ auto_execute=true → running → completed ✓
   │                             └─→ failed → AUTOFAIL issue 🔴
   │
   └─ admin modal
         ├─ Approve → running → completed ✓
         │                   └─→ failed → AUTOFAIL issue 🔴
         └─ Reject  → rejected
```

Every transition is logged in `action_audit` with actor, timestamp, risk score, and details.

---

## Escalation Rules

Issues that linger without resolution automatically escalate:

```yaml
escalation_rules:
  - channel: infra
    after_hours: 4
    raise_to: high
  - channel: security
    after_hours: 1
    raise_to: critical
```

Escalated issues show a live timer badge: `⏱ 3h active`.

---

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/actions` | read | List pending/recent actions |
| POST | `/api/v1/actions/<id>/approve` | admin | Approve and execute |
| POST | `/api/v1/actions/<id>/reject` | admin | Reject proposal |
| GET | `/api/v1/actions/<id>/output` | read | Stream execution output (SSE) |
| GET | `/api/v1/actions/<id>/audit` | read | Full lifecycle audit trail |
