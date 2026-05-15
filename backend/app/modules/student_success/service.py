from datetime import datetime, time, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger_handler import logger
from app.models.chat_history import CampusChannelPost, ChatMessage, ChatSession, StudentSuccessTask
from app.modules.student_success.repository import StudentSuccessRepository
from app.modules.student_success.schemas import StudentTaskCreate, StudentTaskOut, StudentTaskUpdate
from app.services.schedule_service import list_week_events
from app.services.schedule_ai_service import parse_schedule_items_from_text
from app.services.user_settings_service import is_auto_timeline_enabled


WEEKDAY_INDEX = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}
WEEKDAY_LABELS = {
    "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三", "Thursday": "周四",
    "Friday": "周五", "Saturday": "周六", "Sunday": "周日",
}


class StudentSuccessService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = StudentSuccessRepository(db)

    @staticmethod
    def to_out(task: StudentSuccessTask) -> StudentTaskOut:
        return StudentTaskOut(
            id=task.id,
            title=task.title,
            description=task.description or "",
            task_type=task.task_type,
            source_type=task.source_type,
            source_id=task.source_id or "",
            due_at=task.due_at,
            priority=task.priority,
            status=task.status,
            ai_generated=bool(task.ai_generated),
            requires_confirmation=bool(task.requires_confirmation),
            confirmed_at=task.confirmed_at,
            completed_at=task.completed_at,
            ignored_at=task.ignored_at,
            metadata=task.metadata_ or {},
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    async def list_tasks(self, user_id: str, filters: dict, limit: int = 50, offset: int = 0) -> dict:
        rows, total = await self.repo.list_tasks(user_id, filters, limit, offset)
        return {"total": total, "items": [self.to_out(row).model_dump() for row in rows]}

    async def create_manual_task(self, user_id: str, data: StudentTaskCreate) -> StudentTaskOut:
        duplicate = await self.repo.find_duplicate(user_id, data.title, data.task_type, data.due_at, "manual", "")
        if duplicate:
            logger.info("【学生成功中心】手动任务去重命中，用户ID: %s，task_id=%s", user_id, duplicate.id)
            return self.to_out(duplicate)
        task = await self.repo.create(
            user_id=user_id,
            title=data.title.strip(),
            description=data.description,
            task_type=data.task_type,
            source_type="manual",
            source_id="",
            due_at=data.due_at,
            priority=data.priority,
            status="pending",
            ai_generated=False,
            requires_confirmation=False,
            metadata_={"source_label": "手动添加"},
        )
        await self.db.commit()
        logger.info("【学生成功中心】用户创建手动任务，用户ID: %s，task_id=%s", user_id, task.id)
        return self.to_out(task)

    async def update_task(self, user_id: str, task_id: int, data: StudentTaskUpdate) -> StudentTaskOut:
        task = await self._get_owned_task(user_id, task_id)
        payload = data.model_dump(exclude_unset=True)
        now = datetime.now()
        for field in ("title", "description", "task_type", "priority", "due_at"):
            if field in payload:
                setattr(task, field, payload[field])
        if "status" in payload:
            self._apply_status(task, payload["status"], now)
        await self.db.commit()
        await self.db.refresh(task)
        logger.info("【学生成功中心】用户更新任务，用户ID: %s，task_id=%s，status=%s", user_id, task.id, task.status)
        return self.to_out(task)

    async def confirm_task(self, user_id: str, task_id: int) -> StudentTaskOut:
        task = await self._get_owned_task(user_id, task_id)
        task.status = "confirmed"
        task.requires_confirmation = False
        task.confirmed_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task)
        logger.info("【学生成功中心】用户确认AI建议任务，用户ID: %s，task_id=%s", user_id, task.id)
        return self.to_out(task)

    async def delete_task(self, user_id: str, task_id: int) -> bool:
        deleted = await self.repo.delete(user_id, task_id)
        if deleted:
            logger.info("【学生成功中心】用户删除任务，用户ID: %s，task_id=%s", user_id, task_id)
        return deleted

    async def overview(self, user_id: str) -> dict:
        today_start = datetime.combine(datetime.now().date(), time.min)
        today_end = datetime.combine(datetime.now().date(), time.max)
        week_end = today_start + timedelta(days=7)

        today = await self._query_tasks(user_id, StudentSuccessTask.due_at >= today_start, StudentSuccessTask.due_at <= today_end)
        upcoming = await self._query_tasks(user_id, StudentSuccessTask.due_at > today_end, StudentSuccessTask.due_at <= week_end)
        overdue = await self._query_tasks(user_id, StudentSuccessTask.due_at < today_start, StudentSuccessTask.status.in_(["pending", "confirmed"]))
        suggestions = await self._query_tasks(user_id, StudentSuccessTask.ai_generated.is_(True), StudentSuccessTask.requires_confirmation.is_(True), StudentSuccessTask.status == "pending")
        timeline = await self._timeline(user_id, week_end)
        stats = {
            "pending": await self._count(user_id, StudentSuccessTask.status.in_(["pending", "confirmed"])),
            "completed": await self._count(user_id, StudentSuccessTask.status == "completed"),
            "overdue": len(overdue),
            "aiSuggestions": len(suggestions),
        }
        return {
            "todayTasks": [self.to_out(item).model_dump() for item in today],
            "upcomingTasks": [self.to_out(item).model_dump() for item in upcoming],
            "overdueTasks": [self.to_out(item).model_dump() for item in overdue],
            "aiSuggestions": [self.to_out(item).model_dump() for item in suggestions],
            "timeline": timeline,
            "stats": stats,
        }

    async def generate_suggestions(self, user_id: str, sources: list[str], days: int = 7) -> tuple[list[StudentTaskOut], int]:
        created: list[StudentSuccessTask] = []
        skipped = 0
        if "schedule" in sources:
            rows, skip = await self._generate_from_schedule(user_id, days)
            created.extend(rows)
            skipped += skip
        if "campus_channel" in sources:
            rows, skip = await self._generate_from_campus_channel(user_id, days)
            created.extend(rows)
            skipped += skip
        if "cultivation_plan" in sources:
            rows, skip = await self._generate_from_cultivation_plan(user_id)
            created.extend(rows)
            skipped += skip
        if "consultation_log" in sources:
            if await is_auto_timeline_enabled(self.db, user_id):
                rows, skip = await self._generate_from_consultation_log(user_id)
                created.extend(rows)
                skipped += skip
            else:
                logger.info("【学生成功中心】咨询日志开关关闭，跳过任务生成，用户ID: %s", user_id)
        await self.db.commit()
        for item in created:
            await self.db.refresh(item)
        logger.info("【学生成功中心】生成任务建议完成，用户ID: %s，created=%s，skipped=%s", user_id, len(created), skipped)
        return [self.to_out(item) for item in created], skipped

    async def _get_owned_task(self, user_id: str, task_id: int) -> StudentSuccessTask:
        task = await self.repo.get_task(user_id, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return task

    @staticmethod
    def _apply_status(task: StudentSuccessTask, next_status: str, now: datetime) -> None:
        task.status = next_status
        if next_status == "completed":
            task.completed_at = now
        elif next_status == "ignored":
            task.ignored_at = now
        elif next_status == "confirmed":
            task.confirmed_at = now
            task.requires_confirmation = False

    async def _query_tasks(self, user_id: str, *conditions) -> list[StudentSuccessTask]:
        stmt = select(StudentSuccessTask).where(StudentSuccessTask.user_id == user_id, *conditions)
        stmt = stmt.order_by(StudentSuccessTask.due_at.is_(None), StudentSuccessTask.due_at.asc()).limit(20)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _count(self, user_id: str, condition) -> int:
        stmt = select(StudentSuccessTask).where(StudentSuccessTask.user_id == user_id, condition)
        return len((await self.db.execute(stmt)).scalars().all())

    async def _timeline(self, user_id: str, week_end: datetime) -> list[dict[str, Any]]:
        start = datetime.combine(datetime.now().date(), time.min)
        tasks = await self._query_tasks(user_id, StudentSuccessTask.due_at >= start, StudentSuccessTask.due_at <= week_end)
        items = [{
            "kind": "task",
            "date": task.due_at.date().isoformat() if task.due_at else "",
            "time": task.due_at.strftime("%H:%M") if task.due_at else "",
            "title": task.title,
            "source": task.source_type,
            "priority": task.priority,
            "status": task.status,
        } for task in tasks]
        for event in await list_week_events(self.db, user_id):
            event_date = self._date_for_weekday(event.weekday)
            if event_date and start.date() <= event_date <= week_end.date():
                items.append({
                    "kind": "schedule",
                    "date": event_date.isoformat(),
                    "time": event.startTime,
                    "title": event.title,
                    "source": "schedule",
                    "priority": "medium",
                    "status": "confirmed",
                })
        return sorted(items, key=lambda item: (item.get("date") or "9999", item.get("time") or "99:99"))[:40]

    @staticmethod
    def _date_for_weekday(weekday: str):
        if weekday not in WEEKDAY_INDEX:
            return None
        today = datetime.now().date()
        delta = (WEEKDAY_INDEX[weekday] - today.weekday()) % 7
        return today + timedelta(days=delta)

    async def _create_suggestion(self, user_id: str, title: str, task_type: str, source_type: str, source_id: str,
                                 due_at: datetime | None, priority: str, description: str, metadata: dict[str, Any],
                                 requires_confirmation: bool = True) -> tuple[StudentSuccessTask | None, bool]:
        duplicate = await self.repo.find_duplicate(user_id, title, task_type, due_at, source_type, source_id)
        if duplicate:
            logger.info("【学生成功中心】任务生成去重命中，用户ID: %s，existing_task=%s", user_id, duplicate.id)
            return None, True
        task = await self.repo.create(
            user_id=user_id,
            title=title[:255],
            description=description[:1200],
            task_type=task_type,
            source_type=source_type,
            source_id=source_id,
            due_at=due_at,
            priority=priority,
            status="pending",
            ai_generated=True,
            requires_confirmation=requires_confirmation,
            metadata_=metadata,
        )
        return task, False

    async def _generate_from_schedule(self, user_id: str, days: int) -> tuple[list[StudentSuccessTask], int]:
        created, skipped = [], 0
        end_date = datetime.now().date() + timedelta(days=days)
        for event in await list_week_events(self.db, user_id):
            event_date = self._date_for_weekday(event.weekday)
            if not event_date or event_date > end_date:
                continue
            due_at = datetime.combine(event_date, self._parse_time(event.startTime))
            task, dup = await self._create_suggestion(
                user_id=user_id,
                title=f"准备/参加：{event.title}",
                task_type="course" if event.type == "course" else "schedule",
                source_type="schedule",
                source_id=str(event.id),
                due_at=due_at,
                priority="medium",
                description=f"{WEEKDAY_LABELS.get(event.weekday, event.weekday)} {event.startTime}-{event.endTime} {event.location or ''}",
                metadata={"source_label": "课表日程", "source_title": event.title, "summary": event.remark or ""},
                requires_confirmation=False,
            )
            if task:
                created.append(task)
            if dup:
                skipped += 1
        return created, skipped

    @staticmethod
    def _parse_time(value: str) -> time:
        try:
            hour, minute = value.split(":", 1)
            return time(int(hour), int(minute))
        except Exception:
            return time(8, 0)

    async def _generate_from_campus_channel(self, user_id: str, days: int) -> tuple[list[StudentSuccessTask], int]:
        created, skipped = [], 0
        since = datetime.now() - timedelta(days=days)
        keywords = ["报名", "截止", "通知", "活动", "比赛", "讲座", "招募", "DDL", "ddl"]
        likes = [CampusChannelPost.title.like(f"%{word}%") for word in keywords]
        likes += [CampusChannelPost.content.like(f"%{word}%") for word in keywords]
        rows = (await self.db.execute(
            select(CampusChannelPost)
            .where(or_(*likes), or_(CampusChannelPost.publish_time == None, CampusChannelPost.publish_time >= since))
            .order_by(CampusChannelPost.publish_time.desc(), CampusChannelPost.scraped_at.desc())
            .limit(10)
        )).scalars().all()
        for post in rows:
            title = post.title or post.summary or post.content[:40] or "校园频道提醒"
            task, dup = await self._create_suggestion(
                user_id=user_id,
                title=f"关注校园通知：{title[:60]}",
                task_type="campus_notice",
                source_type="campus_channel",
                source_id=str(post.id),
                due_at=post.publish_time,
                priority="high" if "截止" in f"{title}{post.content}" else "medium",
                description=(post.summary or post.content or "")[:500],
                metadata={
                    "source_label": "校园频道公开内容",
                    "source_title": title,
                    "section_name": post.section_name or "其他版块",
                    "summary": "内容来源于校园公开频道，请以学校官方通知为准。",
                },
            )
            if task:
                created.append(task)
            if dup:
                skipped += 1
        return created, skipped

    async def _generate_from_cultivation_plan(self, user_id: str) -> tuple[list[StudentSuccessTask], int]:
        task, dup = await self._create_suggestion(
            user_id=user_id,
            title="核对本学期培养方案与学分进度",
            task_type="cultivation_plan",
            source_type="cultivation_plan",
            source_id="semester-review",
            due_at=datetime.combine(datetime.now().date() + timedelta(days=7), time(20, 0)),
            priority="medium",
            description="建议结合培养方案、已修课程和本学期选课情况核对学分进度。当前系统缺少完整成绩数据，不做毕业结论判断。",
            metadata={"source_label": "培养方案", "summary": "需要补充成绩或已修课程数据后才能做更准确判断。"},
        )
        return ([task] if task else []), 1 if dup else 0

    async def _generate_from_consultation_log(self, user_id: str) -> tuple[list[StudentSuccessTask], int]:
        created, skipped = [], 0
        sessions = select(ChatSession.id).where(ChatSession.user_id == user_id).limit(20)
        rows = (await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id.in_(sessions), ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.desc())
            .limit(12)
        )).scalars().all()
        for message in rows:
            payloads, _ = parse_schedule_items_from_text(message.content[:500], "")
            for payload in payloads[:2]:
                due_at = self._due_at_from_payload(payload)
                task, dup = await self._create_suggestion(
                    user_id=user_id,
                    title=payload.title,
                    task_type="deadline" if payload.type in {"exam", "meeting"} else "ai_suggestion",
                    source_type="consultation_log",
                    source_id=str(message.id),
                    due_at=due_at,
                    priority="medium",
                    description="根据已授权咨询记录识别到的时间节点建议，请确认后再加入正式待办。",
                    metadata={"source_label": "咨询日志", "summary": "已隐藏原始咨询内容，仅保留结构化时间节点。"},
                    requires_confirmation=True,
                )
                if task:
                    created.append(task)
                if dup:
                    skipped += 1
        return created, skipped

    @staticmethod
    def _due_at_from_payload(payload) -> datetime | None:
        if not payload.date:
            return None
        try:
            return datetime.fromisoformat(f"{payload.date}T{payload.startTime}:00")
        except Exception:
            return None
