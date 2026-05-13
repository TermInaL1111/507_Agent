"""Bookmarks API — save/unsave AI answers via Redis."""
import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.utils.auth_utils import get_current_user_id

bookmarks_router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "3")


async def _get_redis():
    import redis.asyncio as aioredis
    return aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")


def _bookmark_key(user_id: str) -> str:
    return f"bookmarks:{user_id}"


async def _load_bookmarks(user_id: str) -> list[dict]:
    r = await _get_redis()
    data = await r.get(_bookmark_key(user_id))
    await r.aclose()
    if data:
        return json.loads(data)
    return []


async def _save_bookmarks(user_id: str, bookmarks: list[dict]):
    r = await _get_redis()
    await r.set(_bookmark_key(user_id), json.dumps(bookmarks, ensure_ascii=False))
    await r.aclose()


class BookmarkAddRequest(BaseModel):
    content: str      # AI answer text
    sources: list = []  # optional sources


@bookmarks_router.get("")
async def list_bookmarks(user_id: str = Depends(get_current_user_id)):
    bookmarks = await _load_bookmarks(user_id)
    return {"bookmarks": sorted(bookmarks, key=lambda b: b.get("created_at", ""), reverse=True)}


@bookmarks_router.post("/add")
async def add_bookmark(req: BookmarkAddRequest, user_id: str = Depends(get_current_user_id)):
    bookmarks = await _load_bookmarks(user_id)
    if len(bookmarks) >= 50:
        raise HTTPException(status_code=400, detail="最多收藏50条")

    bm = {
        "id": uuid.uuid4().hex[:12],
        "content": req.content[:500],
        "sources": req.sources[:5],
        "created_at": datetime.now().isoformat(),
    }
    bookmarks.append(bm)
    await _save_bookmarks(user_id, bookmarks)
    return {"ok": True, "bookmark": bm}


@bookmarks_router.delete("/{bookmark_id}")
async def remove_bookmark(bookmark_id: str, user_id: str = Depends(get_current_user_id)):
    bookmarks = await _load_bookmarks(user_id)
    new_list = [b for b in bookmarks if b.get("id") != bookmark_id]
    if len(new_list) == len(bookmarks):
        raise HTTPException(status_code=404, detail="收藏不存在")
    await _save_bookmarks(user_id, new_list)
    return {"ok": True}
