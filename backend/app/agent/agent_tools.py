import contextvars
import datetime
import json
import os
from pathlib import Path
from typing import List

from langchain_core.tools import tool

from app.core.logger_handler import logger
from app.db.db_config import AsyncSessionLocal
from app.rag.rag_service import RagService
from app.rag.reorder_service import reorder_service
from app.schemas.models import ScheduleEventCreate
from app.services.campus_location_service import (
    build_map_url,
    find_best_location,
    list_campus_locations,
    search_campus_locations as cl_search,
)
from app.services.schedule_ai_service import parse_schedule_items_from_text
from app.services.schedule_service import (
    create_event as svc_create_event,
    find_conflicts as svc_find_conflicts,
    list_week_events as svc_list_week_events,
)
from app.utils.auth_utils import decode_django_jwt

_current_user_id = contextvars.ContextVar("current_user_id", default="")


def set_agent_user_context(user_id: str):
    _current_user_id.set(user_id)

@tool(description="用于从向量数据库里检索文档并生成摘要，返回包含文档列表和摘要的结果。返回格式为：'摘要: [摘要内容]\n\n检索到的文档列表:\n1. [文档1内容]\n2. [文档2内容]\n...'。注意：文档已经过自动重排序，无需再调用重排序工具")
async def rag_summary_tools(query: str) -> str:
    """RAG 摘要工具"""
    result = await RagService().get_documents_and_summary(query)
    documents = result.get("documents", [])
    summary = result.get("summary", "")

    # 格式化返回结果
    formatted_result = f"摘要: {summary}\n\n"
    formatted_result += "检索到的文档列表（已重排序）:\n"
    for i, doc in enumerate(documents, 1):
        formatted_result += f"{i}. {doc}\n"  # 显示完整文档内容

    return formatted_result

@tool(description="用于对文档列表进行重排序，传入查询语句query和文档列表documents，返回重排序后的文档列表，包含文档内容和相似度。注意：rag_summary_tools已内置重排序功能，通常不需要单独调用此工具")
async def reorder_documents_tools(query: str, documents: List[str]) -> str:
    """重排序文档工具"""
    result = await reorder_service.reorder_documents(query, documents)
    if result["success"]:
        # 格式化返回结果
        formatted_result = await reorder_service.format_reorder_result(result["documents"])
        # 记录日志
        logger.info(formatted_result)
        return formatted_result
    else:
        return f"重排序失败: {result['error']}"

@tool(description="当用户明确问自己的ID和用户名时，从JWT中获取当前用户ID和用户名，参数为完整的JWT token字符串")
async def get_user_info_tools(token: str) -> str:
    """获取用户信息工具"""
    payload = decode_django_jwt(token)
    if payload:
        user_id = payload.get("user_id", "未知")
        user_name = payload.get("user_name", "未知")
        return f"用户信息：\n- 用户ID: {user_id}\n- 用户名: {user_name}"
    else:
        return "无法解析JWT token，无法获取用户信息"


@tool(description="用于获取天气信息，需要提供城市名称作为参数，你需要从用户输入中提取城市名称，是str类型")
async def get_weather_tools(city: str = None) -> str:
    """获取天气工具"""
    if not city:
        return "请提供城市名称"
    return f"【{city}】的天气是晴朗的"


@tool(description="用于获取当前年月日时分的工具")
async def what_time_is_now() -> str:
    """获取当前年月日时分的工具"""
    return f"当前时间是：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"


# ── Schedule tools ──────────────────────────────────────────────

@tool(description="查询当前用户整周课表，返回一周所有日程安排。无需参数。")
async def get_schedule_week() -> str:
    user_id = _current_user_id.get()
    if not user_id:
        return "无法获取用户身份，请重新登录。"
    async with AsyncSessionLocal() as db:
        events = await svc_list_week_events(db, user_id)
    if not events:
        return "当前课表还没有安排任何日程。"
    weekday_labels = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                      "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
    lines = []
    for e in events:
        wd = weekday_labels.get(e.weekday, e.weekday)
        date_part = f" ({e.date})" if e.date else ""
        loc = f" @{e.location}" if e.location else ""
        lines.append(f"- {wd}{date_part} {e.startTime}-{e.endTime} 【{e.title}】{loc}")
    return "整周课表：\n" + "\n".join(lines)


