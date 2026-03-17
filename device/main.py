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
from recorder import recorder
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


async def broadcast(event: dict) -> None:
    """Send state update to all connected WebSocket clients (UI)."""
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.add(ws)
    ws_clients -= dead


# ---------------------------------------------------------------------------
# Button handlers
# ---------------------------------------------------------------------------

async def handle_record() -> None:
    global current_story, current_chapter

    if recorder.is_recording:
        logger.info("Already recording")
        return

    if current_story is None:
        current_story = storage.create_story(mode=current_mode)
        current_chapter = storage.create_chapter(current_story["id"], 1, "Chapter 1")
    elif current_chapter is None:
        chapters = storage.get_chapters(current_story["id"])
        next_num = len(chapters) + 1
        current_chapter = storage.create_chapter(
            current_story["id"], next_num, f"Chapter {next_num}"
        )

    recorder.start()
    await broadcast({
        "type": "state",
        "state": "recording",
        "story": current_story,
        "chapter": current_chapter,
        "mode": current_mode,
    })
    await send_state({"state": "recording"})


async def handle_stop() -> None:
    global current_chapter

    if not recorder.is_recording:
        return

    result = recorder.stop()
    if not result:
        await broadcast({"type": "state", "state": "idle"})
        return

    filepath, duration = result
    await broadcast({"type": "state", "state": "transcribing"})

    rec = storage.save_recording(current_chapter["id"], filepath, duration)

    result = await transcribe(filepath)

    processed = process_transcript(result["text"], current_mode)
    storage.save_transcript(rec["id"], result["text"], processed)

    title = generate_chapter_title(result["text"])
    if not current_chapter.get("title") or current_chapter["title"].startswith("Chapter"):
        db = storage.get_db()
        db.execute("UPDATE chapters SET title = ? WHERE id = ?", (title, current_chapter["id"]))
        db.commit()
        current_chapter["title"] = title

    current_chapter = None

    await broadcast({
        "type": "state",
        "state": "idle",
        "transcript": {
            "raw": result["text"],
            "processed": processed,
            "duration": result["duration"],
        },
    })

    if current_mode == "ai_interview":
        questions = generate_follow_up_questions(result["text"])
        await broadcast({"type": "follow_up", "questions": questions})

    await send_state({"state": "idle"})


async def handle_pause() -> None:
    if recorder.is_recording and not recorder.is_paused:
        recorder.pause()
        await broadcast({"type": "state", "state": "paused"})
    elif recorder.is_recording and recorder.is_paused:
        recorder.resume()
        await broadcast({"type": "state", "state": "recording"})


async def handle_play() -> None:
    await broadcast({"type": "state", "state": "playback"})


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

    await ws.send_json({
        "type": "state",
        "state": "recording" if recorder.is_recording else "idle",
        "mode": current_mode,
        "story": current_story,
        "chapter": current_chapter,
    })

    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
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
        "mode": current_mode,
        "story": current_story,
    }


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
