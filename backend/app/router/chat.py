import re
from typing import List
import uuid

from fastapi.routing import APIRouter
from fastapi import UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.agent import get_agent_stream_response
from app.agent.agent_tools import set_agent_user_context
from app.core.logger_handler import logger
from app.db.db_config import AsyncSessionLocal
from app.router.chat_service import ChatService, get_router_service
from app.schemas.models import (
    QueryRequest,
    RAGResponse,
    RAGRequest,
    SessionResponse,
    ReorderResponse,
    ReorderRequest,
    ScheduleEventCreate,
)
from app.services.schedule_service import create_event as svc_create_event
from app.services.source_file_service import create_source_file_record
from app.utils.auth_utils import get_current_user_id
from app.utils.file_handler import pdf_loader
from app.core.success_response import success_response
from app.core.rate_limit import rate_limit


chat_router = APIRouter(prefix="/api", tags=["api"])


_SECTION_TIMES = {
    ("1", "2"): ("08:00", "09:35"),
    ("3", "4"): ("10:05", "11:40"),
    ("5", "6"): ("14:00", "15:35"),
    ("7", "8"): ("16:05", "17:40"),
    ("9", "10"): ("19:00", "20:35"),
}

_WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
_WEEKDAY_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_COURSE_LINE_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})\s+"
    r"([^*]+?)"
    r"\*\s*"
    r"(.+?)"
    r"(?=\n?\d{1,2}\s*-\s*\d{1,2}\s+|$)"
)
_DETAIL_KV_RE = re.compile(r"\s*/?\s*([^:：/]+)[:：]\s*([^/]*)")


def _section_to_time(section_start: str, section_end: str) -> tuple[str, str]:
    """Convert class section numbers to clock time."""
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
    fields = {}
    for match in _DETAIL_KV_RE.finditer(detail_str):
        key = match.group(1).strip()
        value = match.group(2).strip().rstrip("/")
        fields[key] = value
    return fields


def _parse_schedule_pdf_text(text: str) -> tuple[list[dict], str]:
    """Parse text extracted from an academic affairs schedule PDF."""
    items: list[dict] = []
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    raw_lines = text.split("\n")
    merged: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if merged and (stripped.startswith(":") or stripped.startswith("/")):
            merged[-1] = merged[-1] + stripped
        else:
            merged.append(stripped)

    weekday_start_re = re.compile(r"^(星期[一二三四五六日])")

    day_blocks: dict[str, str] = {}
    current_day = ""
    current_lines: list[str] = []

    for line in merged:
        weekday_match = weekday_start_re.match(line)
        if weekday_match:
            if current_day and current_lines:
                day_blocks[current_day] = "\n".join(current_lines)
            current_day = _WEEKDAY_EN[_WEEKDAY_NAMES.index(weekday_match.group(1))]
            rest = line[weekday_match.end():].strip()
            current_lines = [rest] if rest else []
        elif current_day:
            if re.match(r"^(实践课程|其他课程)[：:]", line):
                if current_lines:
                    day_blocks[current_day] = "\n".join(current_lines)
                current_day = ""
                current_lines = []
            else:
                current_lines.append(line)

    if current_day and current_lines:
        day_blocks[current_day] = "\n".join(current_lines)

    for weekday_en, block in day_blocks.items():
        for match in _COURSE_LINE_RE.finditer(block):
            section_start = match.group(1)
            section_end = match.group(2)
            course_name = match.group(3).strip()
            detail_str = match.group(4).strip()

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
    """Upload a schedule PDF, parse courses, and create schedule events."""
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")
    if file.size and file.size > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 20MB")

    source_file = await create_source_file_record(
        file=file, user_id=user_id, kb_type="personal", category="schedule"
    )
    logger.info(f"【课表上传】文件已保存: {source_file.file_id} ({source_file.original_filename})")

    try:
        docs = await pdf_loader(source_file.file_path)
        full_text = "\n".join(doc.page_content for doc in docs)
    except Exception as exc:
        logger.error(f"【课表上传】PDF 文本提取失败: {exc}")
        raise HTTPException(status_code=422, detail=f"PDF 文本提取失败: {str(exc)}") from exc

    if not full_text.strip():
        return success_response(data={
            "file_id": source_file.file_id,
            "filename": source_file.original_filename,
            "text_preview": "",
            "events": [],
            "events_count": 0,
            "warning": "PDF 无可提取文本，可能是扫描版图片。请使用文本格式的 PDF（如教务系统导出）。",
        })

    parsed_items, warning = _parse_schedule_pdf_text(full_text)

    set_agent_user_context(user_id)
    created_events = []
    async with AsyncSessionLocal() as db:
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
                created_events.append({
                    "id": event.id,
                    "title": event.title,
                    "weekday": event.weekday,
                    "startTime": event.startTime,
                    "endTime": event.endTime,
                    "location": event.location,
                })
            except Exception as exc:
                logger.warning(f"【课表上传】创建事件失败: {item} -> {exc}")

    text_preview = full_text[:500] if len(full_text) > 500 else full_text
    return success_response(data={
        "file_id": source_file.file_id,
        "filename": source_file.original_filename,
        "text_preview": text_preview,
        "events": created_events,
        "events_count": len(created_events),
        "warning": warning or None,
    })


@chat_router.post("/agent/query/stream")
async def query_stream(
        request: QueryRequest,
        user_id: str = Depends(get_current_user_id),
        _: None = Depends(rate_limit(limit=10, window=60))
):
    """查询Agent流式响应"""
    session_id = request.session_id or str(uuid.uuid4())
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