@tool(description="查询今日课表。无需参数，自动根据当前日期判断星期几并返回对应日程。")
async def get_schedule_today() -> str:
    user_id = _current_user_id.get()
    if not user_id:
        return "无法获取用户身份，请重新登录。"
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_labels = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                      "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
    today_wd = weekdays[datetime.datetime.now().weekday()]
    async with AsyncSessionLocal() as db:
        events = await svc_list_week_events(db, user_id)
    today_events = [e for e in events if e.weekday == today_wd]
    if not today_events:
        return f"{weekday_labels[today_wd]}暂无课程或日程安排。"
    lines = [f"- {e.startTime}-{e.endTime} 【{e.title}】{e.location or ''}" for e in today_events]
    return f"今日课表（{weekday_labels[today_wd]}）：\n" + "\n".join(lines)


@tool(description="创建一个新的日程/课表事件。title: 事件标题；weekday: 英文星期(Monday~Sunday)；start_time: 开始时间(HH:MM)；end_time: 结束时间(HH:MM)；location: 地点(可选)；date: 具体日期YYYY-MM-DD(可选)；repeat: 重复模式 none/weekly/daily(可选，默认none)；event_type: 类型 course/meeting/exam/study/activity/other(可选，默认other)")
async def create_schedule_event(
    title: str,
    weekday: str,
    start_time: str,
    end_time: str,
    location: str = "",
    date: str = "",
    repeat: str = "none",
    event_type: str = "other",
) -> str:
    user_id = _current_user_id.get()
    if not user_id:
        return "无法获取用户身份，请重新登录。"

    payload = ScheduleEventCreate(
        title=title,
        type=event_type,
        date=date,
        weekday=weekday,
        startTime=start_time,
        endTime=end_time,
        location=location,
        teacher="",
        repeat=repeat,
        source="ai_agent",
        remark="由 AI Agent 添加",
    )

    async with AsyncSessionLocal() as db:
        conflicts = await svc_find_conflicts(db, user_id, weekday, start_time, end_time)
        conflict_info = ""
        if conflicts:
            conflict_list = "；".join(f"【{c.title}】{c.startTime}-{c.endTime}" for c in conflicts)
            conflict_info = f"\n⚠ 时间冲突提醒：{conflict_list}"

        event = await svc_create_event(db, user_id, payload)

    weekday_labels = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                      "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
    wd_label = weekday_labels.get(event.weekday, event.weekday)
    result = f"已添加：【{event.title}】{wd_label} {event.startTime}-{event.endTime}"
    if event.location:
        result += f" @{event.location}"
    result += conflict_info
    return result


# ── Campus tools ────────────────────────────────────────────────

@tool(description="搜索校园地点。keyword: 地点名称关键词，如'图书馆'、'食堂'、'教学楼'。返回匹配的地点列表。")
async def search_campus_locations_tool(keyword: str) -> str:
    results = cl_search(keyword, limit=10)
    if not results:
        return f"未找到与「{keyword}」相关的校园地点，请用更准确的名称重试。"
    lines = [f"- {r['name']}（{r['address']}）{r['description']}" for r in results]
    return "找到以下地点：\n" + "\n".join(lines)


@tool(description="规划两个校园地点之间的步行路线。from_location: 起点名称；to_location: 终点名称。")
async def get_campus_route(from_location: str, to_location: str) -> str:
    start = find_best_location(from_location)
    target = find_best_location(to_location)
    if not start:
        return f"未找到起点「{from_location}」，请提供更准确的地点名称（如：图书馆、第一教学楼、食堂）。"
    if not target:
        return f"未找到终点「{to_location}」，请提供更准确的地点名称（如：图书馆、第一教学楼、食堂）。"
    map_url = build_map_url(target, start, show_route=True)
    return (
        f"从【{start.name}】到【{target.name}】的步行路线：\n"
        f"起点：{start.address}\n"
        f"终点：{target.address}（{target.description}）\n"
        f"[查看站内地图导航]({map_url})"
    )


