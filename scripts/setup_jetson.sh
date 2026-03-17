#!/bin/bash
# Legacy Tape — Jetson Orin Nano Setup Script
# Run once after flashing JetPack to prepare the device
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Legacy Tape — Jetson Setup ==="

# System packages
sudo apt-get update
sudo apt-get install -y \
    python3-pip python3-venv \
    portaudio19-dev \
    ffmpeg \
    sqlite3 \
    nodejs npm \
    cmake build-essential \
    libcurl4-openssl-dev \
    firefox \
    unclutter \
    curl

# Data directories
mkdir -p ~/.legacy-tape/recordings
mkdir -p ~/.legacy-tape/models

# -----------------------------------------------------------------------
# Build whisper.cpp with CUDA
# -----------------------------------------------------------------------
echo ""
echo "--- Building whisper.cpp with CUDA ---"
WHISPER_DIR="$HOME/.legacy-tape/whisper.cpp"

if [ ! -d "$WHISPER_DIR" ]; then
    git clone https://github.com/ggerganov/whisper.cpp "$WHISPER_DIR"
fi

cd "$WHISPER_DIR"
git pull --ff-only 2>/dev/null || true

cmake -B build -DWHISPER_CUDA=ON
cmake --build build --config Release -j$(nproc)

echo "whisper.cpp built at $WHISPER_DIR/build/bin/whisper-cli"

# Download model if not present
MODEL_FILE="$WHISPER_DIR/models/ggml-base.en.bin"
if [ ! -f "$MODEL_FILE" ]; then
    echo "Downloading ggml-base.en model..."
    bash "$WHISPER_DIR/models/download-ggml-model.sh" base.en
fi

# Copy model to standard location
cp "$MODEL_FILE" "$HOME/.legacy-tape/models/ggml-base.en.bin" 2>/dev/null || true

# -----------------------------------------------------------------------
# Python environment
# -----------------------------------------------------------------------
echo ""
echo "--- Python backend ---"
cd "$PROJECT_DIR/device"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# -----------------------------------------------------------------------
# Build UI
# -----------------------------------------------------------------------
echo ""
echo "--- React UI ---"
cd "$PROJECT_DIR/ui"
npm install
npm run build

# -----------------------------------------------------------------------
# Environment file
# -----------------------------------------------------------------------
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << EOF
LT_WHISPER_BACKEND=whisper_cpp
LT_WHISPER_CPP_BIN=$WHISPER_DIR/build/bin/whisper-cli
LT_WHISPER_MODEL_PATH=$HOME/.legacy-tape/models/ggml-base.en.bin
LT_WHISPER_LANGUAGE=en
EOF
    echo "Created $ENV_FILE"
fi

# -----------------------------------------------------------------------
# Kiosk mode — backend service + Firefox autostart + auto-login
# -----------------------------------------------------------------------
echo ""
echo "--- Kiosk mode setup ---"

CURRENT_USER="$(whoami)"

# Install and enable the systemd service for the backend
SERVICE_SRC="$PROJECT_DIR/scripts/autostart.service"
SERVICE_DST="/etc/systemd/system/legacy-tape.service"

if [ -f "$SERVICE_SRC" ]; then
    sudo cp "$SERVICE_SRC" "$SERVICE_DST"
    sudo sed -i "s|User=.*|User=$CURRENT_USER|" "$SERVICE_DST"
    sudo sed -i "s|/home/brett/|/home/$CURRENT_USER/|g" "$SERVICE_DST"
    sudo sed -i "s|Environment=HOME=.*|Environment=HOME=/home/$CURRENT_USER|" "$SERVICE_DST"
    sudo systemctl daemon-reload
    sudo systemctl enable legacy-tape
    echo "Backend service installed and enabled"
fi

# Make kiosk scripts executable
chmod +x "$PROJECT_DIR/scripts/kiosk.sh" 2>/dev/null
chmod +x "$PROJECT_DIR/scripts/toggle_kiosk.sh" 2>/dev/null

# Install the XDG autostart entry for the kiosk browser
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
DESKTOP_SRC="$PROJECT_DIR/scripts/legacy-tape-kiosk.desktop"
if [ -f "$DESKTOP_SRC" ]; then
    sed "s|/home/brett/|/home/$CURRENT_USER/|g" "$DESKTOP_SRC" > "$AUTOSTART_DIR/legacy-tape-kiosk.desktop"
    echo "Kiosk autostart installed"
fi

# Configure GDM auto-login (skip the login screen on boot)
GDM_CONF="/etc/gdm3/custom.conf"
if [ -f "$GDM_CONF" ]; then
    if ! grep -q "AutomaticLoginEnable" "$GDM_CONF"; then
        sudo sed -i "/^\[daemon\]/a AutomaticLoginEnable=True\nAutomaticLogin=$CURRENT_USER" "$GDM_CONF"
        echo "Auto-login enabled for $CURRENT_USER"
    else
        echo "Auto-login already configured"
    fi
else
    echo "WARNING: $GDM_CONF not found — auto-login not configured"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start manually:  ./scripts/start_legacy.sh"
echo "Kiosk control:   ./scripts/toggle_kiosk.sh on|off|status"
echo "Whisper binary:  $WHISPER_DIR/build/bin/whisper-cli"
echo "Whisper model:   $HOME/.legacy-tape/models/ggml-base.en.bin"
echo ""
echo "Reboot to launch in kiosk mode, or run:"
echo "  ./scripts/toggle_kiosk.sh on && sudo reboot"
