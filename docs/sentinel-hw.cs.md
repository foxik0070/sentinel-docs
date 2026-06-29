# Sentinel HW — Fyzický monitorovací robot

**Platforma:** Raspberry Pi Zero 2 W  
**Python:** 3.13+

Sentinel HW je **fyzický ambientní monitoring companion** pro váš serverový cluster. Přeměňuje surový stav infrastruktury na viditelné, slyšitelné a hmatatelné signály — bez obrazovek, klávesnic nebo dashboardů.

Když je vše v pořádku, jeho oči klidně září zeleně. Při bezpečnostním incidentu se rozzlobí do červena a bzučák zaječí. Když v místnosti nikdo není, ztlumí se do téměř neviditelného pohotovostního svitu. Je vždy zapnutý, vždy hlídá, vždy říká pravdu o stavu vaší infrastruktury.

Postavený na Raspberry Pi Zero 2 W, každých 30 sekund polluje Sentinel API a odráží aktuální závažnost incidentů skrze: animovaný ST7789 displej (oči), 8-LED NeoPixel kruh (barva + vzor), KY-006 bzučák (tóny), vibrační motor (haptický puls) a volitelně hlasový syntetizátor Piper TTS.

---

## Hardwarové komponenty

| Komponenta | Model / specifikace | Poznámka |
|---|---|---|
| Mikropočítač | Raspberry Pi Zero 2 W | MicroSD 16 GB+, zdroj 5 V / 2,5 A |
| Displej | 2,0" IPS SPI ST7789, 320×240 | Verze s vyvedeným CS pinem! |
| LED kruh | 8× WS2812B NeoPixel (kruhový modul) | 5 V napájení |
| Bzučák | KY-006 pasivní | PWM na GPIO 13 |
| Vibrační motorek | ERM vibrační modul | GPIO 26 |
| Dotykový senzor | TTP223 kapacitní | Montáž pod horní stěnu |
| Radar pohybu | RCWL-0516 mikrovlnný | Funguje přes plast |
| Světelný senzor | BH1750 I2C | Auto-jas |

### Volitelné — hlasová syntéza (TTS)

| Komponenta | Model | Cena (orientačně) |
|---|---|---|
| I2S DAC + zesilovač | MAX98357A breakout | ~100 Kč |
| Reproduktor | 4 Ω / 2–3 W / 40–50 mm | ~80 Kč |