# ── Training program & course tools ─────────────────────────────

@tool(description="从培养方案知识库中检索信息。query: 查询内容，如'计算机专业的毕业要求'、'高等数学的学分'、'通识选修课列表'等。")
async def get_training_program(query: str) -> str:
    try:
        result = await RagService().rag_summary_with_sources(query)
        answer = result.get("answer") or result.get("response") or ""
        sources = result.get("sources") or []
        if sources:
            src_names = ", ".join(s.get("doc_name", s.get("file_name", "")) for s in sources[:5])
            return f"{answer}\n\n📚 参考来源：{src_names}"
        return answer or "未找到相关的培养方案信息。"
    except Exception as e:
        logger.warning(f"培养方案检索失败: {e}")
        return f"检索培养方案时出现错误，请稍后重试。"


@tool(description="根据策略推荐选修课程。strategy: 推荐策略，可选值：'全面发展'、'专业深入'、'实践为主'、'学分优先'。")
async def recommend_courses(strategy: str = "全面发展") -> str:
    query = f"请根据「{strategy}」的选课策略，推荐合适的选修课程。需要考虑培养方案的学分要求、课程难度梯度、先修要求。"
    try:
        result = await RagService().rag_summary_with_sources(query)
        answer = result.get("answer") or result.get("response") or "暂时无法生成推荐，请提供更详细的偏好（如感兴趣的方向）。"
        return f"选课建议（策略：{strategy}）：\n{answer}"
    except Exception as e:
        logger.warning(f"选课推荐失败: {e}")
        return f"生成选课推荐时出现错误，请稍后重试。"


# ── FAQ recommendations tool ────────────────────────────────────

@tool(description="""推荐高频相关问题。
- query 为空时返回全部 FAQ（置顶优先）
- query 非空时返回语义相似的高频问题列表
当用户提问模糊、对话刚开始、或 RAG 检索无结果时调用。""")
async def faq_recommend(query: str = "") -> str:
    try:
        from app.router.faq import _load_faq
        faq = _load_faq()
        all_questions = faq.get("questions", [])

        if not query or not query.strip():
            all_questions.sort(key=lambda q: (not q.get("pinned", False), q.get("sort", 99)))
            items = all_questions[:8]
        else:
            matched = []
            q_chars = set(query.replace(" ", ""))
            for q in all_questions:
                q_text = q.get("question", "").replace(" ", "")
                common = len(q_chars & set(q_text))
                if common > 1:
                    matched.append((common, q))
            matched.sort(key=lambda x: (not x[1].get("pinned", False), -x[0], x[1].get("sort", 99)))
            items = [q for _, q in matched[:5]]
            if not items:
                items = [q for q in all_questions if q.get("pinned")][:5]

        return json.dumps({
            "type": "faq_recommendations",
            "title": "你可能想问：" if query else "常见问题",
            "questions": items,
        }, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"faq_recommend failed: {e}")
        return "暂时无法加载常见问题。"


# ── Document generation tool ──────────────────────────────────────

_DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", "/app/documents"))
_DOCUMENTS_TEMP_DIR = Path(os.getenv("DOCUMENTS_TEMP_DIR", "/tmp/documents"))

_FIELD_LABELS = {
    "name": "姓名", "student_id": "学号", "class_name": "班级",
    "reason": "原因", "start_date": "开始日期", "end_date": "结束日期",
    "start_time": "开始时间", "end_time": "结束时间", "duration_days": "请假天数",
    "teacher_name": "教师姓名", "recipient_type": "收件人类型", "course_name": "课程名称",
    "student_phone": "本人电话", "parent_phone": "家长电话",
    "signature": "签名", "sign_date": "签字日期",
    "destination": "去向", "relative_relation": "亲属关系", "relative_phone": "亲属电话",
    "phone": "离校期间电话", "leave_start": "离校时间", "leave_end": "返校时间",
    "total_days": "共几天", "student_name": "姓名",
}


def _field_label(key: str) -> str:
    return _FIELD_LABELS.get(key, key)


