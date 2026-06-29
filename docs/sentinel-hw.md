# Sentinel HW — Physical Monitoring Robot

**Platform:** Raspberry Pi Zero 2 W  
**Python:** 3.13+

Sentinel HW is a **physical ambient monitoring companion** for your server cluster. It transforms raw infrastructure state into visible, audible, and tactile signals — without screens, keyboards, or dashboards.

When everything is fine, its eyes glow calmly green. When a security incident fires, they turn angry red and the buzzer screams. When no one is present in the room, it dims itself to a near-invisible standby glow. It is always on, always watching, always honest about the state of your infrastructure.

Built on a Raspberry Pi Zero 2 W, it polls the Sentinel API every 30 seconds and reflects the current incident severity through: animated ST7789 display (eyes), 8-LED NeoPixel ring (colour + pattern), KY-006 buzzer (tones), vibration motor (haptic pulse), and optionally a Piper TTS voice synthesiser.

---

## Hardware Components

| Component | Model / Spec | Note |
|---|---|---|
| Microcomputer | Raspberry Pi Zero 2 W | MicroSD 16 GB+, 5 V / 2.5 A PSU |
| Display | 2.0" IPS SPI ST7789, 320×240 | Version with exposed CS pin required |
| LED ring | 8× WS2812B NeoPixel (circular module) | 5 V power |
| Buzzer | KY-006 passive | PWM on GPIO 13 |
| Vibration motor | ERM vibration module | GPIO 26 |
| Touch sensor | TTP223 capacitive | Mounted under the top wall |
| Motion radar | RCWL-0516 microwave | Works through plastic |
| Light sensor | BH1750 I2C | Auto-brightness |

### Optional — Voice synthesis (TTS)

| Component | Model | Approx. price |
|---|---|---|
| I2S DAC + amplifier | MAX98357A breakout | ~$5 |
| Speaker | 4 Ω / 2–3 W / 40–50 mm | ~$4 |

