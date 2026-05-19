from datetime import datetime

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_history import CampusChannelPost
from app.modules.campus_channel.schemas import CampusChannelPostCreate


class CampusChannelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_many(self, posts: list[CampusChannelPostCreate]) -> tuple[list[CampusChannelPost], int]:
        inserted: list[CampusChannelPost] = []
        skipped = 0
        for post in posts:
            exists = await self.find_duplicate(post.post_url, post.content_hash)
            if exists:
                self._merge_existing(exists, post)
                skipped += 1
                continue
            payload = post.model_dump()
            if not payload.get("post_url"):
                payload["post_url"] = f"{payload.get('channel_url', '')}#post-{payload.get('content_hash', '')[:16]}"
            record = CampusChannelPost(**payload, scraped_at=datetime.now(), is_indexed=False)
            self.db.add(record)
            await self.db.flush()
            inserted.append(record)
        await self.db.commit()
        for item in inserted:
            await self.db.refresh(item)
        return inserted, skipped

    @staticmethod
    def _merge_existing(record: CampusChannelPost, post: CampusChannelPostCreate) -> None:
        payload = post.model_dump()
        for field in ("channel_name", "section_name", "post_url", "post_id", "author_name", "title", "publish_time_text", "publish_time"):
            value = payload.get(field)
            if value and (not getattr(record, field, None) or field in {"channel_name", "section_name", "publish_time_text", "publish_time"}):
                setattr(record, field, value)
        if payload.get("content") and len(payload["content"]) > len(record.content or ""):
            record.content = payload["content"]
        if payload.get("summary") and len(payload["summary"]) > len(record.summary or ""):
            record.summary = payload["summary"]
        merged_images = list(dict.fromkeys((record.images or []) + (payload.get("images") or [])))
        record.images = merged_images
        for field in ("like_count", "comment_count", "share_count", "view_count"):
            value = payload.get(field)
            if value is not None and int(value or 0) >= int(getattr(record, field, 0) or 0):
                setattr(record, field, value)
        raw = dict(record.raw_data or {})
        new_raw = payload.get("raw_data") or {}
        raw.update(new_raw)
        if new_raw.get("comments"):
            raw["comments"] = new_raw["comments"]
        record.raw_data = raw
        record.scraped_at = datetime.now()

    async def find_duplicate(self, post_url: str, content_hash: str) -> CampusChannelPost | None:
        conditions = []
        if post_url:
            conditions.append(CampusChannelPost.post_url == post_url)
        if content_hash:
            conditions.append(CampusChannelPost.content_hash == content_hash)
        if not conditions:
            return None
        result = await self.db.execute(select(CampusChannelPost).where(or_(*conditions)).limit(1))
        return result.scalar_one_or_none()

    async def list_posts(
        self,
        page: int = 1,
        page_size: int = 20,
        section: str | None = None,
        keyword: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sort_by: str = "latest",
        indexed: str = "all",
    ) -> tuple[list[CampusChannelPost], int]:
        stmt = select(CampusChannelPost).distinct(CampusChannelPost.content_hash)
        count_stmt = select(func.count(func.distinct(CampusChannelPost.content_hash))).select_from(CampusChannelPost)
        filters = self._filters(section, keyword, start_date, end_date, indexed)
        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))
        if sort_by == "hot":
            hot_score = (
                CampusChannelPost.like_count
                + CampusChannelPost.comment_count * 2
                + CampusChannelPost.share_count * 3
            )
            stmt = stmt.order_by(hot_score.desc(), CampusChannelPost.publish_time.desc(), CampusChannelPost.scraped_at.desc())
        else:
            stmt = stmt.order_by(CampusChannelPost.publish_time.desc(), CampusChannelPost.scraped_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_stmt)).scalar_one()
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(rows), int(total or 0)

    def _filters(self, section, keyword, start_date, end_date, indexed):
        filters = []
        if section and section != "全部":
            filters.append(CampusChannelPost.section_name == section)
        if keyword:
            like = f"%{keyword}%"
            filters.append(or_(
                CampusChannelPost.title.like(like),
                CampusChannelPost.content.like(like),
                CampusChannelPost.summary.like(like),
                CampusChannelPost.author_name.like(like),
            ))
        if start_date:
            filters.append(CampusChannelPost.publish_time >= start_date)
        if end_date:
            filters.append(CampusChannelPost.publish_time <= end_date)
        if indexed == "true":
            filters.append(CampusChannelPost.is_indexed.is_(True))
        elif indexed == "false":
            filters.append(CampusChannelPost.is_indexed.is_(False))
        return filters

    async def get_post(self, post_id: int) -> CampusChannelPost | None:
        return await self.db.get(CampusChannelPost, post_id)

    async def delete_post(self, post_id: int) -> bool:
        result = await self.db.execute(delete(CampusChannelPost).where(CampusChannelPost.id == post_id))
        await self.db.commit()
        return bool(result.rowcount)

    async def get_posts_for_sync(self, post_ids: list[int], sync_all_unindexed: bool) -> list[CampusChannelPost]:
        stmt = select(CampusChannelPost)
        if sync_all_unindexed:
            stmt = stmt.where(CampusChannelPost.is_indexed.is_(False))
        elif post_ids:
            stmt = stmt.where(CampusChannelPost.id.in_(post_ids))
        else:
            return []
        rows = (await self.db.execute(stmt.order_by(CampusChannelPost.scraped_at.desc()))).scalars().all()
        return list(rows)

    async def mark_indexed(self, post_ids: list[int]) -> None:
        if not post_ids:
            return
        rows = (await self.db.execute(select(CampusChannelPost).where(CampusChannelPost.id.in_(post_ids)))).scalars().all()
        for row in rows:
            row.is_indexed = True
        await self.db.commit()

    async def stats(self) -> dict:
        total = (await self.db.execute(select(func.count()).select_from(CampusChannelPost))).scalar_one() or 0
        indexed = (await self.db.execute(
            select(func.count()).select_from(CampusChannelPost).where(CampusChannelPost.is_indexed.is_(True))
        )).scalar_one() or 0
        latest = (await self.db.execute(select(func.max(CampusChannelPost.scraped_at)))).scalar_one()
        sections_rows = (await self.db.execute(
            select(CampusChannelPost.section_name, func.count())
            .group_by(CampusChannelPost.section_name)
            .order_by(func.count().desc())
        )).all()
        return {
            "total_posts": int(total),
            "indexed_posts": int(indexed),
            "latest_scraped_at": latest.isoformat() if latest else None,
            "sections": [{"name": name or "其他版块", "count": int(count)} for name, count in sections_rows],
        }
