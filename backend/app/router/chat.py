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

from app.schemas.models import QueryRequest, RAGResponse, RAGRequest, SessionResponse, ReorderResponse, ReorderRequest, ScheduleEventCreate
from app.services.schedule_service import create_event as svc_create_event
from app.services.source_file_service import create_source_file_record
from app.utils.auth_utils import get_current_user_id
from app.utils.file_handler import pdf_loader
from app.core.success_response import success_response
from app.core.rate_limit import rate_limit


chat_router = APIRouter(prefix="/api", tags=["api"])

# ── PDF 课表文本解析 ───────────────────────────────────────────

_WEEKDAY_MAP = {
    "星期一": "Monday", "周一": "Monday",
    "星期二": "Tuesday", "周二": "Tuesday",
    "星期三": "Wednesday", "周三": "Wednesday",
    "星期四": "Thursday", "周四": "Thursday",
    "星期五": "Friday", "周五": "Friday",
    "星期六": "Saturday", "周六": "Saturday",
    "星期日": "Sunday", "周七": "Sunday", "周天": "Sunday",
    "Monday": "Monday", "Mon": "Monday",
    "Tuesday": "Tuesday", "Tue": "Tuesday",
    "Wednesday": "Wednesday", "Wed": "Wednesday",
    "Thursday": "Thursday", "Thu": "Thursday",
    "Friday": "Friday", "Fri": "Friday",
    "Saturday": "Saturday", "Sat": "Saturday",
    "Sunday": "Sunday", "Sun": "Sunday",
}

_TIME_RANGE_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-~—至到]\s*(\d{1,2}:\d{2})")
_WEEKDAY_RE = re.compile(
    r"(星期[一二三四五六日天]|周[一二三四五六日天]|"
    r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
)
_LOCATION_RE = re.compile(r"([一-龥A-Za-z]+(?:楼|馆|厅|室|区|堂|中心)\S{0,6})")


def _parse_schedule_pdf_text(text: str) -> tuple[list[dict], str]:
    """从 PDF 提取的文本中解析课表条目。
    返回 (items, warning)，items 每项含 weekday/startTime/endTime/title/location。"""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return [], "PDF 文本为空，可能是扫描版图片 PDF，建议手动输入课表。"

    items: list[dict] = []
    current_weekday = ""

    for line in lines:
        wd_match = _WEEKDAY_RE.match(line)
        if wd_match and len(line) <= 10:
            current_weekday = _WEEKDAY_MAP.get(wd_match.group(1), "")
            continue

        time_match = _TIME_RANGE_RE.search(line)
        if not time_match:
            continue

        start_time = time_match.group(1)
        end_time = time_match.group(2)
        after_time = line[time_match.end():].strip()
        before_time = line[:time_match.start()].strip()

        # 尝试从行首提取星期
        line_weekday = current_weekday
        if before_time:
            wd_at_start = _WEEKDAY_RE.match(before_time)
            if wd_at_start:
                line_weekday = _WEEKDAY_MAP.get(wd_at_start.group(1), current_weekday)
                before_time = before_time[wd_at_start.end():].strip()

        if not line_weekday:
            continue

        # 提取地点（如 "教A301", "实验楼B202"）
        location = ""
        loc_match = _LOCATION_RE.search(after_time)
        if loc_match:
            location = loc_match.group(0)
            after_time = after_time.replace(location, "").strip()

        # 剩余部分作为课程标题
        title = (before_time + " " + after_time).strip()
        title = re.sub(r"\s+", " ", title).strip(" ，,。.")
        if not title or len(title) < 2:
            title_match = re.search(r"[一-龥A-Za-z]{2,20}", after_time)
            if title_match:
                title = title_match.group(0)

        if title and line_weekday:
            items.append({
                "title": title,
                "weekday": line_weekday,
                "startTime": start_time,
                "endTime": end_time,
                "location": location,
            })

    warning = ""
    if not items:
        warning = "未能识别出课表条目，请确认 PDF 包含文本格式的课表（非图片扫描件），或手动输入。"
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
                    teacher="",
                    repeat="weekly",
                    source="pdf_upload",
                    remark=f"从 {source_file.original_filename} 导入",
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
            except Exception as e:
                logger.warning(f"【课表上传】创建事件失败: {item} -> {e}")

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
    # 如果没有提供session_id，自动生成一个
    session_id = request.session_id or str(uuid.uuid4())
    
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
