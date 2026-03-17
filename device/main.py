"""Legacy Tape — Device Orchestrator

FastAPI application that ties together recording, transcription,
memoir structuring, Pico 2 button handling, and the UI.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import settings
from recorder import recorder, list_audio_devices
from transcriber import transcribe, warmup as warmup_whisper
from memoir_engine import process_transcript, generate_chapter_title, generate_follow_up_questions
from pico_bridge import on_button, start_pico_listener, send_state
from sync_client import periodic_sync
import storage

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

current_story: Optional[Dict] = None
current_chapter: Optional[Dict] = None
current_mode: str = settings.default_mode
ws_clients: Set[WebSocket] = set()
_playback_monitor_task: Optional[asyncio.Task] = None
_recording_monitor_task: Optional[asyncio.Task] = None
_transcription_task: Optional[asyncio.Task] = None


async def broadcast(event: dict) -> None:
    """Send state update to all connected WebSocket clients (UI)."""
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.add(ws)
    ws_clients.difference_update(dead)


# ---------------------------------------------------------------------------
# Playback progress monitor
# ---------------------------------------------------------------------------

async def _monitor_playback() -> None:
    """Poll recorder.is_playing and broadcast progress to the UI."""
    try:
        while recorder.is_playing:
            progress = 0.0
            if recorder.play_duration > 0:
                progress = recorder.play_position / recorder.play_duration
            await broadcast({
                "type": "playback_progress",
                "position": round(recorder.play_position, 1),
                "duration": round(recorder.play_duration, 1),
                "progress": round(min(progress, 1.0), 3),
            })
            await asyncio.sleep(0.25)
    except asyncio.CancelledError:
        pass
    finally:
        await broadcast({"type": "state", "state": "idle"})


# ---------------------------------------------------------------------------
# Recording level monitor
# ---------------------------------------------------------------------------

async def _monitor_recording() -> None:
    """Broadcast audio input level while recording so UI can show VU meter."""
    try:
        while recorder.is_recording:
            level = recorder.get_level()
            elapsed = recorder.elapsed_seconds
            await broadcast({
                "type": "recording_level",
                "level": round(min(level, 1.0), 3),
                "elapsed": round(elapsed, 1),
            })
            await asyncio.sleep(0.2)
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Background transcription
# ---------------------------------------------------------------------------

async def _run_transcription(filepath: str, duration: float, chapter_id: str) -> None:
    """Run transcription in background so the UI isn't blocked."""
    global current_chapter
    try:
        rec = storage.save_recording(chapter_id, filepath, duration)
        result = await transcribe(filepath)

        processed = process_transcript(result["text"], current_mode)
        storage.save_transcript(rec["id"], result["text"], processed)

        title = generate_chapter_title(result["text"])
        db = storage.get_db()
        db.execute("UPDATE chapters SET title = ? WHERE id = ?", (title, chapter_id))
        db.commit()

        await broadcast({
            "type": "transcript_ready",
            "transcript": {
                "raw": result["text"],
                "processed": processed,
                "duration": result["duration"],
            },
            "chapter_title": title,
        })
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        await broadcast({
            "type": "error",
            "action": "transcribe",
            "message": str(e),
        })


# ---------------------------------------------------------------------------
# Button handlers
# ---------------------------------------------------------------------------

async def handle_record() -> None:
    global current_story, current_chapter, _recording_monitor_task

    if recorder.is_recording:
        logger.info("Already recording")
        return

    if recorder.is_playing:
        recorder.stop_playback()

    if current_story is None:
        current_story = storage.create_story(mode=current_mode)
        current_chapter = storage.create_chapter(current_story["id"], 1, "Chapter 1")
    elif current_chapter is None:
        chapters = storage.get_chapters(current_story["id"])
        next_num = len(chapters) + 1
        current_chapter = storage.create_chapter(
            current_story["id"], next_num, f"Chapter {next_num}"
        )

    try:
        recorder.start()
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        await broadcast({"type": "error", "action": "record", "message": str(e)})
        return

    _recording_monitor_task = asyncio.create_task(_monitor_recording())

    await broadcast({
        "type": "state",
        "state": "recording",
        "story": current_story,
        "chapter": current_chapter,
        "mode": current_mode,
    })
    await send_state({"state": "recording"})


async def handle_stop() -> None:
    global current_chapter, _playback_monitor_task, _recording_monitor_task, _transcription_task

    if recorder.is_playing:
        recorder.stop_playback()
        if _playback_monitor_task:
            _playback_monitor_task.cancel()
            _playback_monitor_task = None
        await broadcast({"type": "state", "state": "idle"})
        return

    if not recorder.is_recording:
        await broadcast({"type": "state", "state": "idle"})
        return

    if _recording_monitor_task:
        _recording_monitor_task.cancel()
        _recording_monitor_task = None

    result = recorder.stop()
    if not result:
        await broadcast({"type": "state", "state": "idle"})
        await send_state({"state": "idle"})
        return

    filepath, duration = result
    logger.info(f"Recording stopped: {filepath} ({duration:.1f}s)")

    chapter_id = current_chapter["id"] if current_chapter else None
    current_chapter = None

    if chapter_id:
        await broadcast({"type": "state", "state": "transcribing"})
        _transcription_task = asyncio.create_task(
            _run_transcription(filepath, duration, chapter_id)
        )
    else:
        await broadcast({"type": "state", "state": "idle"})

    await send_state({"state": "idle"})


async def handle_pause() -> None:
    if recorder.is_recording and not recorder.is_paused:
        recorder.pause()
        await broadcast({"type": "state", "state": "paused"})
    elif recorder.is_recording and recorder.is_paused:
        recorder.resume()
        await broadcast({"type": "state", "state": "recording"})


