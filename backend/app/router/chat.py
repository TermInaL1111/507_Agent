import json
import re
from typing import List
import uuid

from fastapi.routing import APIRouter
from fastapi import UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.agent import get_agent_stream_response
from app.agent.agent_tools import set_agent_user_context
from app.utils.django_user_client import set_agent_jwt_token
from app.utils.auth_utils import security
from app.core.logger_handler import logger
from sqlalchemy import select

from app.db.db_config import AsyncSessionLocal
from app.models.chat_history import SourceFile
from app.router.chat_service import ChatService, get_router_service

from app.schemas.models import QueryRequest, RAGResponse, RAGRequest, SessionResponse, ReorderResponse, ReorderRequest, ScheduleEventCreate
from app.services.schedule_service import create_event as svc_create_event
from app.services.source_file_service import create_source_file_record
from app.services import session_manager as sm
from app.utils.auth_utils import get_current_user_id
from app.utils.file_handler import pdf_loader
from app.core.success_response import success_response
from app.core.rate_limit import rate_limit


chat_router = APIRouter(prefix="/api", tags=["api"])

# ── PDF 课表文本解析 ───────────────────────────────────────────

# 节次 → 实际时间映射 (中国高校标准作息)
_SECTION_TIMES = {
    ("1", "2"): ("08:00", "09:35"),
    ("3", "4"): ("10:05", "11:40"),
    ("5", "6"): ("14:00", "15:35"),
    ("7", "8"): ("16:05", "17:40"),
    ("9", "10"): ("19:00", "20:35"),
}

_WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
_WEEKDAY_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# 课表条目正则: 节次范围 课程名 * 详细参数(/分隔的key:value)
_COURSE_LINE_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})\s+"  # 节次范围 (如 1-2, 前面不能有数字)
    r"([^*]+?)"                               # 课程名 (到*之前)
    r"\*\s*"                                  # * 分隔符
    r"(.+?)"                                  # 详细参数
    r"(?=\n?\d{1,2}\s*-\s*\d{1,2}\s+|$)"     # 截止于下一门课或行尾
)

# 详情字段 key:value 解析
_DETAIL_KV_RE = re.compile(r"\s*/?\s*([^:：/]+)[:：]\s*([^/]*)")


def _time_to_minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


def _events_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    return _time_to_minutes(start_a) < _time_to_minutes(end_b) and _time_to_minutes(end_a) > _time_to_minutes(start_b)


def _format_schedule_conflict(uploaded: dict, existing_event) -> dict:
    return {
        "uploaded": {
            "title": uploaded.get("title", ""),
            "weekday": uploaded.get("weekday", ""),
            "startTime": uploaded.get("startTime", ""),
            "endTime": uploaded.get("endTime", ""),
            "location": uploaded.get("location", ""),
            "teacher": uploaded.get("teacher", ""),
        },
        "existing": {
            "id": existing_event.id,
            "title": existing_event.title,
            "weekday": existing_event.weekday,
            "startTime": existing_event.startTime,
            "endTime": existing_event.endTime,
            "location": existing_event.location,
            "teacher": existing_event.teacher,
        },
    }


def _section_to_time(section_start: str, section_end: str) -> tuple[str, str]:
    """节次号 → 实际时间，未知节次按递推估算。"""
    key = (section_start, section_end)
    if key in _SECTION_TIMES:
        return _SECTION_TIMES[key]
    s, e = int(section_start), int(section_end)
    if s >= 9:
        return (f"{18 + (s - 9) // 2:02d}:00", f"{18 + (e - 9) // 2:02d}:35")
    if s >= 5:
        return (f"{13 + s // 2:02d}:00", f"{13 + e // 2:02d}:35")
    return (f"{7 + s // 2:02d}:00", f"{7 + e // 2:02d}:35")


