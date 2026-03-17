# Legacy Tape

A Jetson Orin Nano–based embedded storytelling device housed in a cassette-recorder enclosure.
Captures spoken memories from older users through a zero-friction analog-style interface,
transcribes locally, organizes into structured memoir chapters, and syncs to a companion app
for family access and book-generation workflows.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  LEGACY TAPE DEVICE                  │
│                                                      │
│  ┌──────────┐    Serial/USB    ┌──────────────────┐ │
│  │ Pico 2   │◄───────────────►│  Jetson Orin Nano │ │
│  │ (buttons)│                  │                    │ │
│  └──────────┘                  │  ┌──────────────┐ │ │
│                                │  │  Orchestrator │ │ │
│  ┌──────────────┐              │  │  (FastAPI)    │ │ │
│  │ 5" LCD Touch │◄────────────│  │               │ │ │
│  │ (Cassette UI)│  localhost   │  │  Recorder     │ │ │
│  └──────────────┘              │  │  Transcriber  │ │ │
│                                │  │  Memoir Engine│ │ │
│  ┌──────────────┐              │  │  Storage      │ │ │
│  │ Microphone   │─────────────│  │  Sync Client  │ │ │
│  └──────────────┘              │  └──────────────┘ │ │
│                                └──────────────────┘ │
└──────────────┬──────────────────────────────────────┘
               │ HTTPS (text only)
               ▼
┌──────────────────────┐     ┌─────────────────────┐
│   Cloud Sync API     │◄───►│   Companion App     │
│   (memoir text,      │     │   (family access,   │
│    chapter metadata)  │     │    book generation) │
└──────────────────────┘     └─────────────────────┘
```

## Components

| Directory | Description |
|-----------|-------------|
| `device/` | Jetson Orin Nano orchestrator — FastAPI backend handling recording, local transcription (Whisper), memoir structuring, Pico 2 communication, and cloud sync |
| `pico/` | Raspberry Pi Pico 2 firmware (MicroPython) — debounces physical transport buttons, sends commands over serial |
| `ui/` | 5" LCD touchscreen interface (React + Vite) — cassette animations, recording state, chapter display, served by the orchestrator |
| `api/` | Cloud sync API — receives organized memoir text from device, serves companion app |
| `companion-app/` | Mobile companion app — family library, chapter browsing, editing, book generation |
| `scripts/` | Setup and launch scripts for Jetson deployment |

## Recording Modes

- **CLEAN** — Straight recording with minimal processing, raw transcript
- **AI INTERVIEW** — Guided prompts that ask follow-up questions to draw out stories
- **GHOST WRITER** — AI restructures rambling speech into polished prose chapters

## Data Flow

```
Speech → Microphone → WAV capture (local storage)
  → Whisper (local, on Jetson GPU) → transcript
  → Memoir Engine (chapter segmentation, mode processing)
  → Local SQLite (recordings + transcripts + chapters)
  → Sync Client → Cloud API (text + metadata only, no audio)
  → Companion App (family reads, edits, generates books)
```

## Hardware

- **Compute**: NVIDIA Jetson Orin Nano (8GB) — runs Whisper, memoir engine
- **Controls**: Raspberry Pi Pico 2 — interfaces 6 transport buttons + mode switch
- **Display**: 5" IPS LCD touchscreen (800×480) — HDMI or DSI
- **Audio In**: Electret condenser mic or USB mic
- **Audio Out**: Built-in speaker + 3.5mm jack
- **Connectivity**: WiFi (sync), Bluetooth (optional)
- **Power**: 5V/4A barrel jack

## Quick Start (Dev on Mac)

```bash
# 1. Backend
cd device/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py                     # runs on http://localhost:8000

# 2. UI (dev with hot reload)
cd ui/
npm install && npm run dev         # http://localhost:3000 (proxies API to 8000)

