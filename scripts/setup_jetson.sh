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
    libcurl4-openssl-dev

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

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start with: ./scripts/start_legacy.sh"
echo "Whisper binary: $WHISPER_DIR/build/bin/whisper-cli"
echo "Whisper model:  $HOME/.legacy-tape/models/ggml-base.en.bin"
