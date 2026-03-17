#!/bin/bash
# Legacy Tape — Start the device orchestrator + UI
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEVICE_DIR="$PROJECT_DIR/device"
LOG_DIR="$HOME/.legacy-tape/logs"

mkdir -p "$LOG_DIR"

echo "=== Legacy Tape — Starting ==="

# Activate venv
source "$DEVICE_DIR/.venv/bin/activate" 2>/dev/null || true

# Start orchestrator
cd "$DEVICE_DIR"
echo "Starting orchestrator on port 8000..."
python main.py 2>&1 | tee "$LOG_DIR/orchestrator.log" &
ORCH_PID=$!

echo "Orchestrator PID: $ORCH_PID"
echo "$ORCH_PID" > "$LOG_DIR/orchestrator.pid"
echo ""
echo "Legacy Tape running at http://localhost:8000"
echo "Press Ctrl+C to stop"

wait $ORCH_PID
