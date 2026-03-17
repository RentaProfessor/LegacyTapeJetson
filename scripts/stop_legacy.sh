#!/bin/bash
# Legacy Tape — Stop all services
LOG_DIR="$HOME/.legacy-tape/logs"

echo "=== Stopping Legacy Tape ==="

if [ -f "$LOG_DIR/orchestrator.pid" ]; then
    PID=$(cat "$LOG_DIR/orchestrator.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Stopped orchestrator (PID $PID)"
    fi
    rm -f "$LOG_DIR/orchestrator.pid"
else
    pkill -f "python main.py" 2>/dev/null && echo "Stopped orchestrator" || echo "Orchestrator not running"
fi

echo "Done"