async def _extract_faq_from_documents() -> list[dict]:
    """Extract FAQ questions from indexed student handbook docs via LLM."""
    import uuid
    try:
        from app.rag.vector_store import VectorStoreService
        store = VectorStoreService()
        all_docs = await store._get_all_documents("shared")
        if not all_docs:
            return []
        text = "\n\n".join(d.page_content[:500] for d in all_docs[:20])
        summary = text[:3000]
    except Exception:
        return []

    try:
        from langchain_community.chat_models import ChatTongyi
        llm = ChatTongyi(model="qwen3-max")
        prompt = (
            "从以下校园办事指南内容中，提取 5-10 个学生最常问的高频问题。"
            "每个问题应该简洁明确（15字以内），覆盖文档中提到的不同事务。"
            "只返回问题列表，每行一个问题，不要加序号，不要加其他内容。\n\n"
            f"{summary}"
        )
        response = await llm.ainvoke(prompt)
        lines = [line.strip() for line in response.content.split("\n") if line.strip()]
        questions = []
        for i, line in enumerate(lines):
            line = line.lstrip("0123456789.、) ）")
            if len(line) > 5:
                questions.append({
                    "id": f"faq_{uuid.uuid4().hex[:8]}",
                    "question": line[:80],
                    "category": "",
                    "pinned": False,
                    "sort": (i + 1) * 10,
                })
        return questions
    except Exception as e:
        logger.warning(f"FAQ extraction failed: {e}")
        return []


def _load_fields_config(doc_type: str) -> dict:
    fields_path = _DOCUMENTS_DIR / doc_type / "fields.json"
    if not fields_path.exists():
        return {}
    return json.loads(fields_path.read_text(encoding="utf-8"))


def _match_document_type(query: str) -> tuple:
    """RAG-match query to document type. Returns (doc_type | None, spec_snippet | None)."""
    try:
        from app.rag.vector_store import document_spec_store
        results = document_spec_store.search(query, k=3)
        if results and len(results) > 0 and results[0].get("score", 0) > 0.4:
            metadata = results[0].get("metadata", {})
            doc_type = metadata.get("document_type", "")
            snippet = results[0].get("text", "")[:400]
            # Strip markdown headers and frontmatter to leave only readable text
            import re
            snippet = re.sub(r'^---\s*\n.*?\n---\s*\n?', '', snippet, flags=re.DOTALL)
            snippet = re.sub(r'^#{1,4}\s+', '', snippet, flags=re.MULTILINE)
            snippet = snippet.strip()
            return doc_type, snippet
    except Exception:
        pass
    return None, None