Wiring details: see [WIRING.md](https://git.example.com/lukas/sentinel-hw/src/branch/main/WIRING.md).

---

## Architecture

```text
                    ┌─────────────────────────────────┐
                    │         Sentinel HW (RPi)        │
                    │                                  │
  ┌───────────────┐ │  sentinel.py  ←  SentinelAPI     │
  │ chat_service  │ │      ↓           (30 s polling)  │
  │  :5050        │◄──── REST API  ─────────────────── │
  │  /api/v1/     │ │                                  │
  │  issues       │ │  web_ui.py (Flask :5055)         │
  └───────────────┘ │      ↑                           │
                    │  config.yaml                     │
                    │                                  │
                    │  Hardware drivers:               │
                    │  display / leds / buzzer         │
                    │  motor / touch / radar           │
                    │  light / tts / monitor           │
                    └─────────────────────────────────┘
```

The daemon polls `GET /api/v1/issues` and `GET /api/status_check` on the Sentinel server every 30 seconds. Based on the incident category, it sets the LED colour, display expression, buzzer tone, and motor behaviour.

---

## Installation

### 1. Raspberry Pi OS

Install **Raspberry Pi OS Lite 64-bit** via Raspberry Pi Imager. Set SSH, Wi-Fi, and user (`pi`) in the advanced options.

### 2. Clone and install

```bash
git clone <repository> /home/pi/sentinel-hw
cd /home/pi/sentinel-hw
chmod +x install.sh
./install.sh
```

The script:
- Installs system packages (`python3-venv`, `i2c-tools`, `espeak-ng`, fonts, …)
- Enables SPI and I2C via `raspi-config`
- Creates a Python virtualenv in `./venv/`
- Installs all Python dependencies from `requirements.txt`

### 3. Configure

```bash
nano config.yaml
```

Set the Sentinel chat_service URL and API key, enable/disable hardware components, check GPIO pin assignments (must match physical wiring).

### 4. Run

```bash
venv/bin/python sentinel.py
```

### 5. Systemd service (auto-start)

```bash
sudo cp systemd/sentinel.service /etc/systemd/system/sentinel-hw.service
sudo systemctl daemon-reload
sudo systemctl enable --now sentinel-hw

# Logs:
journalctl -u sentinel-hw -f
```

---

## Configuration

All configuration is in `config.yaml`.

```yaml
device:
  name: "Sentinel HW #1"

web_ui:
  enabled: true
  port: 5055
  username: admin
  password: sentinel          # Change before deploying!

sentinel_api:
  enabled: true
  url: "http://192.168.1.10:5050"
  api_key: "<your-agent-token>"
  interval: 30

hardware:
  display:
    enabled: true
    eye_type: oval            # oval or round
    cs_pin: 8
    dc_pin: 24
    reset_pin: 25
    backlight_pin: 22

  leds:
    enabled: true
    pin: 18                   # GPIO 18 without TTS; GPIO 12 with TTS
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

The web interface for configuration and monitoring is available at `http://<ip>:5055`.

**Login:** username and password from `config.yaml → web_ui`

| Tab | Content |
|---|---|
| Overview | Live status (status badge, connection, light, presence, incidents) |
| LEDs | Individual LED configuration — enabled, react_to, link_to |
| Sensors | Enable/disable components, set GPIO pins, collision validation |
| Eyes | Eye type (oval/round), expression style |
| Behaviour | DND timer, auto_brightness, idle_dim, TTS announce |
| Connection | chat_service URL and API key, device name, Web UI password |
| Logs | Ring-buffer of last 500 log entries, live refresh |
| Tests | Test buttons for each component + self-test with results |

### Web UI API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/config` | GET | Full configuration as JSON |
| `/api/config` | POST | Partial patch (deep merge) |
| `/api/live` | GET | Live data — status, sensors, incidents |
| `/api/logs` | GET | Last N log entries |
| `/api/export` | GET | Download config.yaml |
| `/api/pins/validate` | GET | GPIO pin validation — collisions, ranges |
| `/api/test/<component>` | POST | Component test (led / buzzer / …) |

---

## Incident categories and behaviour

| Category | LED colour | Eyes | Buzzer | Condition |
|---|---|---|---|---|
| `security` | Red, fast blink | Angry, red | Aggressive alarm | `channel_type == security` |
| `root` | Orange-red | Squinted | Medium alarm | `channel_type == root` |
| `agent` | Orange, medium | Worried | General alert | key starts with `AGENT|` or `agent` |
| `infra` | Yellow, slow | Squinted | General alert | other |
| `ok` | Green, calm | Normal, green | — | no incidents |
| `idle` | Very dim | Dark blue | — | no presence for N seconds |
| `boot` | Colour animation | Blue, normal | Melody (3 tones) | startup sequence |

### New incident flow

1. SentinelAPI detects a new key (not seen before in `/api/v1/issues`)
2. Fullscreen notification on the display — category, host, description (10 s, touch closes)
3. LED blink in the category colour (4×)
4. Buzzer sound matching the severity
5. Vibration motor (0.5 s)
6. Optional TTS: *"New incident: security on webserver-01"*

---

## LED configuration

Each LED (0–7) is individually configurable in `config.yaml` or via the Web UI.

```yaml
leds:
  individual:
    0: {enabled: true, react_to: [security, root], link_to: null}
    1: {enabled: true, react_to: [security, root, agent], link_to: null}
    2: {enabled: false, react_to: [], link_to: null}   # disabled
    3: {enabled: true, react_to: [], link_to: 0}       # mirrors LED 0
```

**`react_to`** — list of states/categories this LED reacts to.  
Available values: `security`, `root`, `agent`, `infra`, `ok`, `idle`, `boot`.  
Empty list = LED stays off.

**`link_to`** — index of another LED (0–7) to mirror. A linked LED ignores its own `react_to` and copies the target LED's colour. Useful for symmetric patterns or LED groups.

---

## Touch control

Tapping the TTP223 sensor (top of the robot) cycles the display mode:

| Mode | Display content |
|---|---|
| 0 | Eyes — expression based on the most critical category (default) |
| 1 | Incidents — list with colour-coded categories (SEC / ROOT / AGT / INFRA) |
| 2 | Metrics — CPU, RAM, disk from Sentinel chat_service |
| 3 | Info — IP address, ambient light (lux), presence state |

When a notification is active (new incident): touch closes the notification and switches to mode 1.

---

## Voice synthesis (TTS)

> **Important:** TTS requires a MAX98357A I2S module. GPIO 18 is occupied by I2S BCLK  
> → NeoPixel must be moved from GPIO 18 to **GPIO 12**. Adjust `leds.pin` in the configuration.

### espeak-ng (simpler, robotic voice)

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

### Piper (natural voice — recommended)

```bash
venv/bin/pip install piper-tts
sudo mkdir -p /usr/share/piper
# Download model from https://huggingface.co/rhasspy/piper-voices
# Recommended CZ model: cs_CZ-jirka-medium (.onnx + .onnx.json)
sudo mv cs_CZ-jirka-medium.onnx cs_CZ-jirka-medium.onnx.json /usr/share/piper/
```

```yaml
tts:
  enabled: true
  engine: piper
  piper_model: /usr/share/piper/cs_CZ-jirka-medium.onnx
```

### Enable I2S in the OS

`/boot/firmware/config.txt` (Bookworm) or `/boot/config.txt`:

```
dtparam=i2s=on
dtoverlay=hifiberry-dac
```

Test after reboot: `speaker-test -c 2 -t wav`

---

## Testing without hardware (simulation)

```bash
# Start simulation + mock chat_service
python tests/run_local.py --mock-api
# Web UI: http://localhost:5055  (admin / sentinel)
# Mock API: http://localhost:5000

# Inject test scenarios:
curl -X POST http://localhost:5000/inject \
  -H "Content-Type: application/json" \
  -d '{"scenario": "security"}'
# scenarios: security | multi | ok | clear
```

### Automated tests

```bash
python -m pytest tests/ -v
```

| Test file | What it tests | Tests |
|---|---|---|
| `tests/test_leds.py` | LED set_status, set_status_individual, link_to | 10 |
| `tests/test_sentinel_api.py` | Incident categorisation, polling, callback, state | 18 |
| `tests/test_web_ui.py` | Flask endpoints, auth, pin validation, export | 18 |

---

## Registering in Sentinel

In the Sentinel Web UI (`:5050`) under **Sentinel Satellites → HW Devices**:

1. Enter the hostname (automatically prefixed with `sentinel-hw-`)
2. Enter the URL of this Web UI (e.g. `http://192.168.1.99:5055`)
3. Click **Register** → a generated API token is displayed

After registration, clicking the device row in Sentinel UI opens a live incident and HW data modal (sensor state, lux, presence).

---

## Project structure

```text
sentinel-hw/
├── config.yaml
├── sentinel.py          — main application (main loop)
├── web_ui.py            — Flask Web UI (port 5055)
├── chat_service.py      — local reference copy of chat_service
├── requirements.txt
├── install.sh
├── README.md
├── WIRING.md            — GPIO wiring diagrams
├── systemd/
│   └── sentinel.service
├── drivers/
│   ├── display.py       — ST7789 + Pillow (eyes, server list, info)
│   ├── leds.py          — WS2812B NeoPixel + individual config
│   ├── buzzer.py        — KY-006 (PWM tones)
│   ├── motor.py         — vibration motor
│   ├── touch.py         — TTP223 (interrupt)
│   ├── radar.py         — RCWL-0516
│   ├── light.py         — BH1750 (I2C)
│   ├── tts.py           — espeak-ng / piper
│   ├── monitor.py       — HTTP and ping checks
│   └── sentinel_api.py  — polling client for chat_service
├── templates/
│   ├── login.html
│   └── index.html       — 8-tab SPA
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
