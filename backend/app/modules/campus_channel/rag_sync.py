import asyncio
from datetime import datetime

from langchain_core.documents import Document

from app.core.logger_handler import logger
from app.models.chat_history import CampusChannelPost
from app.rag.vector_store import VectorStoreService


class CampusChannelRagSync:
    def __init__(self):
        self.vector_store = VectorStoreService()

    async def sync_posts(self, posts: list[CampusChannelPost]) -> tuple[list[int], int]:
        indexed_ids: list[int] = []
        failed_count = 0
        for post in posts:
            try:
                doc = self._to_document(post)
                doc_id = f"campus_channel_{post.id}_{post.content_hash[:12]}"
                try:
                    await asyncio.to_thread(self.vector_store.vectors_store.delete, ids=[doc_id])
                except Exception:
                    pass
                await asyncio.to_thread(
                    self.vector_store.vectors_store.add_documents,
                    [doc],
                    ids=[doc_id],
                )
                indexed_ids.append(post.id)
            except Exception as e:
                failed_count += 1
                logger.warning(f"【校园频道】RAG同步失败 post_id={post.id}: {e}")
        return indexed_ids, failed_count

    def _to_document(self, post: CampusChannelPost) -> Document:
        publish_time = post.publish_time.isoformat() if post.publish_time else ""
        scraped_at = post.scraped_at.isoformat() if post.scraped_at else datetime.now().isoformat()
        content = (
            f"标题：{post.title}\n"
            f"来源：腾讯频道 / {post.channel_name}\n"
            f"版块：{post.section_name}\n"
            f"作者：{post.author_name}\n"
            f"发布时间：{post.publish_time_text}\n"
            f"互动数据：点赞 {post.like_count}，评论 {post.comment_count}，分享 {post.share_count}\n\n"
            f"正文：\n{post.content}\n\n"
            f"摘要：\n{post.summary}"
        )
        metadata = {
            "source_type": "campus_channel",
            "source": "campus_channel",
            "source_platform": post.source_platform,
            "kb_type": "shared",
            "category": "校园频道",
            "doc_name": f"校园频道 / {post.section_name or '其他版块'} / {post.title or post.post_id}",
            "file_name": f"校园频道-{post.id}",
            "channel_name": post.channel_name,
            "channel_url": post.channel_url,
            "section_name": post.section_name,
            "post_url": post.post_url,
            "post_id": post.post_id,
            "author_name": post.author_name,
            "publish_time": publish_time,
            "publish_time_text": post.publish_time_text,
            "scraped_at": scraped_at,
            "campus_channel_post_id": post.id,
        }
        return Document(page_content=content, metadata=metadata)