def _parse_detail_fields(detail_str: str) -> dict:
    """解析 '周数: 1-6周/校区: 未来城校区/地点: 公教2-304/教师: 万波/...' → dict"""
    fields = {}
    for m in _DETAIL_KV_RE.finditer(detail_str):
        key = m.group(1).strip()
        value = m.group(2).strip().rstrip("/")
        fields[key] = value
    return fields


def _parse_schedule_pdf_text(text: str) -> tuple[list[dict], str]:
    """解析教务系统导出的课表文本。
    支持格式: 星期X 节次 课程名*周数:.../校区:.../地点:.../教师:...
    """
    items: list[dict] = []
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # ── 预处理: 合并续行 ──
    # PDF 提取的文本中，长字段可能被切成多行。
    # 续行特征: 不以星期/节次/实践课程/其他课程/*: 开头
    _START_LINE_RE = re.compile(
        r"^(星期[一二三四五六日])"          # 星期头
        r"|^\d{1,2}\s*-\s*\d{1,2}\s+"     # 节次范围 (如 5-6 课程名)
        r"|^(实践课程|其他课程)[：:]"        # 特殊段
        r"|^\*:"                            # 脚注
    )
    raw_lines = text.split("\n")
    merged: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if merged and not _START_LINE_RE.match(stripped):
            merged[-1] = merged[-1] + stripped
        else:
            merged.append(stripped)

    # ── 按星期拆分 ──
    WEEKDAY_PATTERN = re.compile(
        r"^(星期[一二三四五六日])(?:\s+\d|\s*$|\s*\*)"  # 星期X 后跟空格+数字 或 行尾
    )
    _WD_START = re.compile(r"^(星期[一二三四五六日])")

    day_blocks: dict[str, str] = {}
    current_day = ""
    current_lines: list[str] = []

    for line in merged:
        wd_match = _WD_START.match(line)
        if wd_match:
            # 保存上一个 block
            if current_day and current_lines:
                day_blocks[current_day] = "\n".join(current_lines)
            current_day = _WEEKDAY_EN[_WEEKDAY_NAMES.index(wd_match.group(1))]
            # 去掉星期前缀，保留课程内容
            rest = line[wd_match.end():].strip()
            current_lines = [rest] if rest else []
        elif current_day:
            # 遇到实践课程/其他课程 → 结束当前 block
            if re.match(r"^(实践课程|其他课程)[：:]", line):
                if current_lines:
                    day_blocks[current_day] = "\n".join(current_lines)
                current_day = ""
                current_lines = []
            else:
                current_lines.append(line)

    if current_day and current_lines:
        day_blocks[current_day] = "\n".join(current_lines)

    # ── 解析每个星期的课程 ──
    for weekday_en, block in day_blocks.items():
        for m in _COURSE_LINE_RE.finditer(block):
            section_start = m.group(1)
            section_end = m.group(2)
            course_name = m.group(3).strip()
            detail_str = m.group(4).strip()

            start_time, end_time = _section_to_time(section_start, section_end)
            fields = _parse_detail_fields(detail_str)

            items.append({
                "title": course_name,
                "weekday": weekday_en,
                "startTime": start_time,
                "endTime": end_time,
                "location": fields.get("地点", ""),
                "teacher": fields.get("教师", ""),
                "weeks": fields.get("周数", ""),
                "campus": fields.get("校区", ""),
                "credits": fields.get("学分", ""),
                "assessment": fields.get("考核方式", ""),
                "remark": fields.get("选课备注", ""),
            })

    warning = ""
    if not items:
        warning = "未能识别出课表条目，请确认 PDF 为教务系统导出的文本格式课表（非图片扫描件）。"

    return items, warning


