"""Audio recording engine using sounddevice for low-latency capture."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger

from config import settings


class Recorder:
    def __init__(self):
        self._recording = False
        self._paused = False
        self._frames: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._start_time: float = 0
        self._pause_offset: float = 0
        self._pause_start: float = 0

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_paused(self) -> bool:
        return self._paused

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

        self._frames = []
        self._pause_offset = 0
        self._start_time = time.time()
        self._recording = True
        self._paused = False

        self._stream = sd.InputStream(
            samplerate=settings.sample_rate,
            channels=settings.channels,
            dtype="float32",
            device=settings.audio_device,
            callback=self._audio_callback,
            blocksize=1024,
        )
        self._stream.start()
        logger.info("Recording started")

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
        return filepath, actual_duration

    def get_level(self) -> float:
        """Return current audio input level (0-1) for VU meter display."""
        if not self._frames or not self._recording:
            return 0.0
        last_frame = self._frames[-1]
        return float(np.abs(last_frame).mean()) * 10  # scale for visibility


recorder = Recorder()
