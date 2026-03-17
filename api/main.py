"""Legacy Tape — Cloud Sync API

Receives organized memoir text from Legacy Tape devices,
stores it, and serves the companion app for family access.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from loguru import logger

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChapterIn(BaseModel):
    chapter_num: int
    title: str = ""
    text: str = ""


class StorySyncRequest(BaseModel):
    device_story_id: str
    title: str
    mode: str
    created_at: str
    chapters: list[ChapterIn]


class StoryOut(BaseModel):
    id: str
    device_story_id: str
    title: str
    mode: str
    created_at: str
    synced_at: str
    chapters: list[ChapterIn] = []


class FamilyMember(BaseModel):
    id: str
    name: str
    email: str
    role: str = "viewer"

# ---------------------------------------------------------------------------
# In-memory store (replace with PostgreSQL + SQLAlchemy in production)
# ---------------------------------------------------------------------------

stories_db: dict[str, dict] = {}
family_db: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Auth (placeholder)
# ---------------------------------------------------------------------------

async def verify_device_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing device token")
    return authorization.split(" ", 1)[1]

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Legacy Tape Cloud API starting")
    yield
    logger.info("Shutting down")


app = FastAPI(title="Legacy Tape Cloud API", version="0.1.0", lifespan=lifespan)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "stories": len(stories_db)}


@app.post("/api/v1/stories/sync")
async def sync_story(req: StorySyncRequest, token: str = Depends(verify_device_token)):
    """Receive a story sync from a Legacy Tape device."""
    import uuid

    story_id = None
    for sid, s in stories_db.items():
        if s["device_story_id"] == req.device_story_id:
            story_id = sid
            break

    if story_id is None:
        story_id = str(uuid.uuid4())

    stories_db[story_id] = {
        "id": story_id,
        "device_story_id": req.device_story_id,
        "title": req.title,
        "mode": req.mode,
        "created_at": req.created_at,
        "synced_at": datetime.utcnow().isoformat(),
        "chapters": [ch.model_dump() for ch in req.chapters],
    }

    logger.info(f"Synced story {story_id} ({req.title}, {len(req.chapters)} chapters)")
    return {"id": story_id, "status": "synced"}


@app.get("/api/v1/stories")
async def list_stories():
    """List all stories (companion app library)."""
    return list(stories_db.values())


@app.get("/api/v1/stories/{story_id}")
async def get_story(story_id: str):
    """Get a single story with chapters."""
    if story_id not in stories_db:
        raise HTTPException(status_code=404, detail="Story not found")
    return stories_db[story_id]


@app.get("/api/v1/stories/{story_id}/chapters/{chapter_num}")
async def get_chapter(story_id: str, chapter_num: int):
    """Get a specific chapter's text."""
    if story_id not in stories_db:
        raise HTTPException(status_code=404, detail="Story not found")

    for ch in stories_db[story_id]["chapters"]:
        if ch["chapter_num"] == chapter_num:
            return ch

    raise HTTPException(status_code=404, detail="Chapter not found")


@app.put("/api/v1/stories/{story_id}/chapters/{chapter_num}")
async def update_chapter(story_id: str, chapter_num: int, chapter: ChapterIn):
    """Edit a chapter (family editing from companion app)."""
    if story_id not in stories_db:
        raise HTTPException(status_code=404, detail="Story not found")

    for i, ch in enumerate(stories_db[story_id]["chapters"]):
        if ch["chapter_num"] == chapter_num:
            stories_db[story_id]["chapters"][i] = chapter.model_dump()
            return {"status": "updated"}

    raise HTTPException(status_code=404, detail="Chapter not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
