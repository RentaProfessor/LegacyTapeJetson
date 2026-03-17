"""Cloud sync client — pushes organized memoir text to the companion app API.

Only text and metadata are synced; audio stays on device.
"""

import asyncio

import httpx
from loguru import logger

from config import settings
import storage


async def sync_story(story_id: str) -> bool:
    """Sync a single story's chapters and transcripts to the cloud API."""
    if not settings.sync_enabled or not settings.sync_api_key:
        logger.debug("Sync disabled or no API key configured")
        return False

    story = storage.get_story(story_id)
    if not story:
        return False

    chapters = storage.get_chapters(story_id)
    chapter_data = []
    for ch in chapters:
        text = storage.get_chapter_transcript(ch["id"])
        chapter_data.append({
            "chapter_num": ch["chapter_num"],
            "title": ch["title"],
            "text": text,
        })

    payload = {
        "device_story_id": story_id,
        "title": story["title"],
        "mode": story["mode"],
        "created_at": story["created_at"],
        "chapters": chapter_data,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.sync_api_url}/api/v1/stories/sync",
                json=payload,
                headers={"Authorization": f"Bearer {settings.sync_api_key}"},
            )
            resp.raise_for_status()
            storage.mark_synced(story_id)
            logger.info(f"Synced story {story_id}")
            return True
    except httpx.HTTPError as e:
        logger.error(f"Sync failed for {story_id}: {e}")
        return False


async def sync_all_pending() -> int:
    """Sync all unsynced stories. Returns count of successfully synced."""
    stories = storage.get_unsynced_stories()
    if not stories:
        return 0

    count = 0
    for story in stories:
        if await sync_story(story["id"]):
            count += 1

    logger.info(f"Synced {count}/{len(stories)} pending stories")
    return count


async def periodic_sync(interval_seconds: int = 300) -> None:
    """Background task that syncs pending stories periodically."""
    while True:
        try:
            await sync_all_pending()
        except Exception as e:
            logger.error(f"Periodic sync error: {e}")
        await asyncio.sleep(interval_seconds)