@chat_router.post("/agent/upload")
async def upload_schedule_pdf(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    _: None = Depends(rate_limit(limit=5, window=60)),
):
    """上传课表 PDF，自动解析并创建日程事件。"""
    # 1. 校验文件类型
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")
    if file.size and file.size > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 20MB")

    # 2. 保存文件
    source_file = await create_source_file_record(
        file=file, user_id=user_id, kb_type="personal", category="schedule"
    )
    logger.info(f"【课表上传】文件已保存: {source_file.file_id} ({source_file.original_filename})")

    # 3. 提取 PDF 文本
    file_path = source_file.file_path
    try:
        docs = await pdf_loader(file_path)
        full_text = "\n".join(doc.page_content for doc in docs)
    except Exception as e:
        logger.error(f"【课表上传】PDF 文本提取失败: {e}")
        raise HTTPException(status_code=422, detail=f"PDF 文本提取失败: {str(e)}")

    if not full_text.strip():
        return success_response(data={
            "file_id": source_file.file_id,
            "filename": source_file.original_filename,
            "text_preview": "",
            "events": [],
            "events_count": 0,
            "warning": "PDF 无可提取文本，可能是扫描版图片。请使用文本格式的 PDF（如教务系统导出）。",
        })

    # 4. 解析课表
    parsed_items, warning = _parse_schedule_pdf_text(full_text)

    # 5. 创建日程事件
    # Atomic import rule: if any parsed course conflicts with existing schedule,
    # do not import any rows from this PDF. This prevents re-uploading a mostly
    # duplicate timetable from silently restoring courses the user deleted.
    set_agent_user_context(user_id)
    created_events = []
    skipped = 0
    conflicts = []
    async with AsyncSessionLocal() as db:
        from app.services.schedule_service import list_week_events as svc_list_events

        existing = await svc_list_events(db, user_id)
        for item in parsed_items:
            overlapping = [
                e for e in existing
                if e.weekday == item["weekday"]
                and _events_overlap(item["startTime"], item["endTime"], e.startTime, e.endTime)
            ]
            conflicts.extend(_format_schedule_conflict(item, e) for e in overlapping)

        if conflicts:
            skipped = len(parsed_items)
            logger.info(
                f"【课表上传】检测到 {len(conflicts)} 条时间冲突，整份课表不导入: "
                f"{source_file.original_filename}"
            )
        else:
            for item in parsed_items:
                try:
                    payload = ScheduleEventCreate(
                        title=item["title"],
                        type="course",
                        weekday=item["weekday"],
                        startTime=item["startTime"],
                        endTime=item["endTime"],
                        location=item.get("location", ""),
                        date="",
                        teacher=item.get("teacher", ""),
                        repeat="weekly",
                        source="pdf_upload",
                        remark=item.get("remark", f"从 {source_file.original_filename} 导入"),
                    )
                    event = await svc_create_event(db, user_id, payload)
                    existing.append(event)
                    created_events.append({
                        "id": event.id,
                        "title": event.title,
                        "weekday": event.weekday,
                        "startTime": event.startTime,
                        "endTime": event.endTime,
                        "location": event.location,
                    })
                except Exception as e:
                    logger.warning(f"【课表上传】创建事件失败: {item} -> {e}")

    text_preview = full_text[:500] if len(full_text) > 500 else full_text
    return success_response(data={
        "file_id": source_file.file_id,
        "filename": source_file.original_filename,
        "text_preview": text_preview,
        "events": created_events,
        "events_count": len(created_events),
        "parsed_count": len(parsed_items),
        "duplicates_skipped": skipped,
        "conflicts_count": len(conflicts),
        "conflicts": conflicts,
        "warning": warning or None,
    })


def _weekday_label(weekday: str) -> str:
    return {
        "Monday": "周一",
        "Tuesday": "周二",
        "Wednesday": "周三",
        "Thursday": "周四",
        "Friday": "周五",
        "Saturday": "周六",
        "Sunday": "周日",
    }.get(weekday, weekday or "未知星期")


def _looks_like_uploaded_schedule_query(query: str) -> bool:
    return "已上传" in query and "课表" in query and ".pdf" in query