def _resolve_relative_date(text: str) -> str:
    """Resolve relative dates like '明天', '今天', '下周一' to YYYY-MM-DD."""
    import re
    today = datetime.date.today()
    weekdays_cn = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}

    text = text.strip()

    # Exact date patterns
    for pattern in [r'(\d{4}-\d{2}-\d{2})', r'(\d{4}年\d{1,2}月\d{1,2}日)', r'(\d{1,2}月\d{1,2}日)']:
        m = re.search(pattern, text)
        if m:
            d = m.group(1)
            if '-' in d:
                return d
            d = d.replace('年', '-').replace('月', '-').replace('日', '')
            parts = d.split('-')
            if len(parts) == 2:
                return f"{today.year}-{int(parts[0]):02d}-{int(parts[1]):02d}"
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"

    # Relative day: 今天/明天/后天/昨天
    if '今天' in text:
        return today.strftime("%Y-%m-%d")
    if '明天' in text or '明日' in text:
        return (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if '后天' in text or '後天' in text:
        return (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    if '昨天' in text:
        return (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # 下周X / 下周一
    m = re.search(r'下周(.)', text)
    if m:
        target = weekdays_cn.get(m.group(1))
        if target is not None:
            days_ahead = target - today.weekday() + 7
            if days_ahead <= 7:
                days_ahead += 7
            return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # 本周X / 周X
    m = re.search(r'(?:本周)?(周.)', text)
    if m:
        target = weekdays_cn.get(m.group(1))
        if target is not None:
            days_ahead = target - today.weekday()
            if days_ahead < 0:
                days_ahead += 7
            return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return ""


def _resolve_template_name(fields_config: dict, variant: str, recipient_type: str = "") -> str:
    """Pick the right template file based on variant and sub-variant."""
    variants = fields_config.get("variants", {})
    vcfg = variants.get(variant, {})
    template = vcfg.get("template", "template.docx")
    sub_variants = vcfg.get("sub_variants", {})
    if sub_variants and recipient_type:
        for sv_key, sv_cfg in sub_variants.items():
            if sv_key == recipient_type or recipient_type == sv_key:
                template = sv_cfg.get("template", template)
                break
    return template


async def _lookup_schedule_for_leave(user_id: str, params: dict) -> list[dict]:
    """Query user's schedule to auto-detect courses matching the leave time."""
    if not user_id:
        return []
    try:
        async with AsyncSessionLocal() as db:
            events = await svc_list_week_events(db, user_id)
    except Exception:
        return []

    if not events:
        return []

    target_date = params.get("start_date", "")
    target_weekday = params.get("_weekday", "")

    matches = []
    for e in events:
        if target_date and e.date and str(e.date) == target_date:
            matches.append(e)
        elif target_weekday and e.weekday == target_weekday:
            matches.append(e)

    if not matches:
        return []

    weekday_labels = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                      "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
    return [{
        "course_name": e.title,
        "teacher_name": e.teacher or "",
        "start_date": str(e.date) if e.date else "",
        "end_date": str(e.date) if e.date else "",
        "start_time": e.startTime,
        "end_time": e.endTime,
        "weekday": weekday_labels.get(e.weekday, e.weekday),
        "location": e.location or "",
    } for e in matches]


@tool(description="""通用文书生成工具。根据对话生成校园文书（请假条等）。

课程请假时会自动查用户课表来补全课程名称、教师、时间等信息。

工作方式：
1. 首次调用: 从用户消息中提取已有字段值，调用 doc_preview(query=用户原文, params={已提取字段...}) → 返回预览JSON
2. 用户确认后: doc_preview(query=用户原文, confirmed=True, params={完整字段, _doc_type, _variant, _recipient_type})

你必须在第一次调用后等待用户确认，不要跳过确认步骤。
如果用户使用相对日期（如"明天""下周一"），先调用 what_time_is_now 获取当前日期再解析。""")
async def doc_preview(
    query: str,
    confirmed: bool = False,
    params: dict = None,
) -> str:
    import uuid

    if params is None:
        params = {}
    user_id = _current_user_id.get()

    # ── Phase 2: Generate ──
    if confirmed and params:
        doc_type = params.pop("_doc_type", None)
        variant = params.pop("_variant", None)
        recipient_type = params.pop("_recipient_type", params.get("recipient_type", ""))
        if not doc_type:
            doc_type, _ = _match_document_type(query)
        # Guard: if doc_type doesn't match a known spec, re-match via RAG
        fields_config = _load_fields_config(doc_type) if doc_type else {}
        if not fields_config:
            doc_type, _ = _match_document_type(query)
            fields_config = _load_fields_config(doc_type) if doc_type else {}
        if not doc_type or not fields_config:
            return "无法确定文书类型，请重新描述你的需求。"

        required = list(fields_config.get("required", []))

        if variant and "variants" in fields_config:
            vcfg = fields_config["variants"].get(variant, {})
            required = required + vcfg.get("required", [])

        missing = [f for f in required if not params.get(f)]
        if missing:
            labels = [_field_label(f) for f in missing]
            return f"以下必填字段缺失：{'、'.join(labels)}。请补充后重新确认。"

        template_name = _resolve_template_name(fields_config, variant, recipient_type)

        from app.services.document_generator import DocumentGenerator
        gen = DocumentGenerator(_DOCUMENTS_DIR, _DOCUMENTS_TEMP_DIR)
        output_path = gen.generate(doc_type, params, template_name=template_name)
        file_id = output_path.stem
        file_size = output_path.stat().st_size
        size_str = f"{file_size / 1024:.1f} KB" if file_size > 1024 else f"{file_size} B"

        return json.dumps({
            "type": "document_result",
            "doc_type": doc_type,
            "display_name": fields_config.get("display_name", doc_type),
            "file_name": f"{file_id}.docx",
            "file_size": size_str,
            "download_url": f"/api/documents/download/{file_id}",
            "expires_in": "30 分钟",
        }, ensure_ascii=False)

    # ── Phase 1: Preview ──
    doc_type, spec_snippet = _match_document_type(query)
    if not doc_type:
        available = ["请假条"]
        return f"暂不支持该文书类型。目前支持：{'、'.join(available)}。"

    fields_config = _load_fields_config(doc_type)
    if not fields_config:
        return f"文书类型「{doc_type}」的字段配置缺失，请联系管理员。"

    auto_fill_keys = fields_config.get("auto_fill", [])
    required_keys = list(fields_config.get("required", []))
    optional_keys = list(fields_config.get("optional", []))

    # Determine variant (LLM choice or default)
    variant = params.get("variant", "") or params.get("_variant", "")
    variant_label = ""
    if not variant and "variants" in fields_config:
        variant = next(iter(fields_config["variants"].keys()))
    vcfg = fields_config.get("variants", {}).get(variant, {})
    variant_label = vcfg.get("label", variant)
    required_keys = required_keys + vcfg.get("required", [])
    optional_keys = optional_keys + vcfg.get("optional", [])

    # ── Resolve relative dates ──
    for date_key in ["start_date", "end_date", "leave_start", "leave_end"]:
        raw_val = params.get(date_key, "")
        if raw_val:
            resolved = _resolve_relative_date(raw_val)
            if resolved:
                params[date_key] = resolved
        # Also try extracting from query if key is missing
        if not params.get(date_key):
            resolved = _resolve_relative_date(query)
            if resolved:
                params[date_key] = resolved

    # ── Auto-fill from Django ──
    auto_filled = []
    if user_id and auto_fill_keys:
        try:
            from app.utils.django_user_client import fetch_user_profile
            profile = fetch_user_profile(user_id)
            if profile:
                for key in auto_fill_keys:
                    value = profile.get(key, "")
                    if value:
                        params[key] = value
                        auto_filled.append({"key": key, "label": _field_label(key), "value": str(value), "source": "account"})
        except Exception:
            pass

    # ── Auto-fill from schedule (course leave only) ──
    schedule_candidates = []
    schedule_filled = []
    if variant == "course_leave" and vcfg.get("auto_detect_from_schedule"):
        try:
            schedule_candidates = await _lookup_schedule_for_leave(user_id, params)
        except Exception:
            pass

    if schedule_candidates:
        if len(schedule_candidates) == 1:
            sc = schedule_candidates[0]
            for key in ["teacher_name", "course_name", "start_date", "end_date", "start_time", "end_time"]:
                val = sc.get(key, "")
                if val and not params.get(key):
                    params[key] = val
                    schedule_filled.append({"key": key, "label": _field_label(key), "value": str(val), "source": "schedule"})

    # ── Extract from LLM-provided params ──
    extracted = []
    for key in required_keys + optional_keys:
        if key in auto_fill_keys:
            continue
        if any(sf["key"] == key for sf in schedule_filled):
            continue
        val = params.get(key, "")
        if val:
            extracted.append({"key": key, "label": _field_label(key), "value": str(val)})

    # ── Missing ──
    already = {f["key"] for f in auto_filled} | {f["key"] for f in schedule_filled} | {f["key"] for f in extracted}
    missing = [{"key": k, "label": _field_label(k), "required": True} for k in required_keys if k not in already]

    hint = '回复"确认"生成文档，或回复补充信息' if missing else '回复"确认"生成文档，或回复修改'

    return json.dumps({
        "type": "document_preview",
        "doc_type": doc_type,
        "display_name": fields_config.get("display_name", doc_type),
        "variant": variant,
        "variant_label": variant_label,
        "fields": {
            "auto_filled": auto_filled,
            "schedule_filled": schedule_filled,
            "extracted": extracted,
            "missing": missing,
        },
        "schedule_candidates": schedule_candidates if len(schedule_candidates) > 1 else [],
        "spec_reference": spec_snippet or "",
        "hint": hint,
    }, ensure_ascii=False)