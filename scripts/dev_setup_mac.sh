#!/bin/bash
# Legacy Tape — Mac Development Setup
# Sets up the Python backend and React UI for local testing
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Legacy Tape — Mac Dev Setup ==="
echo ""

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "python3 required. Install via: brew install python"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "node required. Install via: brew install node"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm required. Install via: brew install node"; exit 1; }

# Portaudio (needed by sounddevice for mic access)
if ! brew list portaudio &>/dev/null 2>&1; then
    echo "Installing portaudio..."
    brew install portaudio
fi

# Data directories
mkdir -p ~/.legacy-tape/recordings
mkdir -p ~/.legacy-tape/models

# Python virtual environment
echo ""
echo "--- Python backend ---"
cd "$PROJECT_DIR/device"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "Python deps installed"

# React UI
echo ""
echo "--- React UI ---"
cd "$PROJECT_DIR/ui"
npm install
npm run build
echo "UI built to ui/dist/"

# Optional: whisper.cpp for real transcription on Mac
echo ""
echo "--- whisper.cpp (optional) ---"
if command -v whisper-cli >/dev/null 2>&1 || [ -f "$HOME/.legacy-tape/whisper.cpp/build/bin/whisper-cli" ]; then
    echo "whisper.cpp already available"
else
    echo "whisper.cpp not found. The mock transcriber will be used."
    echo ""
    echo "To install whisper.cpp for real local transcription:"
    echo "  cd ~/.legacy-tape"
    echo "  git clone https://github.com/ggerganov/whisper.cpp"
    echo "  cd whisper.cpp && cmake -B build && cmake --build build --config Release"
    echo "  bash models/download-ggml-model.sh base.en"
    echo ""
    echo "Then set in your env or .env file:"
    echo "  export LT_WHISPER_BACKEND=whisper_cpp"
    echo "  export LT_WHISPER_MODEL_PATH=~/.legacy-tape/whisper.cpp/models/ggml-base.en.bin"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the dev server:"
echo "  cd $PROJECT_DIR/device"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""
echo "Then open http://localhost:8000 in your browser"
echo ""
echo "For hot-reloading UI development:"
echo "  cd $PROJECT_DIR/ui"
echo "  npm run dev          # runs on :3000, proxies API to :8000"
echo ""
echo "Transcription mode: mock (set LT_WHISPER_BACKEND=whisper_cpp for real)"