Detailní schéma zapojení viz [WIRING.md](https://git.example.com/lukas/sentinel-hw/src/branch/main/WIRING.md).

---

## Architektura

```text
                    ┌─────────────────────────────────┐
                    │         Sentinel HW (RPi)        │
                    │                                  │
  ┌───────────────┐ │  sentinel.py  ←  SentinelAPI     │
  │ chat_service  │ │      ↓           (polling 30 s)  │
  │  :5050        │◄──── REST API  ─────────────────── │
  │  /api/v1/     │ │                                  │
  │  issues       │ │  web_ui.py (Flask :5055)         │
  └───────────────┘ │      ↑                           │
                    │  config.yaml                     │
                    │                                  │
                    │  Hardware drivery:               │
                    │  display / leds / buzzer         │
                    │  motor / touch / radar           │
                    │  light / tts / monitor           │
                    └─────────────────────────────────┘
```

Daemon polluje `GET /api/v1/issues` a `GET /api/status_check` na Sentinel serveru každých 30 sekund. Podle kategorie incidentu nastavuje barvu LED, výraz očí, tón buzeru a chování motorku.

---

## Instalace

### 1. Raspberry Pi OS

Nainstalujte **Raspberry Pi OS Lite 64-bit** pomocí Raspberry Pi Imager. V pokročilém nastavení zadejte SSH, Wi-Fi a uživatele (`pi`).

### 2. Klonování a instalace

```bash
git clone <repozitář> /home/pi/sentinel-hw
cd /home/pi/sentinel-hw
chmod +x install.sh
./install.sh
```

Skript provede:
- Instalaci systémových balíčků (`python3-venv`, `i2c-tools`, `espeak-ng`, fonts, …)
- Povolení SPI a I2C přes `raspi-config`
- Vytvoření Python virtualenv v `./venv/`
- Instalaci všech Python závislostí z `requirements.txt`

### 3. Konfigurace

```bash
nano config.yaml
```

Nastavte URL a API klíč Sentinel chat_service, zapněte/vypněte hardwarové komponenty a zkontrolujte GPIO piny (musí odpovídat fyzickému zapojení).

### 4. Spuštění

```bash
venv/bin/python sentinel.py
```

### 5. Systemd služba (automatické spuštění)

```bash
sudo cp systemd/sentinel.service /etc/systemd/system/sentinel-hw.service
sudo systemctl daemon-reload
sudo systemctl enable --now sentinel-hw

# Log:
journalctl -u sentinel-hw -f
```

---

## Konfigurace

Celá konfigurace je v `config.yaml`.

```yaml
device:
  name: "Sentinel HW #1"

web_ui:
  enabled: true
  port: 5055
  username: admin
  password: sentinel          # Změňte před nasazením!

sentinel_api:
  enabled: true
  url: "http://192.168.1.10:5050"
  api_key: "<your-agent-token>"
  interval: 30

hardware:
  display:
    enabled: true
    eye_type: oval            # oval nebo round
    cs_pin: 8
    dc_pin: 24
    reset_pin: 25
    backlight_pin: 22

  leds:
    enabled: true
    pin: 18                   # GPIO 18 bez TTS; GPIO 12 s TTS
    count: 8
    brightness: 0.3
    individual:
      0: {enabled: true, react_to: [security, root, agent, infra, ok], link_to: null}

  buzzer:  {enabled: true, pin: 13}
  motor:   {enabled: true, pin: 26}
  touch:   {enabled: true, pin: 16}
  radar:   {enabled: true, pin: 27, presence_timeout: 60}
  light_sensor: {enabled: true, i2c_bus: 1}
  tts:     {enabled: false, engine: espeak, espeak_voice: cs}

behavior:
  idle_dim: true
  auto_brightness: true
  alert_on_critical: true
  announce_status: false
```

---

## Web UI

Webové rozhraní pro konfiguraci a monitoring je dostupné na `http://<ip>:5055`.

**Přihlášení:** username a heslo z `config.yaml → web_ui`

| Záložka | Obsah |
|---|---|
| Přehled | Live stav (status badge, připojení, světlo, přítomnost, incidenty) |
| LEDs | Individuální konfigurace každé LED — enabled, react_to, link_to |
| Senzory | Zapnutí/vypnutí komponentů, nastavení pinů, validace kolizí |
| Oči | Typ očí (oval/round), styl výrazu |
| Chování | DND časovač, auto_brightness, idle_dim, TTS announce |
| Připojení | URL a API klíč chat_service, jméno zařízení, heslo Web UI |
| Logy | Ring-buffer posledních 500 log záznamů, live refresh |
| Testy | Testovací tlačítka pro každý komponent + self-test s výsledky |

### API endpointy Web UI

| Endpoint | Metoda | Popis |
|---|---|---|
| `/api/config` | GET | Celá konfigurace jako JSON |
| `/api/config` | POST | Částečný patch (deep merge) |
| `/api/live` | GET | Live data — stav, senzory, incidenty |
| `/api/logs` | GET | Posledních N log záznamů |
| `/api/export` | GET | Stažení config.yaml |
| `/api/pins/validate` | GET | Validace GPIO pinů — kolize, rozsahy |
| `/api/test/<component>` | POST | Otestování komponentu (led / buzzer / …) |

---

## Kategorie incidentů a chování

| Kategorie | Barva LED | Oči | Buzzer | Podmínka |
|---|---|---|---|---|
| `security` | Červená, rychle | Hněvivé, červené | Agresivní alarm | `channel_type == security` |
| `root` | Oranžovočervená | Přimhouřené | Střední alarm | `channel_type == root` |
| `agent` | Oranžová, střední | Znepokojené | Obecný alert | key začíná `AGENT|` nebo `agent` |
| `infra` | Žlutá, pomalu | Přimhouřené | Obecný alert | ostatní |
| `ok` | Zelená, klidně | Normální, zelené | — | žádné incidenty |
| `idle` | Velmi tlumená | Tmavě modré | — | žádná přítomnost N sekund |
| `boot` | Barevná animace | Modré, normální | Melodie (3 tóny) | startovací sekvence |

### Průběh při novém incidentu

1. SentinelAPI detekuje nový klíč (dosud neviděný v `/api/v1/issues`)
2. Fullscreen notifikace na displeji — kategorie, host, popis (10 s, dotyk zavře)
3. LED bliknutí v barvě kategorie (4×)
4. Buzzer — zvuk odpovídající závažnosti
5. Vibrační motorek (0,5 s)
6. Volitelně TTS: *„Nový incident: security na webserver-01"*

---

## Konfigurace LED

Každá LED (0–7) je konfigurovatelná samostatně v `config.yaml` nebo přes Web UI.

```yaml
leds:
  individual:
    0: {enabled: true, react_to: [security, root], link_to: null}
    1: {enabled: true, react_to: [security, root, agent], link_to: null}
    2: {enabled: false, react_to: [], link_to: null}    # vypnutá
    3: {enabled: true, react_to: [], link_to: 0}        # kopíruje LED 0
```

**`react_to`** — seznam stavů/kategorií, na které tato LED reaguje.  
Dostupné hodnoty: `security`, `root`, `agent`, `infra`, `ok`, `idle`, `boot`.  
Prázdný seznam = LED zůstane černá.

**`link_to`** — číslo jiné LED (0–7), jejíž výslednou barvu kopírovat. LED s `link_to` ignoruje vlastní `react_to`. Vhodné pro symetrické vzory nebo skupiny.

---

## Ovládání dotykem

Poklepání na TTP223 senzor (temeno robota) přepíná režim displeje:

| Režim | Zobrazení |
|---|---|
| 0 | Oči — výraz dle nejzávažnější kategorie (výchozí) |
| 1 | Incidenty — seznam s barevnými kategoriemi (SEC / ROOT / AGT / INFRA) |
| 2 | Metriky — CPU, RAM, disk ze Sentinel chat_service |
| 3 | Info — IP adresa, okolní světlo (lux), stav přítomnosti |

Při aktivní notifikaci (nový incident): dotyk notifikaci zavře a přejde do režimu 1.

---

## Hlasová syntéza (TTS)

> **Důležité:** TTS vyžaduje MAX98357A I2S modul. GPIO 18 je obsazeno I2S BCLK  
> → NeoPixel musí být přesunut z GPIO 18 na **GPIO 12**. Uprav `leds.pin` v konfiguraci.

### espeak-ng (jednodušší, robotický hlas)

```bash
sudo apt-get install -y espeak-ng
```

```yaml
tts:
  enabled: true
  engine: espeak
  espeak_voice: cs
  rate: 140
```

### Piper (přirozený hlas — doporučeno)

```bash
venv/bin/pip install piper-tts
sudo mkdir -p /usr/share/piper
# Stáhnout model z https://huggingface.co/rhasspy/piper-voices
# Doporučený CZ model: cs_CZ-jirka-medium (.onnx + .onnx.json)
sudo mv cs_CZ-jirka-medium.onnx cs_CZ-jirka-medium.onnx.json /usr/share/piper/
```

```yaml
tts:
  enabled: true
  engine: piper
  piper_model: /usr/share/piper/cs_CZ-jirka-medium.onnx
```

### Aktivace I2S v OS

`/boot/firmware/config.txt` (Bookworm) nebo `/boot/config.txt`:

```
dtparam=i2s=on
dtoverlay=hifiberry-dac
```

Test po restartu: `speaker-test -c 2 -t wav`

---

## Testování bez hardware (simulace)

```bash
# Spuštění simulace + mock chat_service
python tests/run_local.py --mock-api
# Web UI: http://localhost:5055  (admin / sentinel)
# Mock API: http://localhost:5000

# Vložení testovacích scénářů:
curl -X POST http://localhost:5000/inject \
  -H "Content-Type: application/json" \
  -d '{"scenario": "security"}'
# scénáře: security | multi | ok | clear
```

### Automatizované testy

```bash
python -m pytest tests/ -v
```

| Soubor | Co testuje | Testů |
|---|---|---|
| `tests/test_leds.py` | LED set_status, set_status_individual, link_to | 10 |
| `tests/test_sentinel_api.py` | Kategorizace incidentů, polling, callback, stav | 18 |
| `tests/test_web_ui.py` | Flask endpointy, auth, pin validace, export | 18 |

---

## Registrace v Sentinelu

Ve Sentinel Web UI (`:5050`) v sekci **Sentinel Satellites → HW Devices**:

1. Zadejte hostname (automaticky dostane prefix `sentinel-hw-`)
2. Zadejte URL tohoto Web UI (např. `http://192.168.1.99:5055`)
3. Klikněte **Registrovat** → zobrazí se vygenerovaný API token

Po registraci lze kliknout na řádek zařízení v Sentinel UI a otevře se detail modal s live incidenty a HW daty (stav senzorů, lux, přítomnost).

---

## Struktura projektu

```text
sentinel-hw/
├── config.yaml
├── sentinel.py          — hlavní aplikace (hlavní smyčka)
├── web_ui.py            — Flask Web UI (port 5055)
├── chat_service.py      — lokální referenční kopie chat_service
├── requirements.txt
├── install.sh
├── README.md
├── WIRING.md            — schémata zapojení GPIO
├── systemd/
│   └── sentinel.service
├── drivers/
│   ├── display.py       — ST7789 + Pillow (oči, server list, info)
│   ├── leds.py          — WS2812B NeoPixel + individual config
│   ├── buzzer.py        — KY-006 (PWM tóny)
│   ├── motor.py         — vibrační motorek
│   ├── touch.py         — TTP223 (interrupt)
│   ├── radar.py         — RCWL-0516
│   ├── light.py         — BH1750 (I2C)
│   ├── tts.py           — espeak-ng / piper
│   ├── monitor.py       — HTTP a ping kontroly
│   └── sentinel_api.py  — polling klient pro chat_service
├── templates/
│   ├── login.html
│   └── index.html       — 8-záložkové SPA
├── static/
│   ├── style.css
│   └── script.js
└── tests/
    ├── mock_hardware.py
    ├── mock_chat_service.py
    ├── run_local.py
    ├── test_leds.py
    ├── test_sentinel_api.py
    └── test_web_ui.py
```
