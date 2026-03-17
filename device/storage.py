"""Local SQLite storage for recordings, transcripts, and chapters."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from config import settings

_db: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        _db = sqlite3.connect(settings.db_path, check_same_thread=False)
        _db.row_factory = sqlite3.Row
        _db.execute("PRAGMA journal_mode=WAL")
        _db.execute("PRAGMA foreign_keys=ON")
        _init_schema(_db)
    return _db


def _init_schema(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS stories (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL DEFAULT 'Untitled Story',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            mode            TEXT NOT NULL DEFAULT 'clean',
            synced          INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS chapters (
            id              TEXT PRIMARY KEY,
            story_id        TEXT NOT NULL REFERENCES stories(id),
            chapter_num     INTEGER NOT NULL,
            title           TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            UNIQUE(story_id, chapter_num)
        );

        CREATE TABLE IF NOT EXISTS recordings (
            id              TEXT PRIMARY KEY,
            chapter_id      TEXT NOT NULL REFERENCES chapters(id),
            file_path       TEXT NOT NULL,
            duration_secs   REAL NOT NULL DEFAULT 0,
            recorded_at     TEXT NOT NULL,
            transcribed     INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS transcripts (
            id              TEXT PRIMARY KEY,
            recording_id    TEXT NOT NULL REFERENCES recordings(id),
            raw_text        TEXT NOT NULL DEFAULT '',
            processed_text  TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL
        );
    """)
    db.commit()


def create_story(title: str = "Untitled Story", mode: str = "clean") -> Dict:
    db = get_db()
    story_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO stories (id, title, created_at, updated_at, mode) VALUES (?, ?, ?, ?, ?)",
        (story_id, title, now, now, mode),
    )
    db.commit()
    logger.info(f"Created story {story_id}: {title}")
    return {"id": story_id, "title": title, "mode": mode, "created_at": now}


def create_chapter(story_id: str, chapter_num: int, title: str = "") -> Dict:
    db = get_db()
    chapter_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO chapters (id, story_id, chapter_num, title, created_at) VALUES (?, ?, ?, ?, ?)",
        (chapter_id, story_id, chapter_num, title, now),
    )
    db.commit()
    logger.info(f"Created chapter {chapter_num} for story {story_id}")
    return {"id": chapter_id, "story_id": story_id, "chapter_num": chapter_num, "title": title}


def save_recording(chapter_id: str, file_path: str, duration: float) -> Dict:
    db = get_db()
    rec_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO recordings (id, chapter_id, file_path, duration_secs, recorded_at) VALUES (?, ?, ?, ?, ?)",
        (rec_id, chapter_id, file_path, duration, now),
    )
    db.commit()
    logger.info(f"Saved recording {rec_id} ({duration:.1f}s)")
    return {"id": rec_id, "chapter_id": chapter_id, "duration": duration}


def save_transcript(recording_id: str, raw_text: str, processed_text: str = "") -> Dict:
    db = get_db()
    tid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO transcripts (id, recording_id, raw_text, processed_text, created_at) VALUES (?, ?, ?, ?, ?)",
        (tid, recording_id, raw_text, processed_text or raw_text, now),
    )
    db.execute("UPDATE recordings SET transcribed = 1 WHERE id = ?", (recording_id,))
    db.commit()
    return {"id": tid, "recording_id": recording_id}


def get_story(story_id: str) -> Optional[Dict]:
    db = get_db()
    row = db.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
    return dict(row) if row else None


def get_stories() -> List[Dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM stories ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_chapters(story_id: str) -> List[Dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM chapters WHERE story_id = ? ORDER BY chapter_num", (story_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_chapter_transcript(chapter_id: str) -> str:
    """Get the combined processed transcript text for a chapter."""
    db = get_db()
    rows = db.execute("""
        SELECT t.processed_text FROM transcripts t
        JOIN recordings r ON t.recording_id = r.id
        WHERE r.chapter_id = ?
        ORDER BY r.recorded_at
    """, (chapter_id,)).fetchall()
    return "\n\n".join(r["processed_text"] for r in rows)


def get_unsynced_stories() -> List[Dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM stories WHERE synced = 0").fetchall()
    return [dict(r) for r in rows]


def mark_synced(story_id: str) -> None:
    db = get_db()
    db.execute("UPDATE stories SET synced = 1 WHERE id = ?", (story_id,))
    db.commit()
