"""Serial bridge to Raspberry Pi Pico 2 for physical transport controls.

Protocol: Pico sends single-line JSON commands over USB serial.
  {"btn": "record"}
  {"btn": "play"}
  {"btn": "stop"}
  {"btn": "pause"}
  {"btn": "rewind"}
  {"btn": "ffwd"}
  {"btn": "mode", "value": "clean"|"ai_interview"|"ghost_writer"}

Device responds with state updates:
  {"state": "recording", "elapsed": 45.2, "chapter": 3}
  {"state": "idle"}
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable, Dict, List, Optional

from loguru import logger

from config import settings

_callbacks: Dict[str, List[Callable]] = {}


def on_button(button: str, callback: Callable) -> None:
    """Register a callback for a button press event."""
    _callbacks.setdefault(button, []).append(callback)


async def _dispatch(button: str, value: Optional[str] = None) -> None:
    for cb in _callbacks.get(button, []):
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(value) if value else await cb()
            else:
                cb(value) if value else cb()
        except Exception as e:
            logger.error(f"Button callback error ({button}): {e}")


async def start_pico_listener() -> None:
    """Listen for button events from Pico 2 over serial."""
    try:
        import serial_asyncio

        reader, writer = await serial_asyncio.open_serial_connection(
            url=settings.pico_port,
            baudrate=settings.pico_baud,
        )
        logger.info(f"Pico 2 connected on {settings.pico_port}")

        while True:
            line = await reader.readline()
            try:
                data = json.loads(line.decode().strip())
                btn = data.get("btn")
                value = data.get("value")
                if btn:
                    logger.debug(f"Pico button: {btn} (value={value})")
                    await _dispatch(btn, value)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Pico parse error: {e}")

    except Exception as e:
        logger.warning(f"Pico 2 not connected ({e}), running in software-only mode")


async def send_state(state: dict) -> None:
    """Send state update back to Pico 2 for LED/display feedback.

    In software-only mode this is a no-op.
    """
    logger.debug(f"State → Pico: {state}")
