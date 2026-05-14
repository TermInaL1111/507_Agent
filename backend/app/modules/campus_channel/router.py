from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.success_response import success_response
from app.db.db_config import get_db
from app.modules.campus_channel.repository import CampusChannelRepository
from app.modules.campus_channel.schemas import CampusChannelScrapeRequest, CampusChannelSyncRequest
from app.modules.campus_channel.service import CampusChannelService
from app.utils.auth_utils import get_current_user_id


campus_channel_router = APIRouter(prefix="/api/campus-channel", tags=["campus-channel"])


@campus_channel_router.post("/scrape")
async def scrape_campus_channel(
    request: CampusChannelScrapeRequest,
    db=Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    return success_response(data=(await CampusChannelService(db).scrape(request)).model_dump())


@campus_channel_router.get("/posts")
async def list_campus_channel_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    section: str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sort_by: str = Query(default="latest", pattern="^(latest|hot)$"),
    indexed: str = Query(default="all", pattern="^(true|false|all)$"),
    db=Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    data = await CampusChannelService(db).list_posts(page, page_size, section, keyword, start_date, end_date, sort_by, indexed)
    return success_response(data=data.model_dump())


@campus_channel_router.get("/posts/{post_id}")
async def get_campus_channel_post(post_id: int, db=Depends(get_db), _: str = Depends(get_current_user_id)):
    post = await CampusChannelRepository(db).get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return success_response(data=post)


@campus_channel_router.delete("/posts/{post_id}")
async def delete_campus_channel_post(post_id: int, db=Depends(get_db), _: str = Depends(get_current_user_id)):
    deleted = await CampusChannelRepository(db).delete_post(post_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return success_response(message="校园频道帖子已删除")


@campus_channel_router.post("/sync-rag")
async def sync_campus_channel_rag(
    request: CampusChannelSyncRequest,
    db=Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    return success_response(data=(await CampusChannelService(db).sync_rag(request)).model_dump())


@campus_channel_router.get("/stats")
async def campus_channel_stats(db=Depends(get_db), _: str = Depends(get_current_user_id)):
    return success_response(data=(await CampusChannelService(db).stats()).model_dump())
