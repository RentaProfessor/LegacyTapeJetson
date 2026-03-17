#!/bin/bash
# Legacy Tape — Toggle kiosk mode on/off
# Usage: ./toggle_kiosk.sh on    (enable kiosk + backend autostart)
#        ./toggle_kiosk.sh off   (disable kiosk, normal desktop on next boot)
#        ./toggle_kiosk.sh status

AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/legacy-tape-kiosk.desktop"
SERVICE_NAME="legacy-tape"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DESKTOP="$SCRIPT_DIR/legacy-tape-kiosk.desktop"

case "${1:-status}" in
    on)
        echo "=== Enabling kiosk mode ==="

        # Enable backend systemd service
        sudo systemctl enable "$SERVICE_NAME" 2>/dev/null
        sudo systemctl start "$SERVICE_NAME" 2>/dev/null
        echo "[+] Backend service enabled"

        # Install autostart .desktop file
        mkdir -p "$AUTOSTART_DIR"
        cp "$SOURCE_DESKTOP" "$DESKTOP_FILE"
        echo "[+] Kiosk autostart installed"

        echo ""
        echo "Kiosk mode ON. Reboot to launch fullscreen automatically."
        echo "  sudo reboot"
        ;;

    off)
        echo "=== Disabling kiosk mode ==="

        # Disable backend systemd service (stop it too)
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null
        echo "[-] Backend service disabled"

        # Remove autostart .desktop file
        rm -f "$DESKTOP_FILE"
        echo "[-] Kiosk autostart removed"

        # Kill any running kiosk Firefox
        pkill -f "firefox.*--kiosk" 2>/dev/null && echo "[-] Killed kiosk Firefox" || true

        echo ""
        echo "Kiosk mode OFF. Next boot will show normal desktop."
        echo "  sudo reboot"
        ;;

    status)
        echo "=== Kiosk Status ==="
        if [ -f "$DESKTOP_FILE" ]; then
            echo "  Autostart:  ENABLED"
        else
            echo "  Autostart:  disabled"
        fi
        if systemctl is-enabled "$SERVICE_NAME" > /dev/null 2>&1; then
            echo "  Service:    ENABLED"
        else
            echo "  Service:    disabled"
        fi
        if systemctl is-active "$SERVICE_NAME" > /dev/null 2>&1; then
            echo "  Backend:    RUNNING"
        else
            echo "  Backend:    stopped"
        fi
        if pgrep -f "firefox.*--kiosk" > /dev/null 2>&1; then
            echo "  Firefox:    RUNNING (kiosk)"
        else
            echo "  Firefox:    not running"
        fi
        ;;

    *)
        echo "Usage: $0 {on|off|status}"
        exit 1
        ;;
esac