def _format_conflict_message(filename: str, parsed_count: int, conflicts: list[dict]) -> str:
    lines = []
    for conflict in conflicts[:8]:
        uploaded = conflict.get("uploaded", {})
        existing = conflict.get("existing", {})
        day = _weekday_label(uploaded.get("weekday", ""))
        uploaded_time = f"{uploaded.get('startTime', '--:--')}-{uploaded.get('endTime', '--:--')}"
        existing_time = f"{existing.get('startTime', '--:--')}-{existing.get('endTime', '--:--')}"
        existing_location = f" @ {existing.get('location')}" if existing.get("location") else ""
        lines.append(
            f"- {day} {uploaded_time}「{uploaded.get('title', '未命名课程')}」"
            f"与已有「{existing.get('title', '未命名课程')}」{existing_time}{existing_location} 时间冲突"
        )

    more = ""
    if len(conflicts) > len(lines):
        more = f"\n- 另外还有 {len(conflicts) - len(lines)} 条冲突未展开。"

    conflict_summary = (
        "这些记录与当前时间表存在时间冲突"
        if len(conflicts) >= parsed_count
        else f"其中 {len(conflicts)} 条记录与当前时间表存在时间冲突"
    )

    return (
        f"我检查了你刚上传的「{filename}」，识别出 {parsed_count} 条课表记录。\n\n"
        f"⚠️ {conflict_summary}。为避免重复导入或把你已删除的课程自动补回，本次没有导入这份 PDF 中的任何课程。\n\n"
        f"时间冲突明细：\n" + "\n".join(lines) + more +
        "\n\n如果你想用这份 PDF 覆盖当前课表，请先清空或删除已有冲突课程，再重新导入。"
    )


async def _build_recent_schedule_upload_conflict_message(query: str, user_id: str) -> str | None:
    if not _looks_like_uploaded_schedule_query(query):
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SourceFile)
            .where(
                SourceFile.user_id == user_id,
                SourceFile.kb_type == "personal",
                SourceFile.category == "schedule",
            )
            .order_by(SourceFile.created_at.desc())
            .limit(1)
        )
        source_file = result.scalar_one_or_none()
        if not source_file:
            return None

    try:
        docs = await pdf_loader(source_file.file_path)
        full_text = "\n".join(doc.page_content for doc in docs)
        parsed_items, warning = _parse_schedule_pdf_text(full_text)
    except Exception as e:
        logger.warning(f"【课表上传】最近上传课表冲突兜底解析失败: {e}")
        return None

    if not parsed_items or warning:
        return None

    conflicts = []
    async with AsyncSessionLocal() as db:
        from app.services.schedule_service import list_week_events as svc_list_events

        existing = await svc_list_events(db, user_id)
        for item in parsed_items:
            overlapping = [
                e for e in existing
                if e.weekday == item["weekday"]
                and _events_overlap(item["startTime"], item["endTime"], e.startTime, e.endTime)
            ]
            conflicts.extend(_format_schedule_conflict(item, e) for e in overlapping)

    if not conflicts:
        return None

    return _format_conflict_message(source_file.original_filename, len(parsed_items), conflicts)


async def _single_response_stream(query: str, session_id: str, user_id: str, content: str):
    yield f"data: {json.dumps({'type': 'response', 'content': content, 'session_id': session_id}, ensure_ascii=False)}\n\n"
    stored_response = json.dumps({"content": content, "card": None, "tool_calls": []}, ensure_ascii=False)
    await sm.session_manager.add_message(session_id, user_id, query, stored_response)
    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': [], 'credibility': {'level': 'high', 'label': '基于课表冲突检测', 'icon': '⚠️', 'detail': '由系统解析上传 PDF 并比对当前时间表'}}, ensure_ascii=False)}\n\n"


