# AI Autofix & Bezpečné akce

Autofix je AI-driven remediační pipeline Sentinelu. Když detektor vyvolá incident, LLM analyzuje kontext logu a navrhne konkrétní bash příkaz k opravě problému. Příkaz je zobrazen adminovi s metadaty o riziku a dry-run preview. **Nic se nespustí, dokud to admin explicitně neschválí.**

---

## Jak to skutečně funguje

Autofix není magie — je to přísně kontrolovaný pipeline:

1. **Spuštění** — admin klikne 🪄 na kartě incidentu, nebo systém spustí automaticky pro nakonfigurované detektory
2. **AI analýza** — kontext logu + metadata incidentu se pošle Ollama LLM (NPU nebo CPU)
3. **Safety gate** — `safety.classify()` ohodnotí navrhovaný příkaz vůči allowlistu `allowed_commands`
4. **Dry-run preview** — `safety.simulate()` spustí read-only náhled toho, co by příkaz udělal
5. **Souhlas admina** — návrh se zobrazí v modalu Web UI s risk score, dry-run výstupem a tlačítky Schválit/Zamítnout
6. **SSH spuštění** — pouze po explicitním souhlasu, `actions.py` se připojí na cílový management node a spustí příkaz
7. **Verifikace** — incident přechází do stavu `validating`; pokud detektor problém v dalším cyklu nevidí, auto-resolved

```
Incident detekován
   │
   ├─ AI analyzuje kontext logu
   │      └─ Ollama worker → { command, description, confidence }
   │
   ├─ safety.classify() kontroluje allowlist + pravidla rizika
   │      └─ pokud BLOCKED → okamžitě odmítnuto, modal se nezobrazí
   │
   ├─ safety.simulate() generuje dry-run preview
   │
   ▼
Admin modal (Web UI nebo mobilní aplikace)
   ┌────────────────────────────────────────────┐
   │  Návrh: systemctl restart postgresql       │
   │  Riziko: LOW  │  Node: db-node-02          │
   │  Dry-run: restartuje PostgreSQL service    │
   │                                            │
   │  [✅ Schválit]        [❌ Zamítnout]       │
   └────────────────────────────────────────────┘
   │
   └─ Schválit → SSH exec → STDOUT/STDERR zalogován
              → status incidentu: running → completed
              → detektor potvrdí opravu → resolved ✓
```

---

## Co Autofix umí a neumí

**Umí:**

- Restartovat failnutou službu (`systemctl restart <svc>`)
- Znovu připojit filesystém (`mount -a`, `mount /dev/... /mnt/...`)
- Rotovat logy (`logrotate -f ...`)
- Spustit vlastní diagnostické skripty na allowlistu
- Dosáhnout na nody za bastionem přes ProxyJump

**Neumí (by design):**

- Spustit cokoliv, co není na allowlistu `allowed_commands`
- Spustit destruktivní příkazy (`rm -rf`, `mkfs`, `shutdown`) — automaticky blokováno
- Spustit bez souhlasu admina, pokud není explicitně nastaven `auto_execute: true`
- Obejít dry-run preview
- Působit na nody, které nejsou v mappingu `infrastructure`

---

## Safety klasifikátor

`safety.classify()` vyhodnotí každý navrhovaný příkaz ještě před zobrazením modalu:

| Úroveň rizika | Příklady | Chování |
|---|---|---|
| **LOW** | `systemctl restart nginx`, `logrotate -f` | Zelené — zobrazí se normálně |
| **MEDIUM** | `apt-get install`, `mount -a`, `sysctl -w` | Žluté varování |
| **HIGH** | `rm -rf`, `dd if=`, `mkfs`, `iptables -F` | Červené varování, nutné extra potvrzení |
| **BLOCKED** | `shutdown`, `reboot`, `halt`, fork bombs | Odmítnuto tiše — admin vůbec neuvidí |

Příkazy neodpovídající žádnému vzoru v `allowed_commands` jsou také blokovány bez ohledu na risk level.

---

## Konfigurace

```yaml
# /etc/sentinel/config.yaml

allowed_commands:
  # Restart konkrétní služby — nízké riziko, vyžaduje souhlas
  - pattern: "systemctl restart *"
    auto_execute: false
    risk: low

  # Znovu připojit filesystémy — střední riziko, vždy manuálně
  - pattern: "mount -a"
    auto_execute: false
    risk: medium

  # Vlastní diagnostika — auto-execute bezpečné read-only příkazy
  - pattern: "journalctl -u * --since *"
    auto_execute: true
    risk: low

infrastructure:
  - hostname: "db-node-02"
    ssh_user: root
    management_node: true
    # Routování přes bastion:
    ssh_jump_host: "bastion.example.com"
    ssh_jump_user: "jump"
```

---

## Autonomní spuštění

Při `auto_execute: true` Sentinel přeskočí schvalovací modal a spustí přímo. Používejte pouze pro bezpečné, idempotentní nebo read-only příkazy.

Selhání vždy vytvoří `AUTOFAIL` issue s červeným badge — i při `auto_execute`. Vždy víte, když něco šlo špatně.

---

## SSH Jump Host (ProxyJump)

Produkční clustery mají compute nody za bastionem. Autofix to řeší transparentně:

```yaml
infrastructure:
  - hostname: "hpc-node-01"
    ssh_user: root
    management_node: true
    ssh_jump_host: "bastion.example.com"
    ssh_jump_user: "jumpuser"
```

Vygenerovaný SSH příkaz:

```bash
ssh -J jumpuser@bastion.example.com root@hpc-node-01 'systemctl restart nginx'
```

---

## SSH Modal (admin+)

Pro situace, kdy Autofix není spuštěn, ale potřebujete přímý přístup — SSH Modal umožňuje adminům spouštět příkazy (na allowlistu) na libovolném agentovi přímo z Web UI:

1. Klikněte na agenta → otevřete detail modal agenta
2. Klikněte **SSH** (role `admin` nebo `superadmin`)
3. Pište příkazy — živý výstup streamován přes SSE
4. Vše logováno v tabulce `ssh_execute_log` s actorem, timestampem, STDOUT/STDERR

---

## Lifecycle akce

```
created (pending)
   │
   ├─ auto_execute=true → running → completed ✓
   │                             └─→ failed → AUTOFAIL issue 🔴
   │
   └─ admin modal
         ├─ Schválit → running → completed ✓
         │                    └─→ failed → AUTOFAIL issue 🔴
         └─ Zamítnout → rejected
```

Každý přechod je zalogován v `action_audit` s actorem, timestampem, risk score a detaily.

---

## Eskalační pravidla

Issues, které přetrvávají bez řešení, automaticky eskalují:

```yaml
escalation_rules:
  - channel: infra
    after_hours: 4
    raise_to: high
  - channel: security
    after_hours: 1
    raise_to: critical
```

Eskalované issues zobrazují živý timer badge: `⏱ 3h active`.

---

## API

| Metoda | Cesta | Auth | Popis |
|---|---|---|---|
| GET | `/api/v1/actions` | read | Seznam pending/recent akcí |
| POST | `/api/v1/actions/<id>/approve` | admin | Schválit a spustit |
| POST | `/api/v1/actions/<id>/reject` | admin | Zamítnout návrh |
| GET | `/api/v1/actions/<id>/output` | read | Stream výstupu (SSE) |
| GET | `/api/v1/actions/<id>/audit` | read | Plný lifecycle audit trail |
