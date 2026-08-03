# Preparing a Monitored Host for AI Features

For the AI layer to work fully, Sentinel needs an account on each monitored host and precisely scoped permissions. This document explains **what to configure and why** — not just commands to copy.

Without this setup Sentinel still runs and reports problems, but **cannot investigate them in detail**. Diagnostics return nothing, the AI answers from a single log line, and its suggestions will be considerably less useful.

---

## Why a Dedicated Account and Not Root

Sentinel has SSH access to the entire infrastructure and part of its decisions are proposed by a language model. If it connected as root, any mistake — in code, in the model, or injected by an attacker via log content — would have unlimited impact.

The `sentinel` account therefore has no special privileges by default. Root access is granted only for specific commands listed in sudoers, and that list is something you can read and approve. **What is not on that list, Sentinel will not execute** — even if the model proposes it.

---

## 1. User and SSH Key

Create an account without a password; an interactive shell is not required — Sentinel runs individual commands, not sessions.

```bash
useradd --system --create-home --shell /bin/bash sentinel
mkdir -p /home/sentinel/.ssh && chmod 700 /home/sentinel/.ssh
# Sentinel's public key (the counterpart to ssh_execution.key_path on the server)
echo 'ssh-ed25519 AAAA... sentinel@rpi5' > /home/sentinel/.ssh/authorized_keys
chmod 600 /home/sentinel/.ssh/authorized_keys
chown -R sentinel:sentinel /home/sentinel/.ssh
```

Sentinel connects with `BatchMode=yes` — **no command may ask for a password**. If it does, the connection silently fails. That is why `NOPASSWD` is used in sudoers below.

It is recommended to restrict the key on the `authorized_keys` side too (`from="SENTINEL_IP"`) so it cannot be used from anywhere else.

---

## 2. The `systemd-journal` Group — Without It Diagnostics Are Half-Blind

This is the most commonly overlooked step, and it shows up quietly: `journalctl` returns a polite message saying it sees nothing, and the AI concludes there is nothing in the log.

```bash
usermod -aG systemd-journal sentinel
```

Membership takes effect **only after a new login**. Watch out for shared SSH connections (`ControlPersist`) — they hold the original groups until they expire.

Verify:

```bash
ssh sentinel@HOST id -nG          # must include systemd-journal
ssh sentinel@HOST journalctl -n 5 --no-pager
```

If the second command prints *"You are currently not seeing messages from other users and the system"*, the group is missing or has not taken effect yet.

---

## 3. Sudoers — What Sentinel May Do as Root

