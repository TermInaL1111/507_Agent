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
from urllib.parse import urlparse

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
        mode = os.getenv("CAMPUS_CHANNEL_USE_PLAYWRIGHT", "auto").lower()
        html_sources: list[tuple[str, str]] = []

        if mode in {"true", "1", "yes", "auto"}:
            try:
                html_sources.append(("playwright", self._fetch_with_playwright(channel_url)))
            except Exception as exc:
                if mode in {"true", "1", "yes"}:
                    raise
                logger.warning(f"【校园频道】Playwright 采集不可用，回退静态 HTML: {exc}")

        if mode in {"false", "0", "no", "auto"} or not html_sources:
            html_sources.append(("static", self._fetch_public_html(channel_url)))

        channel_name = "中国地质大学（武汉）频道"
        all_posts: list[CampusChannelPostCreate] = []
        seen = set()
        for source_name, html_text in html_sources:
            channel_name = self._extract_channel_name(html_text) or channel_name
            posts = self._extract_posts_from_html(html_text, channel_url, channel_name, include_images)
            logger.info(f"【校园频道】{source_name} 解析候选帖子 {len(posts)} 条")
            for post in posts:
                dedupe_key = post.post_id or post.post_url or post.content_hash
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                all_posts.append(post)

        all_posts = self._enrich_posts_from_public_detail(all_posts, include_images=include_images)

        if not all_posts:
            logger.warning("【校园频道】公开页面中未发现可解析帖子，可能页面需要登录、限制访问或结构变化")
        filtered = self._filter_posts(all_posts, section=section, keyword=keyword, since_days=since_days)
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
            raise RuntimeError("后端环境未安装 playwright，无法使用浏览器渲染采集") from exc

        headless = os.getenv("CAMPUS_CHANNEL_HEADLESS", "true").lower() != "false"
        scrolls = self._safe_int(os.getenv("CAMPUS_CHANNEL_PLAYWRIGHT_SCROLLS", "6")) or 6
        wait_ms = self._safe_int(os.getenv("CAMPUS_CHANNEL_PLAYWRIGHT_WAIT_MS", "800")) or 800
        section_limit = self._safe_int(os.getenv("CAMPUS_CHANNEL_SECTION_SCAN_LIMIT", "20")) or 20
        launch_args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]

        def tag_section_text(text: str, section_name: str) -> str:
            if not section_name or section_name == "全部":
                return text
            time_pattern = r"(?=(?:刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+)"
            return re.sub(time_pattern, f"版块：{section_name} ", text)

        collected_texts: list[str] = []
        scan_sections = ["全部"] + SECTION_NAMES[:max(section_limit - 1, 0)]
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, args=launch_args)
            page = browser.new_page(user_agent=self.user_agent, viewport={"width": 1365, "height": 1800})
            try:
                response = page.goto(channel_url, wait_until="domcontentloaded", timeout=30000)
                if response and response.status in (401, 403):
                    raise RuntimeError("校园频道公开页面拒绝访问或需要登录，已停止采集")
                page.wait_for_timeout(wait_ms)
                first_text = page.locator("body").inner_text(timeout=8000)
                if any(token in first_text for token in ("请登录后查看", "登录后查看")):
                    raise RuntimeError("校园频道页面需要登录或限制访问，已停止采集")

                for section_name in scan_sections:
                    if section_name != "全部":
                        try:
                            page.get_by_text(section_name, exact=True).first.click(timeout=2500)
                            page.wait_for_timeout(wait_ms)
                        except Exception as exc:
                            logger.debug(f"【校园频道】版块 {section_name} 点击失败，跳过: {exc}")
                            continue

                    stable_rounds = 0
                    last_text = ""
                    for round_index in range(max(scrolls, 1)):
                        try:
                            body_text = page.locator("body").inner_text(timeout=8000)
                        except Exception:
                            body_text = ""
                        if body_text:
                            collected_texts.append(tag_section_text(body_text, section_name))
                        if round_index == max(scrolls, 1) - 1:
                            break

                        page.evaluate("""
                            () => {
                                const scrollables = [...document.querySelectorAll('*')]
                                  .filter(el => el.scrollHeight > el.clientHeight + 100)
                                  .sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
                                if (scrollables[0]) {
                                  scrollables[0].scrollTop += Math.max(scrollables[0].clientHeight, 900);
                                }
                                window.scrollBy(0, 1200);
                            }
                        """)
                        page.mouse.wheel(0, 1200)
                        page.wait_for_timeout(wait_ms)
                        if body_text and body_text == last_text:
                            stable_rounds += 1
                        else:
                            stable_rounds = 0
                        last_text = body_text
                        if stable_rounds >= 2:
                            break

                collected_texts.append(page.content())
                return "\n\n".join(dict.fromkeys(collected_texts))
            finally:
                browser.close()

    def _fetch_detail_with_playwright(self, post_url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("后端环境未安装 playwright，无法使用浏览器渲染详情页") from exc
        headless = os.getenv("CAMPUS_CHANNEL_HEADLESS", "true").lower() != "false"
        wait_ms = self._safe_int(os.getenv("CAMPUS_CHANNEL_PLAYWRIGHT_WAIT_MS", "900")) or 900
        launch_args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, args=launch_args)
            page = browser.new_page(user_agent=self.user_agent, viewport={"width": 1365, "height": 1800})
            try:
                response = page.goto(post_url, wait_until="domcontentloaded", timeout=25000)
                if response and response.status in (401, 403):
                    raise RuntimeError("帖子详情页拒绝访问或需要登录")
                page.wait_for_timeout(wait_ms * 2)
                try:
                    page.get_by_text("展开", exact=True).first.click(timeout=1200)
                    page.wait_for_timeout(wait_ms)
                except Exception:
                    pass
                return page.locator("body").inner_text(timeout=8000) + "\n" + page.content()
            finally:
                browser.close()

    def _extract_channel_name(self, html_text: str) -> str:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
        if title_match:
            title = self._clean_text(title_match.group(1))
            title = re.sub(r"[-_].*$", "", title).strip()
            if title:
                return re.split(r"[｜|]", title, maxsplit=1)[0].strip() or title
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
            raw_time = item.get("publish_time") or item.get("time") or ""
            publish_time_text = self._clean_text(item.get("publish_time_text") or self._format_publish_time_text(str(raw_time)) or raw_time)
            publish_time = raw_time if isinstance(raw_time, datetime) else self._parse_publish_time(str(raw_time) or publish_time_text)
            post_url = self._clean_text(item.get("post_url") or item.get("url") or "")
            post_id = self._clean_text(str(item.get("post_id") or item.get("id") or ""))
            images = item.get("images") if include_images else []
            if include_images:
                images = list(dict.fromkeys((images or []) + (item.get("gifs") or []) + (item.get("videos") or [])))
            if not isinstance(images, list):
                images = []
            raw = self._json_safe(item if isinstance(item, dict) else {})
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

        for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_text, re.I | re.S):
            script = html.unescape(match.group(1) or "").strip()
            try:
                data = json.loads(script)
            except Exception as exc:
                logger.debug(f"【校园频道】JSON-LD 解析失败: {exc}")
                continue
            items.extend(self._extract_schema_posts(data))

        for match in re.finditer(r"<script[^>]*>(.*?)</script>", html_text, re.I | re.S):
            script = html.unescape(match.group(1) or "")
            if not any(token in script for token in ("SocialMediaPosting", "content", "post", "feed", "author", "topic")):
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

    def _extract_schema_posts(self, data: Any) -> list[dict[str, Any]]:
        posts: list[dict[str, Any]] = []

        def walk(node: Any):
            if isinstance(node, dict):
                if node.get("@type") == "SocialMediaPosting":
                    normalized = self._normalize_schema_post(node)
                    if normalized:
                        posts.append(normalized)
                for key in ("@graph", "itemListElement", "item", "mainEntity", "hasPart"):
                    if key in node:
                        walk(node[key])
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)
        return posts

    def _normalize_schema_post(self, post_data: dict[str, Any]) -> dict[str, Any] | None:
        title = self._clean_text(post_data.get("headline") or post_data.get("name") or "")
        content = self._clean_text(post_data.get("articleBody") or post_data.get("text") or post_data.get("description") or "")
        if not content:
            content = title
        if not title:
            title = self._derive_title(content)
        if len(f"{title}{content}".strip()) < 8:
            return None

        author_info = post_data.get("author") or {}
        author_name = author_info.get("name", "") if isinstance(author_info, dict) else str(author_info or "")
        interaction = post_data.get("interactionStatistic") or []
        like_count = comment_count = share_count = 0
        if isinstance(interaction, dict):
            interaction = [interaction]
        if isinstance(interaction, list):
            for stat in interaction:
                if not isinstance(stat, dict):
                    continue
                interaction_type = str(stat.get("interactionType") or "").lower()
                count = self._safe_int(stat.get("userInteractionCount") or stat.get("interactionCount"))
                if "comment" in interaction_type:
                    comment_count = count
                elif "share" in interaction_type:
                    share_count = count
                elif "like" in interaction_type or not interaction_type:
                    like_count = count

        images = self._normalize_media_list(post_data.get("image"))
        videos = self._normalize_video_list(post_data.get("video"))
        gifs = self._normalize_media_list(post_data.get("gif"))
        post_url = self._clean_text(post_data.get("url") or "")
        post_id = self._extract_post_id(post_url)
        date_published = self._clean_text(post_data.get("datePublished") or "")
        section_name = self._infer_section({"url": post_url}, f"{title} {content}")

        return {
            "id": post_id,
            "title": title,
            "content": content,
            "author": self._clean_text(author_name),
            "time": date_published,
            "publish_time": self._parse_publish_time(date_published),
            "publish_time_text": self._format_publish_time_text(date_published),
            "section": section_name,
            "like_count": like_count,
            "comment_count": comment_count,
            "share_count": share_count,
            "url": post_url,
            "images": images,
            "videos": videos,
            "gifs": gifs,
            "raw": post_data,
        }

    @staticmethod
    def _normalize_media_list(value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            for key in ("url", "contentUrl", "thumbnailUrl"):
                if value.get(key):
                    return [str(value[key])]
            return []
        if isinstance(value, list):
            items: list[str] = []
            for item in value:
                items.extend(QQChannelScraper._normalize_media_list(item))
            return list(dict.fromkeys(items))
        return []

    @staticmethod
    def _normalize_video_list(value: Any) -> list[str]:
        return QQChannelScraper._normalize_media_list(value)

    @staticmethod
    def _extract_post_id(post_url: str) -> str:
        if not post_url:
            return ""
        path = urlparse(post_url).path.rstrip("/")
        return path.rsplit("/", 1)[-1] if "/" in path else path

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

        chunks = re.split(r"(?=(?:刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+)", text)
        items = []
        for chunk in chunks:
            chunk = self._clean_text(chunk)
            if len(chunk) < 20:
                continue
            if "登录后加入频道即可发帖" in chunk or "不选择版块 发表 全部" in chunk:
                continue
            if not self._extract_time_text(chunk):
                continue
            section_from_marker = ""
            marker_match = re.match(r"^(?P<prefix>(?:刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+)版块：(?P<section>[^\s]+)\s+(?P<body>.+)$", chunk)
            if marker_match:
                section_from_marker = marker_match.group("section")
                chunk = marker_match.group("prefix") + marker_match.group("body")
            parsed = self._parse_visible_post(chunk)
            if not parsed:
                parsed = {"content": self._trim_visible_chunk(chunk), "time": self._extract_time_text(chunk)}
            if section_from_marker:
                parsed["section"] = section_from_marker
            content = self._clean_text(parsed.get("content", ""))
            if len(content) < 8:
                continue
            parsed["content"] = content[:1200]
            parsed.setdefault("title", self._derive_title(content))
            parsed.setdefault("time", self._extract_time_text(chunk))
            items.append(parsed)
        return items

    def _enrich_posts_from_public_detail(self, posts: list[CampusChannelPostCreate], include_images: bool) -> list[CampusChannelPostCreate]:
        if str(os.getenv("CAMPUS_CHANNEL_FETCH_DETAILS", "true")).lower() not in {"true", "1", "yes"}:
            return posts
        max_details = self._safe_int(os.getenv("CAMPUS_CHANNEL_DETAIL_LIMIT", "20")) or 20
        max_comment_details = self._safe_int(os.getenv("CAMPUS_CHANNEL_COMMENT_DETAIL_LIMIT", "5")) or 5
        comment_detail_count = 0
        enriched: list[CampusChannelPostCreate] = []
        for index, post in enumerate(posts):
            if index >= max_details or not post.post_url:
                enriched.append(post)
                continue
            try:
                detail_html = self._fetch_public_html(post.post_url)
                detail = self._extract_detail_fields(detail_html, include_images=include_images)
                if detail.get("comment_count", 0) and not detail.get("comments") and comment_detail_count < max_comment_details:
                    try:
                        rendered_detail_html = self._fetch_detail_with_playwright(post.post_url)
                        rendered_detail = self._extract_detail_fields(rendered_detail_html, include_images=include_images)
                        detail.update({k: v for k, v in rendered_detail.items() if v})
                        comment_detail_count += 1
                    except Exception as exc:
                        logger.debug(f"【校园频道】渲染详情评论失败 post={post.post_id}: {exc}")
                if detail:
                    updated = post.model_copy(deep=True)
                    if detail.get("content") and len(detail["content"]) > len(updated.content or ""):
                        updated.content = detail["content"]
                        updated.summary = self._summarize(updated.content)
                    if detail.get("title") and len(detail["title"]) > len(updated.title or ""):
                        updated.title = detail["title"][:512]
                    if detail.get("view_count") is not None:
                        updated.view_count = detail["view_count"]
                    if detail.get("comment_count") is not None:
                        updated.comment_count = detail["comment_count"]
                    if detail.get("like_count") is not None and not updated.like_count:
                        updated.like_count = detail["like_count"]
                    if include_images and detail.get("images"):
                        updated.images = list(dict.fromkeys((updated.images or []) + detail["images"]))
                    raw = dict(updated.raw_data or {})
                    raw.update({k: v for k, v in detail.items() if k in {"comments", "detail_text"}})
                    updated.raw_data = raw
                    enriched.append(updated)
                else:
                    enriched.append(post)
            except Exception as exc:
                logger.debug(f"【校园频道】详情补全失败 post={post.post_id}: {exc}")
                enriched.append(post)
        return enriched

    def _extract_detail_fields(self, html_text: str, include_images: bool) -> dict[str, Any]:
        clean_text = self._clean_text(re.sub(r"<script.*?</script>|<style.*?</style>", " ", html_text, flags=re.I | re.S))
        clean_text = self._clean_text(re.sub(r"<[^>]+>", " ", html.unescape(clean_text)))
        result: dict[str, Any] = {"detail_text": clean_text[:3000]}
        title_match = re.search(r"加入频道\s+(?:\d+/\d+\s+)?(?P<author>\S{1,40})?\s*(?P<body>.+?)\s+(?P<date>20\d{2}-\d{2}-\d{2})\s+浏览", clean_text)
        if title_match:
            body = self._clean_text(title_match.group("body"))
            body = re.sub(r"^(复制图片\s*)+", "", body).strip()
            if body:
                result["content"] = body
                result["title"] = self._derive_title(body)
        view_match = re.search(r"浏览\s*(\d+)", clean_text)
        if view_match:
            result["view_count"] = self._safe_int(view_match.group(1))
        comment_count_match = re.search(r"评论\s*(\d+)", clean_text)
        if comment_count_match:
            result["comment_count"] = self._safe_int(comment_count_match.group(1))
        # Detail pages expose a small public comment preview between 热门 and 暂无更多评论.
        comments: list[dict[str, Any]] = []
        comment_area_match = re.search(r"热门\s+(?P<comments>.+?)\s+-\s*暂无更多评论", clean_text)
        if comment_area_match:
            comment_text = self._clean_text(comment_area_match.group("comments"))
            for part in re.split(r"(?=(?:刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+)", comment_text):
                part = self._clean_text(part)
                m = re.match(r"(?P<time>刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+(?P<content>.+?)(?:\s+\d+\s+回复)?$", part)
                if m and len(m.group("content")) >= 2:
                    comments.append({"time": m.group("time"), "content": m.group("content")[:300]})
        if comments:
            result["comments"] = comments
        if include_images:
            image_urls = re.findall(r"https?://(?:channel|channelr|qqchannel-profile)[^\"'\s<>]+", html_text)
            image_urls = [url for url in image_urls if not url.endswith('.svg') and 'share-logo' not in url and 'qqchannel-profile' not in url]
            if image_urls:
                result["images"] = list(dict.fromkeys(html.unescape(url) for url in image_urls))[:20]
        return result

    def _filter_posts(
        self,
        posts: list[CampusChannelPostCreate],
        section: str | None,
        keyword: str | None,
        since_days: int | None,
    ) -> list[CampusChannelPostCreate]:
        now = datetime.now()
        since_time = now - timedelta(days=since_days) if since_days else None
        result = []
        for post in posts:
            if section and section != "全部" and section not in (post.section_name or ""):
                continue
            if keyword:
                haystack = f"{post.title}\n{post.content}\n{post.summary}\n{post.author_name}"
                if keyword.lower() not in haystack.lower():
                    continue
            if since_time and post.publish_time:
                publish_time = self._normalize_datetime(post.publish_time)
                if publish_time and publish_time < since_time:
                    continue
            result.append(post)
        return result

    @staticmethod
    def _trim_visible_chunk(chunk: str) -> str:
        chunk = re.sub(r"^(刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+", "", chunk).strip()
        chunk = re.split(r"\s+(?:点赞|评论|分享)\b", chunk, maxsplit=1)[0].strip()
        return chunk

    @staticmethod
    def _parse_visible_post(chunk: str) -> dict[str, Any] | None:
        time_match = re.match(r"^(?P<time>刚刚|昨天|前天|\d+\s*(?:分钟前|小时前|天前|周前|月前))\s+(?P<rest>.+)$", chunk)
        if not time_match:
            return None
        publish_text = time_match.group("time")
        rest = time_match.group("rest").strip()

        interaction_part = ""
        body = rest
        marker = re.search(r"\s+(点赞|评论|分享)\b", rest)
        if marker:
            body = rest[:marker.start()].strip()
            interaction_part = rest[marker.start():]
        else:
            tail = re.match(r"(?P<body>.+?)\s+(?P<like>\d+)\s+(?P<comment>\d+)\s+(?P<share>\d+)\s+(?P<author>[^\s]{1,40})$", rest)
            if tail:
                body = tail.group("body").strip()
                return {
                    "content": body,
                    "title": body[:80],
                    "time": publish_text,
                    "like_count": int(tail.group("like")),
                    "comment_count": int(tail.group("comment")),
                    "share_count": int(tail.group("share")),
                    "author": tail.group("author"),
                }

        if not body or len(body) < 8:
            return None
        numbers = [int(x) for x in re.findall(r"\b\d+\b", interaction_part)[:3]]
        author = ""
        author_match = re.search(r"\b(?:点赞|评论|分享)\b.*?(?:\d+\s+){1,3}([^\s]{1,40})$", interaction_part)
        if author_match:
            author = author_match.group(1)
        return {
            "content": body,
            "title": body[:80],
            "time": publish_text,
            "like_count": numbers[0] if len(numbers) > 0 else 0,
            "comment_count": numbers[1] if len(numbers) > 1 else 0,
            "share_count": numbers[2] if len(numbers) > 2 else 0,
            "author": author,
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
        keyword_sections = [
            ("失物招领|寻物启事", ("丢", "捡", "失物", "寻物", "遗失", "找", "不见")),
            ("二手交易", ("出", "收", "二手", "转让", "闲置", "电动车", "价格", "元")),
            ("赛事组队", ("组队", "比赛", "竞赛", "队友", "招募")),
            ("期末｜资料共享", ("资料", "期末", "复习", "真题", "答案")),
            ("学习交流", ("图书馆", "自习", "课程", "学习", "考试")),
            ("通知", ("通知", "公告", "报名", "截止", "安排")),
        ]
        for section, keywords in keyword_sections:
            if any(keyword in content for keyword in keywords):
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
        if re.match(r"^\d{4}-\d{2}-\d{2}T", value):
            try:
                return QQChannelScraper._normalize_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
            except ValueError:
                pass
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
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        """Use timezone-naive local datetimes for DB storage and comparisons."""
        if not value:
            return None
        if value.tzinfo is not None:
            return value.astimezone().replace(tzinfo=None)
        return value

    @staticmethod
    def _json_safe(value: Any) -> Any:
        try:
            return json.loads(json.dumps(value, ensure_ascii=False, default=str))
        except Exception:
            return {}

    @staticmethod
    def _format_publish_time_text(value: str) -> str:
        parsed = QQChannelScraper._parse_publish_time(value)
        if not parsed:
            return value or ""
        now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
        delta = now - parsed
        if delta.total_seconds() < 60:
            return "刚刚"
        if delta.total_seconds() < 3600:
            return f"{max(int(delta.total_seconds() // 60), 1)}分钟前"
        if delta.total_seconds() < 86400:
            return f"{max(int(delta.total_seconds() // 3600), 1)}小时前"
        if delta.days < 30:
            return f"{delta.days}天前"
        return parsed.strftime("%Y-%m-%d %H:%M")

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
