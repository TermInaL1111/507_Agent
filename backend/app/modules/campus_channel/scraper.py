import hashlib
import html
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any

from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.core.logger_handler import logger
from app.modules.campus_channel.schemas import CampusChannelPostCreate


SECTION_NAMES = [
    "一分钟支教", "通知", "寒武纪", "地大之声", "赛事组队", "安利室友",
    "失物招领|寻物启事", "组织小喇叭", "猫狗日记", "学习交流", "地大秋景",
    "宝藏社团", "老乡拼车", "新生爆照", "实践分享", "期末｜资料共享",
    "二手交易", "处罚公示",
]


class QQChannelScraper:
    """Best-effort scraper for QQ Channel public pages.

    It only requests the public page URL. It does not log in, solve challenges,
    call private APIs, or interact with the channel.
    """

    def __init__(self, user_agent: str | None = None, request_interval_seconds: float = 1.5):
        self.user_agent = user_agent or os.getenv(
            "CAMPUS_CHANNEL_USER_AGENT",
            "Mozilla/5.0 (compatible; 507-Agent-CampusChannel/1.0; public-page-fetch)",
        )
        self.request_interval_seconds = request_interval_seconds

    def scrape_channel(
        self,
        channel_url: str,
        max_posts: int = 100,
        section: str | None = None,
        keyword: str | None = None,
        since_days: int | None = None,
        include_images: bool = False,
    ) -> list[CampusChannelPostCreate]:
        time.sleep(max(self.request_interval_seconds, 0))
        if os.getenv("CAMPUS_CHANNEL_USE_PLAYWRIGHT", "false").lower() == "true":
            html_text = self._fetch_with_playwright(channel_url)
        else:
            html_text = self._fetch_public_html(channel_url)
        channel_name = self._extract_channel_name(html_text) or "中国地质大学（武汉）频道"
        posts = self._extract_posts_from_html(html_text, channel_url, channel_name, include_images)
        if not posts:
            logger.warning("【校园频道】公开 HTML 中未发现可解析帖子，可能页面改为动态加载或需要登录")
        filtered = self._filter_posts(posts, section=section, keyword=keyword, since_days=since_days)
        return filtered[:max_posts]

    def _fetch_public_html(self, channel_url: str) -> str:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        request = Request(channel_url, headers=headers)
        try:
            with urlopen(request, timeout=15) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                if status in (401, 403):
                    raise RuntimeError("校园频道公开页面拒绝访问或需要登录，已停止采集")
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise RuntimeError("校园频道公开页面拒绝访问或需要登录，已停止采集") from exc
            raise

    def _fetch_with_playwright(self, channel_url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("已启用 Playwright 采集，但后端环境未安装 playwright；请先安装依赖或关闭 CAMPUS_CHANNEL_USE_PLAYWRIGHT") from exc

        headless = os.getenv("CAMPUS_CHANNEL_HEADLESS", "true").lower() != "false"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page(user_agent=self.user_agent)
            try:
                response = page.goto(channel_url, wait_until="networkidle", timeout=20000)
                if response and response.status in (401, 403):
                    raise RuntimeError("校园频道公开页面拒绝访问或需要登录，已停止采集")
                page.wait_for_timeout(1200)
                body_text = page.locator("body").inner_text(timeout=5000)
                if any(token in body_text for token in ("请登录", "扫码登录", "登录后查看")):
                    raise RuntimeError("校园频道页面需要登录或限制访问，已停止采集")
                return page.content()
            finally:
                browser.close()

    def _extract_channel_name(self, html_text: str) -> str:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
        if title_match:
            title = self._clean_text(title_match.group(1))
            title = re.sub(r"[-_].*$", "", title).strip()
            if title:
                return title
        if "中国地质大学" in html_text:
            return "中国地质大学（武汉）频道"
        return ""

    def _extract_posts_from_html(
        self,
        html_text: str,
        channel_url: str,
        channel_name: str,
        include_images: bool,
    ) -> list[CampusChannelPostCreate]:
        candidates: list[dict[str, Any]] = []
        candidates.extend(self._extract_from_json_blobs(html_text))
        candidates.extend(self._extract_from_visible_text(html_text, include_images=include_images))

        seen = set()
        posts: list[CampusChannelPostCreate] = []
        for item in candidates:
            content = self._clean_text(item.get("content") or item.get("text") or item.get("summary") or "")
            title = self._clean_text(item.get("title") or self._derive_title(content))
            if not content and not title:
                continue
            text_for_quality = f"{title}{content}"
            if len(text_for_quality.strip()) < 8 or not re.search(r"[\u4e00-\u9fffA-Za-z]", text_for_quality):
                continue
            if "登录后加入频道即可发帖" in content or "不选择版块 发表 全部" in content:
                continue
            section_name = self._infer_section(item, content)
            author = self._clean_text(item.get("author_name") or item.get("author") or item.get("nick") or "")
            publish_time_text = self._clean_text(item.get("publish_time_text") or item.get("time") or "")
            publish_time = self._parse_publish_time(publish_time_text)
            post_url = self._clean_text(item.get("post_url") or item.get("url") or "")
            post_id = self._clean_text(str(item.get("post_id") or item.get("id") or ""))
            images = item.get("images") if include_images else []
            if not isinstance(images, list):
                images = []
            raw = item if isinstance(item, dict) else {}
            content_hash = self.make_content_hash(channel_url, title, content, author, publish_time_text)
            if content_hash in seen:
                continue
            seen.add(content_hash)
            posts.append(CampusChannelPostCreate(
                channel_url=channel_url,
                channel_name=channel_name,
                section_name=section_name,
                post_url=post_url,
                post_id=post_id or content_hash[:16],
                author_name=author,
                title=title,
                content=content or title,
                summary=self._summarize(content or title),
                images=[str(x) for x in images if x],
                like_count=self._safe_int(item.get("like_count") or item.get("likes")),
                comment_count=self._safe_int(item.get("comment_count") or item.get("comments")),
                share_count=self._safe_int(item.get("share_count") or item.get("shares")),
                view_count=self._safe_int_or_none(item.get("view_count") or item.get("views")),
                publish_time_text=publish_time_text,
                publish_time=publish_time,
                content_hash=content_hash,
                raw_data=raw,
            ))
        return posts

    def _extract_from_json_blobs(self, html_text: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for match in re.finditer(r"<script[^>]*>(.*?)</script>", html_text, re.I | re.S):
            script = html.unescape(match.group(1) or "")
            if not any(token in script for token in ("content", "post", "feed", "author", "topic")):
                continue
            for obj_text in re.findall(r"\{[^{}]{20,3000}\}", script):
                try:
                    obj = json.loads(obj_text)
                except Exception:
                    continue
                flattened = self._normalize_json_object(obj)
                if flattened:
                    items.append(flattened)
        return items

    def _normalize_json_object(self, obj: dict[str, Any]) -> dict[str, Any] | None:
        text_fields = ["content", "text", "summary", "desc", "description"]
        if not any(obj.get(k) for k in text_fields):
            return None
        text_value = str(obj.get("content") or obj.get("text") or obj.get("summary") or obj.get("desc") or "")
        if len(text_value.strip()) < 8 or not re.search(r"[\u4e00-\u9fffA-Za-z]", text_value):
            return None
        return {
            "id": obj.get("id") or obj.get("postId") or obj.get("msgId"),
            "title": obj.get("title") or obj.get("subject"),
            "content": obj.get("content") or obj.get("text") or obj.get("summary") or obj.get("desc"),
            "author": obj.get("author") or obj.get("nickname") or obj.get("nick"),
            "time": obj.get("time") or obj.get("publishTime") or obj.get("createdAt"),
            "section": obj.get("section") or obj.get("category") or obj.get("topic"),
            "like_count": obj.get("likeCount") or obj.get("like_count"),
            "comment_count": obj.get("commentCount") or obj.get("comment_count"),
            "share_count": obj.get("shareCount") or obj.get("share_count"),
            "view_count": obj.get("viewCount") or obj.get("view_count"),
            "url": obj.get("url") or obj.get("link"),
            "images": obj.get("images") or obj.get("pics") or [],
            "raw": obj,
        }

    def _extract_from_visible_text(self, html_text: str, include_images: bool) -> list[dict[str, Any]]:
        text = self._clean_text(re.sub(r"<script.*?</script>|<style.*?</style>", " ", html_text, flags=re.I | re.S))
        text = self._clean_text(re.sub(r"<[^>]+>", " ", html.unescape(text)))
        if len(text) < 80:
            return []
        chunks = re.split(r"(?=(?:\d+\s*(?:小时前|分钟前|天前)|刚刚|昨天|前天))", text)
        items = []
        for chunk in chunks:
            chunk = self._clean_text(chunk)
            if len(chunk) < 30:
                continue
            if not any(section in chunk for section in SECTION_NAMES) and not re.search(r"\d+\s*(小时前|天前|分钟前)", chunk):
                continue
            item = {"content": chunk[:1200], "time": self._extract_time_text(chunk)}
            parsed = self._parse_visible_post(chunk)
            if parsed:
                item.update(parsed)
            items.append(item)
        return items

    def _filter_posts(
        self,
        posts: list[CampusChannelPostCreate],
        section: str | None,
        keyword: str | None,
        since_days: int | None,
    ) -> list[CampusChannelPostCreate]:
        now = datetime.now()
        result = []
        for post in posts:
            if section and section != "全部" and section not in (post.section_name or ""):
                continue
            if keyword:
                haystack = f"{post.title}\n{post.content}\n{post.summary}\n{post.author_name}"
                if keyword.lower() not in haystack.lower():
                    continue
            if since_days and post.publish_time:
                if post.publish_time < now - timedelta(days=since_days):
                    continue
            result.append(post)
        return result

    @staticmethod
    def _parse_visible_post(chunk: str) -> dict[str, Any] | None:
        pattern = r"^(?P<time>刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+(?P<body>.+?)\s+(?P<like>\d+)\s+(?P<comment>\d+)\s+(?P<share>\d+)\s+(?P<author>[^\s]{1,40})$"
        match = re.match(pattern, chunk)
        if not match:
            return None
        body = match.group("body").strip()
        return {
            "content": body,
            "title": body[:80],
            "time": match.group("time"),
            "like_count": int(match.group("like")),
            "comment_count": int(match.group("comment")),
            "share_count": int(match.group("share")),
            "author": match.group("author"),
        }

    @staticmethod
    def make_content_hash(channel_url: str, title: str, content: str, author_name: str = "", publish_time_text: str = "") -> str:
        normalized = re.sub(r"\s+", "", f"{channel_url}|{title}|{content}|{author_name}|{publish_time_text}")[:2000]
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _clean_text(value: Any) -> str:
        return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()

    @staticmethod
    def _derive_title(content: str) -> str:
        content = content.strip()
        if not content:
            return ""
        first = re.split(r"[。！？\n]", content, maxsplit=1)[0]
        return first[:48] or content[:48]

    @staticmethod
    def _summarize(content: str) -> str:
        return (content or "").strip()[:180]

    @staticmethod
    def _infer_section(item: dict[str, Any], content: str) -> str:
        raw = str(item.get("section") or item.get("section_name") or "")
        if raw:
            return raw
        for section in SECTION_NAMES:
            if section in content:
                return section
        return "其他版块"

    @staticmethod
    def _extract_time_text(text: str) -> str:
        match = re.search(r"(刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))", text)
        return match.group(1) if match else ""

    @staticmethod
    def _parse_publish_time(value: str) -> datetime | None:
        value = str(value or "").strip()
        now = datetime.now()
        match = re.search(r"(\d+)\s*分钟前", value)
        if match:
            return now - timedelta(minutes=int(match.group(1)))
        match = re.search(r"(\d+)\s*小时前", value)
        if match:
            return now - timedelta(hours=int(match.group(1)))
        match = re.search(r"(\d+)\s*天前", value)
        if match:
            return now - timedelta(days=int(match.group(1)))
        if value == "昨天":
            return now - timedelta(days=1)
        if value == "前天":
            return now - timedelta(days=2)
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(value, fmt)
                if fmt.startswith("%m"):
                    parsed = parsed.replace(year=now.year)
                return parsed
            except ValueError:
                continue
        return None

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(float(str(value).replace(",", "").strip()))
        except Exception:
            return 0

    @classmethod
    def _safe_int_or_none(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return cls._safe_int(value)
