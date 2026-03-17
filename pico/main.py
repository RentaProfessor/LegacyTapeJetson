"""Legacy Tape — Raspberry Pi Pico 2 Firmware (MicroPython)

Reads 6 transport buttons + 1 mode rotary switch, debounces them,
and sends JSON commands over USB serial to the Jetson Orin Nano.

Pin assignments (active-low, internal pull-up):
  GP2  — STOP/EJECT
  GP3  — RECORD
  GP4  — PLAY
  GP5  — REWIND
  GP6  — FAST FORWARD
  GP7  — PAUSE

Mode switch (3-position rotary, active-low):
  GP10 — CLEAN
  GP11 — AI INTERVIEW
  GP12 — GHOST WRITER

Status LEDs:
  GP15 — Recording LED (red)
  GP16 — Power LED (green)
"""

import json
import sys
import time

from machine import Pin


BUTTON_PINS = {
    "stop": 2,
    "record": 3,
    "play": 4,
    "rewind": 5,
    "ffwd": 6,
    "pause": 7,
}

MODE_PINS = {
    "clean": 10,
    "ai_interview": 11,
    "ghost_writer": 12,
}

LED_REC = 15
LED_POWER = 16

DEBOUNCE_MS = 50


class Button:
    def __init__(self, pin_num, name):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.name = name
        self._last_state = 1
        self._last_change = 0

    def check(self):
        """Returns True if a new press is detected (debounced, active-low)."""
        state = self.pin.value()
        now = time.ticks_ms()

        if state != self._last_state and time.ticks_diff(now, self._last_change) > DEBOUNCE_MS:
            self._last_state = state
            self._last_change = now
            return state == 0  # pressed when low
        return False


def send(data):
    """Send a JSON line over USB serial."""
    sys.stdout.write(json.dumps(data) + "\n")


def read_mode(mode_pins):
    """Read which mode position the rotary switch is in."""
    for mode_name, pin in mode_pins.items():
        if pin.value() == 0:
            return mode_name
    return "clean"


def main():
    buttons = {name: Button(pin, name) for name, pin in BUTTON_PINS.items()}

    mode_inputs = {name: Pin(pin, Pin.IN, Pin.PULL_UP) for name, pin in MODE_PINS.items()}

    led_rec = Pin(LED_REC, Pin.OUT)
    led_power = Pin(LED_POWER, Pin.OUT)

    led_power.value(1)
    led_rec.value(0)

    current_mode = read_mode(mode_inputs)
    recording = False

    send({"btn": "mode", "value": current_mode})

    while True:
        for name, button in buttons.items():
            if button.check():
                send({"btn": name})

                if name == "record":
                    recording = True
                    led_rec.value(1)
                elif name == "stop":
                    recording = False
                    led_rec.value(0)
                elif name == "pause":
                    if recording:
                        led_rec.toggle()

        new_mode = read_mode(mode_inputs)
        if new_mode != current_mode:
            current_mode = new_mode
            send({"btn": "mode", "value": current_mode})

        if recording:
            led_rec.toggle()
            time.sleep_ms(500)
        else:
            time.sleep_ms(10)


if __name__ == "__main__":
    main()
