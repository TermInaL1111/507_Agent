import asyncio
import os
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger_handler import logger
from app.modules.campus_channel.rag_sync import CampusChannelRagSync
from app.modules.campus_channel.repository import CampusChannelRepository
from app.modules.campus_channel.schemas import (
    CampusChannelPostListResponse,
    CampusChannelScrapeRequest,
    CampusChannelScrapeResponse,
    CampusChannelStatsResponse,
    CampusChannelSyncRequest,
    CampusChannelSyncResponse,
)
from app.modules.campus_channel.scraper import QQChannelScraper


class CampusChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CampusChannelRepository(db)

    async def scrape(self, request: CampusChannelScrapeRequest) -> CampusChannelScrapeResponse:
        scraper = QQChannelScraper()
        try:
            posts = await asyncio.to_thread(
                scraper.scrape_channel,
                request.channel_url,
                request.max_posts,
                request.section,
                request.keyword,
                request.since_days,
                request.include_images,
            )
        except Exception as e:
            logger.warning(f"【校园频道】采集失败: {e}")
            return CampusChannelScrapeResponse(
                success=False,
                failed_count=1,
                message="校园频道内容采集失败，请稍后重试。若页面需要登录或限制访问，请检查频道公开访问状态。",
            )

        if request.dry_run:
            return CampusChannelScrapeResponse(
                success=True,
                scraped_count=len(posts),
                inserted_count=0,
                skipped_count=0,
                failed_count=0,
                message="校园频道采集预览完成",
                preview=[],
            )

        inserted, skipped = await self.repo.upsert_many(posts)
        logger.info(f"【校园频道】采集完成 scraped={len(posts)} inserted={len(inserted)} skipped={skipped}")
        return CampusChannelScrapeResponse(
            success=True,
            scraped_count=len(posts),
            inserted_count=len(inserted),
            skipped_count=skipped,
            failed_count=0,
            message="校园频道采集完成",
        )

    async def list_posts(
        self,
        page: int,
        page_size: int,
        section: str | None,
        keyword: str | None,
        start_date: str | None,
        end_date: str | None,
        sort_by: str,
        indexed: str,
    ) -> CampusChannelPostListResponse:
        rows, total = await self.repo.list_posts(
            page=page,
            page_size=page_size,
            section=section,
            keyword=keyword,
            start_date=self._parse_date(start_date),
            end_date=self._parse_date(end_date),
            sort_by=sort_by,
            indexed=indexed,
        )
        return CampusChannelPostListResponse(total=total, page=page, page_size=page_size, items=rows)

    async def sync_rag(self, request: CampusChannelSyncRequest) -> CampusChannelSyncResponse:
        posts = await self.repo.get_posts_for_sync(request.post_ids, request.sync_all_unindexed)
        indexed_ids, failed_count = await CampusChannelRagSync().sync_posts(posts)
        await self.repo.mark_indexed(indexed_ids)
        return CampusChannelSyncResponse(success=True, indexed_count=len(indexed_ids), failed_count=failed_count)

    async def stats(self) -> CampusChannelStatsResponse:
        return CampusChannelStatsResponse(**await self.repo.stats())

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None


_auto_task: asyncio.Task | None = None


async def start_campus_channel_scheduler():
    global _auto_task
    if str(os.getenv("CAMPUS_CHANNEL_AUTO_SCRAPE", "false")).lower() != "true":
        return
    if _auto_task and not _auto_task.done():
        return
    _auto_task = asyncio.create_task(_auto_scrape_loop())
    logger.info("【校园频道】自动采集任务已启动")


async def _auto_scrape_loop():
    from app.db.db_config import AsyncSessionLocal

    interval = int(os.getenv("CAMPUS_CHANNEL_SCRAPE_INTERVAL_MINUTES", "360"))
    channel_url = os.getenv("CAMPUS_CHANNEL_URL", "https://pd.qq.com/g/px50o26u67")
    max_posts = int(os.getenv("CAMPUS_CHANNEL_MAX_POSTS_PER_RUN", "50"))
    include_images = str(os.getenv("CAMPUS_CHANNEL_INCLUDE_IMAGES", "false")).lower() == "true"
    auto_sync = str(os.getenv("CAMPUS_CHANNEL_AUTO_SYNC_RAG", "false")).lower() == "true"
    while True:
        try:
            async with AsyncSessionLocal() as db:
                service = CampusChannelService(db)
                await service.scrape(CampusChannelScrapeRequest(
                    channel_url=channel_url,
                    max_posts=max_posts,
                    since_days=None,
                    include_images=include_images,
                ))
                if auto_sync:
                    await service.sync_rag(CampusChannelSyncRequest(sync_all_unindexed=True))
        except Exception as e:
            logger.warning(f"【校园频道】自动采集任务失败: {e}")
        await asyncio.sleep(max(interval, 5) * 60)