@chat_router.post("/agent/query/stream")
async def query_stream(
        request: QueryRequest,
        user_id: str = Depends(get_current_user_id),
        credentials = Depends(security),
        _: None = Depends(rate_limit(limit=100, window=60))
):
    """查询Agent流式响应"""
    # 如果没有提供session_id，自动生成一个
    session_id = request.session_id or str(uuid.uuid4())

    # Store JWT token for agent tools (e.g., doc_preview auto-fill)
    set_agent_jwt_token(credentials.credentials)

    conflict_message = await _build_recent_schedule_upload_conflict_message(request.query, user_id)
    if conflict_message:
        return StreamingResponse(
            _single_response_stream(request.query, session_id, user_id, conflict_message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    # 直接调用get_agent_stream_response函数
    return StreamingResponse(
        get_agent_stream_response(request.query, session_id, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@chat_router.post("/rag/query", response_model=RAGResponse)
async def query_rag(
        request: RAGRequest,
        router_service: ChatService = Depends(get_router_service),
        _: None = Depends(rate_limit(limit=15, window=60))
):
    """RAG检索"""
    result = await router_service.handle_rag_query(request.query)
    answer = result.get("answer") or result.get("response", "")
    return success_response(data=RAGResponse(response=answer, answer=answer, sources=result.get("sources", [])))


@chat_router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, user_id: str = Depends(get_current_user_id), router_service: ChatService = Depends(get_router_service)):
    """获取会话信息，使用user_id验证"""
    history = await router_service.handle_get_session(session_id, user_id)
    return success_response(data=SessionResponse(session_id=session_id, history=history))



@chat_router.delete("/session/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user_id), router_service: ChatService = Depends(get_router_service)):
    """删除会话"""
    await router_service.handle_delete_session(session_id, user_id)
    return success_response(message=f"Session {session_id} deleted successfully")

@chat_router.get("/sessions")
async def get_all_sessions(router_service: ChatService = Depends(get_router_service)):
    """获取所有会话ID"""
    session_ids = await router_service.handle_get_all_sessions()
    return success_response(data={"sessions": session_ids})



@chat_router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str, current_user_id: str = Depends(get_current_user_id), router_service: ChatService = Depends(get_router_service)):
    """获取用户所有会话ID"""
    session_ids = await router_service.handle_get_user_sessions(user_id, current_user_id)
    return success_response(data={"sessions": session_ids})


@chat_router.post("/vector/add/single")
async def add_vector_single(
        file: UploadFile = File(...),
        user_id: str = Depends(get_current_user_id),
        router_service: ChatService = Depends(get_router_service),
        _: None = Depends(rate_limit(limit=5, window=60))
):
    """上传文件，将文件保存到向量数据库，仅支持TXT和PDF"""
    filename = await router_service.handle_add_vector_single(file, user_id)
    return success_response(message=f"文件 {filename} 已成功上传并存储到向量数据库")



@chat_router.post("/vector/add/multiple")
async def add_vector_multiple(
        files: List[UploadFile] = File(..., description="要上传的文件列表，仅支持PDF和TXT格式"),
        user_id: str = Depends(get_current_user_id),
        router_service: ChatService = Depends(get_router_service),
        _: None = Depends(rate_limit(limit=3, window=60))
):
    """上传多个文件，将文件保存到向量数据库，仅支持TXT和PDF"""
    filenames = await router_service.handle_add_vector_multiple(files, user_id)
    return success_response(message=f"文件 {filenames} 已成功上传并存储到向量数据库")


@chat_router.delete("/vector/clean")
async def clean_user_vectors(user_id: str = Depends(get_current_user_id), router_service: ChatService = Depends(get_router_service)):
    """删除用户上传的所有向量"""
    await router_service.clean_user_upload(user_id)
    return success_response(message="已成功删除用户上传的所有向量")


@chat_router.post("/reorder", response_model=ReorderResponse)
async def reorder_documents(
        request: ReorderRequest,
        router_service: ChatService = Depends(get_router_service),
        _: None = Depends(rate_limit(limit=20, window=60))
):
    """使用Ollama本地的嵌入模型对文档进行中文重排序"""
    sorted_docs = await router_service.handle_reorder(request.query, request.documents)
    return success_response(data=ReorderResponse(documents=sorted_docs))
