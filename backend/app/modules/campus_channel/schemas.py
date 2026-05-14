from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_CHANNEL_URL = "https://pd.qq.com/g/px50o26u67"


class CampusChannelPostBase(BaseModel):
    source_platform: str = "qq_channel"
    channel_url: str = DEFAULT_CHANNEL_URL
    channel_name: str = "中国地质大学（武汉）频道"
    section_name: str = ""
    post_url: str = ""
    post_id: str = ""
    author_name: str = ""
    title: str = ""
    content: str = ""
    summary: str = ""
    images: list[str] = Field(default_factory=list)
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    view_count: int | None = None
    publish_time_text: str = ""
    publish_time: datetime | None = None
    content_hash: str = ""
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CampusChannelPostCreate(CampusChannelPostBase):
    pass


class CampusChannelPostOut(CampusChannelPostBase):
    id: int
    scraped_at: datetime | None = None
    is_indexed: bool = False

    class Config:
        from_attributes = True


class CampusChannelScrapeRequest(BaseModel):
    channel_url: str = DEFAULT_CHANNEL_URL
    max_posts: int = Field(default=100, ge=1, le=500)
    section: str | None = None
    keyword: str | None = None
    since_days: int | None = Field(default=7, ge=1, le=365)
    include_images: bool = False
    dry_run: bool = False


class CampusChannelScrapeResponse(BaseModel):
    success: bool = True
    scraped_count: int = 0
    inserted_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    message: str = "校园频道采集完成"
    preview: list[CampusChannelPostOut] = Field(default_factory=list)


class CampusChannelSyncRequest(BaseModel):
    post_ids: list[int] = Field(default_factory=list)
    sync_all_unindexed: bool = True


class CampusChannelSyncResponse(BaseModel):
    success: bool = True
    indexed_count: int = 0
    failed_count: int = 0


class CampusChannelPostListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CampusChannelPostOut]


class CampusChannelStatsResponse(BaseModel):
    total_posts: int = 0
    indexed_posts: int = 0
    sections: list[dict[str, Any]] = Field(default_factory=list)
    latest_scraped_at: str | None = None
