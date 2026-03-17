"""Local Whisper transcription via whisper.cpp, with mock fallback for Mac dev.

Backends:
  - whisper_cpp: Calls the whisper.cpp binary (CUDA on Jetson, Metal on Mac)
  - mock: Returns fake transcripts for UI testing without any model
"""

import asyncio
import json
import random
import subprocess
import time
from functools import partial
from pathlib import Path

from loguru import logger

from config import settings

# ---------------------------------------------------------------------------
# Mock backend — for UI development and testing without a Whisper model
# ---------------------------------------------------------------------------

_MOCK_STORIES = [
    "I remember the summer of nineteen fifty two when we drove all the way "
    "from Ohio to California. Your grandfather had just bought that old blue "
    "Chevy and we packed everything we owned into the back seat. The kids were "
    "so excited they could barely sit still.",

    "My mother used to make the most wonderful apple pie. She would wake up at "
    "five in the morning just to get the crust right. The whole house would smell "
    "like cinnamon and brown sugar. I have tried to recreate it a hundred times "
    "but it never tastes quite the same.",

    "When I was sixteen I got my first job at the hardware store on Main Street. "
    "Old Mr. Henderson was the owner and he taught me everything about hard work. "
    "I earned thirty five cents an hour and I thought I was the richest kid in town.",

    "The day your father was born was the happiest day of my life. It was raining "
    "outside and the hospital was packed. But when the nurse put him in my arms "
    "everything else just disappeared. He had the tiniest little fingers.",

    "We used to have a dog named Biscuit. He was a golden retriever and the "
    "friendliest animal you ever met. He would wait by the front door every single "
    "day for the kids to come home from school. When he passed away we all cried "
    "for a week straight.",
]


def _transcribe_mock(audio_path: str) -> dict:
    story = random.choice(_MOCK_STORIES)
    sentences = [s.strip() for s in story.split(".") if s.strip()]
    segments = []
    t = 0.0
    for sentence in sentences:
        duration = len(sentence.split()) * 0.4
        segments.append({"start": round(t, 2), "end": round(t + duration, 2), "text": sentence + "."})
        t += duration + 0.5

    time.sleep(1.5)  # simulate processing delay

    logger.info(f"Mock transcription for {audio_path}: {len(segments)} segments")
    return {
        "text": story,
        "segments": segments,
        "language": "en",
        "duration": t,
    }


# ---------------------------------------------------------------------------
# whisper.cpp backend
# ---------------------------------------------------------------------------

def _transcribe_whisper_cpp(audio_path: str) -> dict:
    if not settings.whisper_cpp_bin:
        raise RuntimeError("whisper.cpp binary not found — set LT_WHISPER_CPP_BIN")
    if not settings.whisper_model_path:
        raise RuntimeError("Whisper model not found — set LT_WHISPER_MODEL_PATH")

    cmd = [
        settings.whisper_cpp_bin,
        "-m", settings.whisper_model_path,
        "-f", audio_path,
        "-l", settings.whisper_language,
        "--output-json",
        "--no-prints",
    ]

    logger.info(f"Running whisper.cpp: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.error(f"whisper.cpp failed: {result.stderr}")
        raise RuntimeError(f"whisper.cpp error: {result.stderr[:500]}")

    json_path = Path(audio_path + ".json")
    if not json_path.exists():
        json_path = Path(audio_path).with_suffix(".json")

    if json_path.exists():
        data = json.loads(json_path.read_text())
        json_path.unlink()
        return _parse_whisper_json(data)

    return _parse_whisper_stdout(result.stdout)


def _parse_whisper_json(data: dict) -> dict:
    """Parse whisper.cpp JSON output format."""
    segments = []
    full_text_parts = []

    for item in data.get("transcription", []):
        text = item.get("text", "").strip()
        if not text:
            continue

        start_ms = item.get("offsets", {}).get("from", 0)
        end_ms = item.get("offsets", {}).get("to", 0)

        segments.append({
            "start": start_ms / 1000.0,
            "end": end_ms / 1000.0,
            "text": text,
        })
        full_text_parts.append(text)

    full_text = " ".join(full_text_parts)
    duration = segments[-1]["end"] if segments else 0

    logger.info(f"whisper.cpp: {len(segments)} segments, {len(full_text)} chars")
    return {
        "text": full_text,
        "segments": segments,
        "language": settings.whisper_language,
        "duration": duration,
    }


def _parse_whisper_stdout(stdout: str) -> dict:
    """Fallback: parse timestamp lines from whisper.cpp stdout."""
    segments = []
    full_text_parts = []

    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("["):
            continue
        try:
            time_part, text = line.split("]", 1)
            time_part = time_part.lstrip("[")
            start_str, end_str = time_part.split("-->")
            start = _parse_timestamp(start_str.strip())
            end = _parse_timestamp(end_str.strip())
            text = text.strip()
            if text:
                segments.append({"start": start, "end": end, "text": text})
                full_text_parts.append(text)
        except (ValueError, IndexError):
            continue

    full_text = " ".join(full_text_parts)
    duration = segments[-1]["end"] if segments else 0

    return {
        "text": full_text,
        "segments": segments,
        "language": settings.whisper_language,
        "duration": duration,
    }


def _parse_timestamp(ts: str) -> float:
    """Parse 'HH:MM:SS.mmm' or 'MM:SS.mmm' to seconds."""
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(ts)


# ---------------------------------------------------------------------------
# Public API — same interface regardless of backend
# ---------------------------------------------------------------------------

def transcribe_sync(audio_path: str) -> dict:
    backend = settings.whisper_backend
    logger.info(f"Transcribing {audio_path} (backend={backend})")

    if backend == "mock":
        return _transcribe_mock(audio_path)
    elif backend == "whisper_cpp":
        return _transcribe_whisper_cpp(audio_path)
    else:
        raise ValueError(f"Unknown whisper backend: {backend}")


async def transcribe(audio_path: str) -> dict:
    """Async wrapper — runs transcription in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(transcribe_sync, audio_path))


def warmup() -> None:
    """Log which backend is active. For whisper_cpp, verify the binary exists."""
    backend = settings.whisper_backend
    logger.info(f"Transcription backend: {backend}")

    if backend == "whisper_cpp":
        if not Path(settings.whisper_cpp_bin).exists():
            logger.error(f"whisper.cpp binary not found at {settings.whisper_cpp_bin}")
            raise FileNotFoundError(settings.whisper_cpp_bin)
        if not Path(settings.whisper_model_path).exists():
            logger.error(f"Whisper model not found at {settings.whisper_model_path}")
            raise FileNotFoundError(settings.whisper_model_path)
        logger.info(f"  binary: {settings.whisper_cpp_bin}")
        logger.info(f"  model:  {settings.whisper_model_path}")
    elif backend == "mock":
        logger.warning("Using MOCK transcriber — set LT_WHISPER_BACKEND=whisper_cpp for real transcription")