# --- OR production mode (single server) ---
cd ui/ && npm run build            # builds to ui/dist/
cd device/ && python main.py       # serves UI + API on http://localhost:8000
```

## Jetson Orin Nano — Full Setup Checklist

### Prerequisites

- Jetson Orin Nano (8GB) with JetPack 6.x flashed to SD card / NVMe
- 5" IPS LCD (800x480) connected via HDMI or DSI
- USB microphone or electret mic with USB sound card
- WiFi configured (for initial setup, git clone, and optional cloud sync)
- Keyboard + mouse connected (for initial mouse-based testing)

### Step 1: Push to GitHub from Mac

```bash
# On your Mac
cd "Desktop/ROOT FILES/LEGACY TAPE"
git init
git add .
git commit -m "Legacy Tape v1 — cassette recorder with transport UI"
git remote add origin https://github.com/YOUR_USER/legacy-tape.git
git push -u origin main
```

### Step 2: Clone on Jetson

```bash
ssh jetson@<JETSON_IP>             # or plug in keyboard/monitor
cd ~
git clone https://github.com/YOUR_USER/legacy-tape.git
cd legacy-tape
```

### Step 3: Run the setup script

```bash
chmod +x scripts/setup_jetson.sh
./scripts/setup_jetson.sh
```

This installs all system packages, builds whisper.cpp with CUDA, downloads the
`base.en` model, creates the Python venv, installs Python deps, and builds the
React UI. Takes ~10-15 min on first run.

**What the script installs:**
- System: `python3-pip`, `python3-venv`, `portaudio19-dev`, `ffmpeg`, `sqlite3`, `nodejs`, `npm`, `cmake`
- Python: `fastapi`, `uvicorn`, `sounddevice`, `soundfile`, `numpy`, `loguru`, `pydantic-settings`, `pyserial`, `httpx`
- whisper.cpp: built from source with `-DWHISPER_CUDA=ON` for GPU acceleration
- Model: `ggml-base.en.bin` (~142 MB)

### Step 4: Verify audio input

```bash
# List audio devices
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Record a 5-second test
arecord -d 5 -f S16_LE -r 16000 /tmp/test.wav && aplay /tmp/test.wav
```

If the USB mic doesn't show up as default, set `LT_AUDIO_DEVICE` in the `.env`
file to the device name or index from the `query_devices()` output.

### Step 5: Start Legacy Tape

```bash
cd ~/legacy-tape
./scripts/start_legacy.sh
```

Open Chromium on the Jetson to `http://localhost:8000`. The full cassette UI
with transport buttons will appear. Use the mouse to click REC, STOP, PLAY,
REW, FF, PAUSE, MODE, and NEW.

### Step 6: Test the full flow with mouse

1. Click **REC** — recording starts, reels spin, status shows RECORDING
2. Speak into the microphone for 10-30 seconds
3. Click **STOP** — status shows PROCESSING while Whisper transcribes
4. Wait for transcription to finish (status returns to READY)
5. Click **REW** to rewind the tape, then **PLAY** to see playback animation
6. Click **MODE** to cycle through CLEAN / AI INTERVIEW / GHOST WRITER
7. Click **NEW** to start a fresh story

### Step 7: Auto-start on boot (optional)

```bash
sudo cp scripts/autostart.service /etc/systemd/system/legacy-tape.service
# Edit the service file if your username isn't 'jetson':
#   sudo nano /etc/systemd/system/legacy-tape.service
sudo systemctl daemon-reload
sudo systemctl enable legacy-tape
sudo systemctl start legacy-tape

# Check status
sudo systemctl status legacy-tape
journalctl -u legacy-tape -f       # live logs
```

### Step 8: Chromium kiosk mode for the 5" LCD (optional)

```bash
# Launch Chromium in kiosk mode (fullscreen, no toolbar)
chromium-browser --kiosk --noerrdialogs --disable-infobars \
  --no-first-run http://localhost:8000 &
```

To auto-launch on boot, add the above to `~/.config/autostart/legacy-tape-ui.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Legacy Tape UI
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:8000
```

### Later: Wire Pico 2 buttons

When ready to add physical buttons:

1. Flash `pico/main.py` onto the Pico 2 via Thonny or `mpremote`
2. Wire 6 buttons (active-low with internal pull-ups) to GP2-GP7
3. Wire 3-position mode switch to GP10-GP12
4. Connect Pico to Jetson via USB — appears as `/dev/ttyACM0`
5. Recording LED on GP15, power LED on GP16
6. The orchestrator auto-detects the Pico serial connection on startup

### Troubleshooting

| Problem | Fix |
|---------|-----|
| No audio input | Check `arecord -l`, set `LT_AUDIO_DEVICE` in `.env` |
| Whisper not found | Run `setup_jetson.sh` again, check `~/.legacy-tape/whisper.cpp/build/bin/whisper-cli` exists |
| Port 8000 in use | `./scripts/stop_legacy.sh` then start again |
| UI blank at localhost:8000 | Run `cd ui && npm run build` to rebuild |
| Pico not detected | Check `ls /dev/ttyACM*`, set `LT_PICO_PORT` if different |
| CUDA out of memory | Use smaller model: set `LT_WHISPER_MODEL_SIZE=tiny.en` |

### Environment Variables (`.env` or export)

| Variable | Default | Description |
|----------|---------|-------------|
| `LT_WHISPER_BACKEND` | `auto` | `whisper_cpp`, `mock`, or `auto` |
| `LT_WHISPER_CPP_BIN` | auto-detected | Path to whisper-cli binary |
| `LT_WHISPER_MODEL_PATH` | auto-detected | Path to ggml model file |
| `LT_WHISPER_MODEL_SIZE` | `base.en` | Model to download if not present |
| `LT_AUDIO_DEVICE` | system default | Sounddevice device name or index |
| `LT_PICO_PORT` | `/dev/ttyACM0` | Pico 2 serial port |
| `LT_SYNC_ENABLED` | `false` | Enable cloud sync |
| `LT_SYNC_API_KEY` | empty | API key for cloud sync |

## Tech Stack

- **Device Backend**: Python 3.10+, FastAPI, whisper.cpp (CUDA), SQLite
- **Device UI**: React 18, Vite, Framer Motion (cassette animations)
- **Pico Firmware**: MicroPython
- **Cloud API**: Python, FastAPI, PostgreSQL
- **Companion App**: React Native (Expo)
