# Sentinel Docs

![License: MIT](https://img.shields.io/badge/License-MIT-cyan.svg)
![MkDocs](https://img.shields.io/badge/MkDocs-Material-blue)
![Languages](https://img.shields.io/badge/languages-EN%20%2B%20CS-green)

**Documentation for the complete Sentinel ecosystem.**

Published at: **https://sentinel-docs.example.com**

MkDocs + Material theme with bilingual (EN / CS) support via the i18n plugin. Covers all Sentinel modules with user guides, technical references, API docs, deployment guides, and troubleshooting.

---

## Contents

| Document | Description |
|---|---|
| `index.md` | Overview, module table, architecture |
| `sentinel-agent.md` | Agent installation, routines, delta filter, wire protocol |
| `sentinel-alert.md` | Alert dashboard setup, modules, work mode |
| `sentinel-app.md` | Flutter app setup, screens, offline mode |
| `sentinel-autofix.md` | AI Autofix workflow, safety classifier, SSH modal |
| `sentinel-console-client.md` | TUI client setup, keybindings |
| `sentinel-hw.md` | Hardware robot wiring, drivers, Web UI |
| `sentinel-overhealth.md` | Orchestrator setup, systemd timer, SSH config |
| `sentinel-plugins.md` | Detector plugins, Pattern Editor, custom detector guide |
| `sentinel/user_documentation.md` | End-user guide — issues, tags, workflow |
| `sentinel/technical_documentation.md` | Architecture, DB schema, routes, config |
| `sentinel/programming_documentation.md` | API reference, Swagger, webhooks |
| `API.md` | Complete REST API — auth scopes, all endpoints, WebSocket events, Prometheus |
| `DEPLOYMENT.md` | Deployment order, nginx, RHEL notes, checklist |
| `TROUBLESHOOTING.md` | Common issues — LDAP, Socket.IO proxy, work mode, 2FA |

---

## Local Development

### Requirements

- Python 3.13+
- MkDocs + Material + plugins

### Install

```bash
git clone https://github.com/foxik0070/sentinel-docs /opt/sentinel-docs
cd /opt/sentinel-docs
python install_docs.py         # interactive: installs venv, configures nginx + systemd
```

Or manually:

```bash
pip install mkdocs mkdocs-material mkdocs-static-i18n mkdocs-minify-plugin
mkdocs serve                   # http://localhost:8000
```

### Build static site

```bash
mkdocs build                   # outputs to site/
```

---

## Language Switch

The docs support English (default) and Czech (`/cs/`). Switch language using the button next to the search bar, or navigate directly:

- English: `https://sentinel-docs.example.com/`
- Czech: `https://sentinel-docs.example.com/cs/`

### nginx note

If `/cs/` returns 404, add to your nginx vhost:

```nginx
port_in_redirect off;
absolute_redirect off;
```

---

## Structure

```
docs/
├── index.md                          # EN home
├── index.cs.md                       # CS home
├── sentinel-agent.md                 # EN
├── sentinel-agent.cs.md              # CS
├── ...
├── sentinel/
│   ├── user_documentation.md
│   ├── technical_documentation.md
│   └── programming_documentation.md
├── API.md
├── DEPLOYMENT.md
├── TROUBLESHOOTING.md
└── stylesheets/
    └── sentinel.css                  # Custom dark sci-fi theme
mkdocs.yml
```

---

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 foxik0070.
