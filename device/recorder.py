"""Audio recording and playback engine using sounddevice."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger

from config import settings


def find_usb_mic() -> Optional[int]:
    """Auto-detect a USB microphone and return its device index."""
    try:
        devices = sd.query_devices()
    except Exception as e:
        logger.error(f"Failed to query audio devices: {e}")
        return None

    usb_keywords = ["usb", "uac", "c-media", "blue", "samson", "fifine", "boya"]
    candidates = []

    for i, dev in enumerate(devices):
        if dev["max_input_channels"] < 1:
            continue
        name_lower = dev["name"].lower()
        hostapi = sd.query_hostapis(dev["hostapi"])["name"].lower()
        is_usb = any(kw in name_lower for kw in usb_keywords)
        is_external = "built-in" not in name_lower and "hdmi" not in name_lower
        if is_usb:
            candidates.insert(0, (i, dev))
        elif is_external and "default" not in name_lower:
            candidates.append((i, dev))

    if candidates:
        idx, dev = candidates[0]
        logger.info(f"Auto-detected USB mic: [{idx}] {dev['name']}")
        return idx

    return None


def list_audio_devices() -> list:
    """Return a list of audio device info dicts for the API."""
    try:
        devices = sd.query_devices()
    except Exception:
        return []
    result = []
    for i, dev in enumerate(devices):
        result.append({
            "index": i,
            "name": dev["name"],
            "max_input_channels": dev["max_input_channels"],
            "max_output_channels": dev["max_output_channels"],
            "default_samplerate": dev["default_samplerate"],
        })
    return result


class Recorder:
    def __init__(self):
        self._recording = False
        self._paused = False
        self._frames: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._start_time: float = 0
        self._pause_offset: float = 0
        self._pause_start: float = 0

        self._playing = False
        self._play_thread: Optional[threading.Thread] = None
        self._play_stop_flag = threading.Event()
        self._play_position: float = 0.0
        self._play_duration: float = 0.0
        self._on_playback_done: Optional[Callable] = None

        self.last_recording_path: Optional[str] = None
        self._input_device: Optional[int] = None

    def resolve_input_device(self) -> None:
        """Detect and lock in the input device at startup."""
        if settings.audio_device is not None and settings.audio_device != "":
            try:
                self._input_device = int(settings.audio_device)
            except (ValueError, TypeError):
                self._input_device = settings.audio_device
            logger.info(f"Using configured audio device: {self._input_device}")
            return

        usb_idx = find_usb_mic()
        if usb_idx is not None:
            self._input_device = usb_idx
            return

        logger.warning("No USB mic found — using system default input device")
        self._input_device = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def play_position(self) -> float:
        return self._play_position

    @property
    def play_duration(self) -> float:
        return self._play_duration

    @property
    def elapsed_seconds(self) -> float:
        if not self._recording:
            return 0
        if self._paused:
            return self._pause_start - self._start_time - self._pause_offset
        return time.time() - self._start_time - self._pause_offset

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        if self._recording and not self._paused:
            self._frames.append(indata.copy())

    def start(self) -> None:
        if self._recording:
            logger.warning("Already recording")
            return

        if self._playing:
            self.stop_playback()

        self._frames = []
        self._pause_offset = 0
        self._start_time = time.time()
        self._recording = True
        self._paused = False

        try:
            self._stream = sd.InputStream(
                samplerate=settings.sample_rate,
                channels=settings.channels,
                dtype="float32",
                device=self._input_device,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
            dev_name = "default"
            if self._input_device is not None:
                try:
                    dev_name = sd.query_devices(self._input_device)["name"]
                except Exception:
                    dev_name = str(self._input_device)
            logger.info(f"Recording started (device: {dev_name})")
        except Exception as e:
            self._recording = False
            logger.error(f"Failed to start recording: {e}")
            raise

    def pause(self) -> None:
        if not self._recording or self._paused:
            return
        self._paused = True
        self._pause_start = time.time()
        logger.info("Recording paused")

    def resume(self) -> None:
        if not self._recording or not self._paused:
            return
        self._pause_offset += time.time() - self._pause_start
        self._paused = False
        logger.info("Recording resumed")

    def stop(self) -> Optional[Tuple[str, float]]:
        """Stop recording, save WAV file. Returns (file_path, duration_secs) or None."""
        if not self._recording:
            return None

        duration = self.elapsed_seconds

        self._recording = False
        self._paused = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            logger.warning("No audio frames captured")
            return None

        audio = np.concatenate(self._frames, axis=0)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        filepath = str(Path(settings.recordings_dir) / filename)

        sf.write(filepath, audio, settings.sample_rate)
        actual_duration = len(audio) / settings.sample_rate
        logger.info(f"Saved recording: {filepath} ({actual_duration:.1f}s)")

        self._frames = []
        self.last_recording_path = filepath
        return filepath, actual_duration

    def play(self, filepath: Optional[str] = None, on_done: Optional[Callable] = None) -> bool:
        """Play a WAV file. Returns True if playback started."""
        target = filepath or self.last_recording_path
        if not target or not Path(target).exists():
            logger.warning(f"No file to play: {target}")
            return False

        if self._recording:
            logger.warning("Cannot play while recording")
            return False

        if self._playing:
            self.stop_playback()

        self._on_playback_done = on_done
        self._play_stop_flag.clear()
        self._play_thread = threading.Thread(target=self._play_worker, args=(target,), daemon=True)
        self._play_thread.start()
        return True

    def _play_worker(self, filepath: str) -> None:
        try:
            data, samplerate = sf.read(filepath, dtype="float32")
            self._play_duration = len(data) / samplerate
            self._play_position = 0.0
            self._playing = True

            logger.info(f"Playing: {filepath} ({self._play_duration:.1f}s)")

            block_size = 1024
            total_frames = len(data)
            pos = 0

            stream = sd.OutputStream(samplerate=samplerate, channels=data.ndim, dtype="float32")
            stream.start()

            try:
                while pos < total_frames and not self._play_stop_flag.is_set():
                    end = min(pos + block_size, total_frames)
                    chunk = data[pos:end]
                    stream.write(chunk)
                    pos = end
                    self._play_position = pos / samplerate
            finally:
                stream.stop()
                stream.close()

        except Exception as e:
            logger.error(f"Playback error: {e}")
        finally:
            self._playing = False
            self._play_position = 0.0
            if self._on_playback_done:
                try:
                    self._on_playback_done()
                except Exception:
                    pass

    def stop_playback(self) -> None:
        if not self._playing:
            return
        self._play_stop_flag.set()
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=2)
        self._playing = False
        self._play_position = 0.0
        logger.info("Playback stopped")

    def get_level(self) -> float:
        """Return current audio input level (0-1) for VU meter display."""
        if not self._frames or not self._recording:
            return 0.0
        last_frame = self._frames[-1]
        return float(np.abs(last_frame).mean()) * 10


recorder = Recorder()
