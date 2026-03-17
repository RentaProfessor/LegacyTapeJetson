#!/bin/bash
# Legacy Tape — Kiosk launcher
# Waits for the backend, disables screen blanking, launches Firefox fullscreen.
# Called by the XDG autostart .desktop file at login.

BACKEND_URL="http://localhost:8000"
MAX_WAIT=60

# -----------------------------------------------------------------------
# Wait for the FastAPI backend to come up
# -----------------------------------------------------------------------
echo "[kiosk] Waiting for backend at $BACKEND_URL ..."
elapsed=0
while ! curl -sf "$BACKEND_URL" > /dev/null 2>&1; do
    sleep 2
    elapsed=$((elapsed + 2))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "[kiosk] Backend not ready after ${MAX_WAIT}s — launching anyway"
        break
    fi
done
echo "[kiosk] Backend ready (${elapsed}s)"

# -----------------------------------------------------------------------
# Disable screen blanking, screensaver, and power management
# -----------------------------------------------------------------------
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null

gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null
gsettings set org.gnome.settings-daemon.plugins.power idle-dim false 2>/dev/null
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' 2>/dev/null
gsettings set org.gnome.desktop.screensaver lock-enabled false 2>/dev/null
gsettings set org.gnome.desktop.notifications show-banners false 2>/dev/null

# -----------------------------------------------------------------------
# Hide mouse cursor (if unclutter is installed)
# -----------------------------------------------------------------------
if command -v unclutter > /dev/null 2>&1; then
    unclutter -idle 0.5 -root &
fi

# -----------------------------------------------------------------------
# Launch Firefox in kiosk mode with auto-restart
# -----------------------------------------------------------------------
echo "[kiosk] Starting Firefox kiosk → $BACKEND_URL"

while true; do
    firefox --kiosk "$BACKEND_URL" 2>/dev/null
    EXIT_CODE=$?
    echo "[kiosk] Firefox exited ($EXIT_CODE) — restarting in 2s"
    sleep 2
done