The sudoers file must be a **subset** of the application whitelist (`allowed_commands` in Sentinel's config). Both the application and the OS must agree, otherwise the command is not executed — two independent safety mechanisms.

Create `/etc/sudoers.d/sentinel` (always via `visudo -f` so a typo does not lock sudo):

```
# Diagnostics — read-only, but root for full output
sentinel ALL=(root) NOPASSWD: /usr/bin/ss -tlnp
sentinel ALL=(root) NOPASSWD: /usr/bin/ss -tlnH
sentinel ALL=(root) NOPASSWD: /usr/bin/du -sh /var/*
sentinel ALL=(root) NOPASSWD: /bin/mount
sentinel ALL=(root) NOPASSWD: /usr/bin/dpkg -l

# Remediation — only specific services, not wildcards
sentinel ALL=(root) NOPASSWD: /bin/systemctl restart nginx.service
sentinel ALL=(root) NOPASSWD: /bin/systemctl restart <other specific units>

# Log maintenance
sentinel ALL=(root) NOPASSWD: /usr/bin/journalctl --vacuum-time=7d
sentinel ALL=(root) NOPASSWD: /usr/bin/journalctl --rotate
```

Think carefully about what you put here. **Do not write `systemctl restart *`** — that would allow restarting anything including `sshd`, losing your own access to the host. List the specific units you want managed automatically.

Verify (must not ask for a password):

```bash
ssh sentinel@HOST 'sudo -n ss -tlnp | head -3'
```

### Which Commands Need Sudo

Sentinel prefixes `sudo -n` **only** for these command prefixes; everything else runs without elevated privileges:

| Group | Commands |
|---|---|
| Service management | `systemctl restart/start/stop/enable/disable/mask/unmask/reload/daemon-reload` |
| Filesystems | `mount`, `umount` |
| Packages | `apt-get`, `apt`, `dpkg` |
| Log maintenance | `journalctl --rotate`, `journalctl --vacuum` |
| Backups | `proxmox-backup-client garbage-collect` |
| Host restart | `reboot`, `shutdown`, `poweroff` |
| Diagnostics with full output | `ss`, `du` |

Standard diagnostics run **without sudo**: `df`, `free`, `uptime`, `ps`, `systemctl status`, `systemctl --failed`, `journalctl -p err`, `ip addr`, `dmesg`, `who`, `uname`.

---

## 4. Required Packages on the Host

The AI diagnostics picks from a fixed command catalog. A missing tool does not crash Sentinel — the step returns an error — but it reduces diagnostic quality unnecessarily.

| Package | Used for |
|---|---|
| `iproute2` | `ss`, `ip` — ports and interfaces |
| `procps` | `free`, `uptime`, `ps` |
| `coreutils` | `df`, `du`, `who` |
| `systemd` | `systemctl`, `journalctl`, `timedatectl` |
| `util-linux` | `dmesg`, `mount` |

On minimal images (Alpine, distroless containers) some of these may be absent or have different syntax. Expect limited diagnostics there.

---

## 5. Reading Application Logs

Sentinel reads the system journal, but applications often write to their own files. When a directory is only accessible to root, diagnostics cannot reach them and **you only learn the service crashed, not why**.

Three options, ordered from best:

1. **Direct the application to write to the journal** (`StandardOutput=journal` in the unit). Cleanest — Sentinel has access via `systemd-journal` and nothing else needs to be set.
2. **Add `sentinel` to the group that owns the logs** (`usermod -aG adm sentinel` if logs belong to group `adm`).
3. **Allow specific reading in sudoers** — most explicit, but requires maintenance:
   ```
   sentinel ALL=(root) NOPASSWD: /usr/bin/tail -n 50 /var/log/myapp/app.log
   ```

> Real example: `/var/log/rpi-backup/` has permissions `drwxr-x--- root root`, so Sentinel knows a backup failed but cannot read the reason from the log.

---

## 6. Verify the Setup

```bash
HOST=your-host

ssh sentinel@$HOST id -nG                    # includes systemd-journal?
ssh sentinel@$HOST journalctl -n 3 --no-pager # returns entries, not a permissions message?
ssh sentinel@$HOST 'sudo -n ss -tlnp | head' # passes without a password prompt?
ssh sentinel@$HOST 'df -h; free -m; systemctl --failed --no-pager'
```

From inside Sentinel itself:

```bash
sudo python3 -c "
from sentinel import actions
for c in ('id -nG', 'journalctl -n 3 --no-pager', 'df -h'):
    ok, out = actions.run_ssh_command_real('$HOST', c, timeout=20, internal=True)
    print(('OK  ' if ok else 'ERROR'), c, '->', out[:80].replace(chr(10),' '))"
```

Note: run as **root** (`sudo`), because the known-hosts file `/var/lib/sentinel/known_hosts` is owned by root. As another user, adding an unknown host will fail.

---

## 7. When AI Answers Poorly

Before tuning prompts, check these — in most cases the cause is here:

| Symptom | Most likely cause |
|---|---|
| "Not enough information" for everything | Missing `systemd-journal` membership, diagnostics return empty |
| Diagnostics report empty output | Missing tool (`iproute2`, `procps`) |
| Generic suggestions with no reference to host state | Diagnostic steps failing — check sudoers |
| "sudo: a password is required" | Missing `NOPASSWD` or command not in sudoers |
| Knows a service crashed but not why | Application log outside journal and unreadable — see section 5 |

A complete list of operational pitfalls is in [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Minimal Setup Checklist

```bash
useradd --system --create-home --shell /bin/bash sentinel
usermod -aG systemd-journal sentinel
install -d -m 700 -o sentinel -g sentinel /home/sentinel/.ssh
echo 'ssh-ed25519 AAAA... sentinel@rpi5' > /home/sentinel/.ssh/authorized_keys
chmod 600 /home/sentinel/.ssh/authorized_keys
chown sentinel:sentinel /home/sentinel/.ssh/authorized_keys
visudo -f /etc/sudoers.d/sentinel     # see section 3
```

This gives Sentinel **read access to host state and the system log**. The right to change anything is only granted where you explicitly put it in sudoers — and even then, any change proposal goes through approval in the UI.
