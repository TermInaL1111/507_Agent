import contextvars
import json
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
from app.schemas.leave import CourseLeaveRequest, LongLeaveRequest
from app.services.leave_service import generate_leave_docx
from app.services.schedule_service import (
    create_event as svc_create_event,
    find_conflicts as svc_find_conflicts,
    list_week_events as svc_list_week_events,
)
from app.utils.auth_utils import decode_django_jwt

import datetime

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


# ── Leave request tool ───────────────────────────────────────────

_TEMP_DIR = "/tmp/leave_docx"


@tool(description="""生成请假条 Word 文档并返回下载链接。

两种类型：
- course_leave: 课程请假（单次课请假），需要 recipient_type("teacher"交给任课老师 或 "student_affairs"学工组备案)、teacher_name(老师姓名，仅teacher类型)、class_name(班级)、student_name(姓名)、student_id(学号)、reason(请假原因)、duration_days(请假天数)、start_date(开始日期如2026年5月10日)、start_time(开始时间如8时)、end_date(结束日期)、end_time(结束时间)、student_phone(本人电话)、parent_phone(家长电话)、signature(签名)、sign_date(签字日期)
- long_leave: 长假期请假（多天离校），需要 student_name(姓名)、student_id(学号)、class_name(班号)、phone(离校期间电话)、parent_relation(亲属关系如父亲/母亲)、parent_phone(亲属电话)、leave_start(离校时间如2026年5月10日8时)、leave_end(返校时间)、total_days(共几天)、reason(请假原因)、destination(去向地址)、signature(签字)、sign_date(签字日期)

尽量从对话中提取信息填入参数，缺失的必填字段在返回中提醒用户补充。""")
async def generate_leave_request(
    leave_type: str = "course_leave",
    # 课程请假字段
    recipient_type: str = "teacher",
    teacher_name: str = "",
    class_name: str = "",
    student_name: str = "",
    student_id: str = "",
    reason: str = "",
    duration_days: str = "",
    start_date: str = "",
    start_time: str = "",
    end_date: str = "",
    end_time: str = "",
    student_phone: str = "",
    parent_phone: str = "",
    signature: str = "",
    sign_date: str = "",
    # 长假期请假字段
    phone: str = "",
    parent_relation: str = "",
    parent_phone_long: str = "",
    leave_start: str = "",
    leave_end: str = "",
    total_days: str = "",
    destination: str = "",
) -> str:
    import uuid
    from pathlib import Path

    Path(_TEMP_DIR).mkdir(parents=True, exist_ok=True)

    try:
        if leave_type == "course_leave":
            req = CourseLeaveRequest(
                recipient_type=recipient_type,
                teacher_name=teacher_name,
                class_name=class_name,
                student_name=student_name,
                student_id=student_id,
                reason=reason,
                duration_days=duration_days,
                start_date=start_date,
                start_time=start_time,
                end_date=end_date,
                end_time=end_time,
                student_phone=student_phone,
                parent_phone=parent_phone,
                signature=signature,
                sign_date=sign_date,
            )
        else:
            req = LongLeaveRequest(
                student_name=student_name,
                student_id=student_id,
                class_name=class_name,
                phone=phone,
                parent_relation=parent_relation,
                parent_phone=parent_phone_long or parent_phone,
                leave_start=leave_start,
                leave_end=leave_end,
                total_days=total_days,
                reason=reason,
                destination=destination,
                signature=signature,
                sign_date=sign_date,
            )

        buf, filename = generate_leave_docx(leave_type, req if leave_type == "course_leave" else None, req if leave_type == "long_leave" else None)

        file_id = uuid.uuid4().hex[:12]
        file_path = Path(_TEMP_DIR) / f"{file_id}.docx"
        file_path.write_bytes(buf.getvalue())

        download_url = f"/api/leave/download/{file_id}"

        # 检查缺失字段
        missing = []
        if leave_type == "course_leave":
            if not student_name: missing.append("姓名")
            if not student_id: missing.append("学号")
            if not class_name: missing.append("班级")
            if not reason: missing.append("请假原因")
            if not start_date: missing.append("开始日期")
        else:
            if not student_name: missing.append("姓名")
            if not student_id: missing.append("学号")
            if not reason: missing.append("请假原因")
            if not leave_start: missing.append("离校时间")

        hint = ""
        if missing:
            hint = f"\n\n⚠ 以下信息缺失，已留空：{'、'.join(missing)}。你可以[点击打开表单页面](/leave-request)补充完整后重新生成。"

        return f"✅ 请假条已生成：[下载 {filename}]({download_url}){hint}"

    except Exception as e:
        logger.error(f"【请假条生成】Agent 工具异常: {e}")
        return f"生成请假条时出现错误：{str(e)}"