async def handle_play() -> None:
    global _playback_monitor_task

    if recorder.is_recording or recorder.is_playing:
        return

    if not recorder.last_recording_path:
        logger.warning("No recording to play")
        await broadcast({"type": "state", "state": "idle"})
        return

    loop = asyncio.get_event_loop()

    def on_done():
        loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(broadcast({"type": "state", "state": "idle"}))
        )

    started = recorder.play(on_done=on_done)
    if started:
        await broadcast({"type": "state", "state": "playback"})
        _playback_monitor_task = asyncio.create_task(_monitor_playback())
    else:
        logger.warning("Playback failed to start")
        await broadcast({"type": "state", "state": "idle"})


async def handle_rewind() -> None:
    await broadcast({"type": "action", "action": "rewind"})


async def handle_ffwd() -> None:
    global current_chapter

    if not recorder.is_recording and current_story:
        chapters = storage.get_chapters(current_story["id"])
        next_num = len(chapters) + 1
        current_chapter = storage.create_chapter(
            current_story["id"], next_num, f"Chapter {next_num}"
        )
        await broadcast({
            "type": "new_chapter",
            "chapter": current_chapter,
        })


async def handle_mode(value: str = None) -> None:
    global current_mode
    modes = ["clean", "ai_interview", "ghost_writer"]
    if value and value in modes:
        current_mode = value
    else:
        idx = modes.index(current_mode)
        current_mode = modes[(idx + 1) % len(modes)]

    await broadcast({"type": "mode", "mode": current_mode})


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Data dir: {settings.data_dir}")

    recorder.resolve_input_device()
    warmup_whisper()

    on_button("record", handle_record)
    on_button("stop", handle_stop)
    on_button("pause", handle_pause)
    on_button("play", handle_play)
    on_button("rewind", handle_rewind)
    on_button("ffwd", handle_ffwd)
    on_button("mode", handle_mode)

    asyncio.create_task(start_pico_listener())

    if settings.sync_enabled:
        asyncio.create_task(periodic_sync())

    yield

    recorder.stop_playback()
    logger.info("Shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Legacy Tape", lifespan=lifespan)


# ---------------------------------------------------------------------------
# WebSocket — real-time state updates to the cassette UI
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global current_story, current_chapter

    await ws.accept()
    ws_clients.add(ws)
    logger.info(f"UI connected ({len(ws_clients)} clients)")

    current_state = "idle"
    if recorder.is_recording:
        current_state = "recording"
    elif recorder.is_playing:
        current_state = "playback"

    await ws.send_json({
        "type": "state",
        "state": current_state,
        "mode": current_mode,
        "story": current_story,
        "chapter": current_chapter,
    })

    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            try:
                if action == "record":
                    await handle_record()
                elif action == "stop":
                    await handle_stop()
                elif action == "pause":
                    await handle_pause()
                elif action == "play":
                    await handle_play()
                elif action == "rewind":
                    await handle_rewind()
                elif action == "ffwd":
                    await handle_ffwd()
                elif action == "mode":
                    await handle_mode(data.get("value"))
                elif action == "new_story":
                    current_story = None
                    current_chapter = None
                    await broadcast({"type": "state", "state": "idle", "story": None, "chapter": None})
            except Exception as e:
                logger.error(f"Action '{action}' failed: {e}")
                await broadcast({
                    "type": "error",
                    "action": action,
                    "message": str(e),
                })
                await broadcast({"type": "state", "state": "idle"})
    except WebSocketDisconnect:
        ws_clients.discard(ws)
        logger.info(f"UI disconnected ({len(ws_clients)} clients)")


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "recording": recorder.is_recording,
        "playing": recorder.is_playing,
        "mode": current_mode,
        "story": current_story,
    }


@app.get("/api/devices")
async def get_devices():
    return {"devices": list_audio_devices()}


@app.get("/api/stories")
async def list_stories():
    return storage.get_stories()


@app.get("/api/stories/{story_id}")
async def get_story(story_id: str):
    story = storage.get_story(story_id)
    if not story:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    chapters = storage.get_chapters(story_id)
    for ch in chapters:
        ch["text"] = storage.get_chapter_transcript(ch["id"])
    story["chapters"] = chapters
    return story


@app.get("/api/stories/{story_id}/chapters")
async def list_chapters(story_id: str):
    return storage.get_chapters(story_id)


@app.post("/api/record")
async def start_recording():
    await handle_record()
    return {"status": "recording"}


@app.post("/api/stop")
async def stop_recording():
    await handle_stop()
    return {"status": "stopped"}


@app.post("/api/pause")
async def pause_recording():
    await handle_pause()
    return {"status": "paused" if recorder.is_paused else "recording"}


@app.post("/api/play")
async def play_recording():
    await handle_play()
    return {"status": "playing" if recorder.is_playing else "idle"}


@app.post("/api/mode/{mode}")
async def set_mode(mode: str):
    await handle_mode(mode)
    return {"mode": current_mode}


@app.post("/api/sync")
async def trigger_sync():
    from sync_client import sync_all_pending
    count = await sync_all_pending()
    return {"synced": count}


# ---------------------------------------------------------------------------
# Serve the UI
# ---------------------------------------------------------------------------

ui_dist = Path(__file__).parent.parent / "ui" / "dist"
if ui_dist.exists():
    app.mount("/", StaticFiles(directory=str(ui_dist), html=True), name="ui")
else:
    @app.get("/")
    async def root():
        return {"message": "Legacy Tape API running. Build UI with: cd ui && npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )
