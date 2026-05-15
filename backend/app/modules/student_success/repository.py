from datetime import datetime

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_history import StudentSuccessTask


PRIORITY_WEIGHT = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


class StudentSuccessRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tasks(self, user_id: str, filters: dict, limit: int = 50, offset: int = 0) -> tuple[list[StudentSuccessTask], int]:
        stmt = select(StudentSuccessTask).where(StudentSuccessTask.user_id == user_id)
        count_stmt = select(func.count()).select_from(StudentSuccessTask).where(StudentSuccessTask.user_id == user_id)
        conditions = self._filters(filters)
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        stmt = stmt.order_by(StudentSuccessTask.due_at.is_(None), StudentSuccessTask.due_at.asc(), StudentSuccessTask.priority.asc())
        stmt = stmt.offset(offset).limit(limit)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(rows), int(total)

    @staticmethod
    def _filters(filters: dict) -> list:
        conditions = []
        for field in ("status", "task_type", "source_type", "priority"):
            value = filters.get(field)
            if value:
                conditions.append(getattr(StudentSuccessTask, field) == value)
        if filters.get("ai_generated") is not None:
            conditions.append(StudentSuccessTask.ai_generated.is_(filters["ai_generated"]))
        if filters.get("from_date"):
            conditions.append(StudentSuccessTask.due_at >= filters["from_date"])
        if filters.get("to_date"):
            conditions.append(StudentSuccessTask.due_at <= filters["to_date"])
        return conditions

    async def get_task(self, user_id: str, task_id: int) -> StudentSuccessTask | None:
        result = await self.db.execute(
            select(StudentSuccessTask).where(
                and_(StudentSuccessTask.id == task_id, StudentSuccessTask.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def find_duplicate(
        self,
        user_id: str,
        title: str,
        task_type: str,
        due_at: datetime | None = None,
        source_type: str = "",
        source_id: str = "",
    ) -> StudentSuccessTask | None:
        conditions = [
            StudentSuccessTask.user_id == user_id,
            StudentSuccessTask.status.in_(["pending", "confirmed"]),
            StudentSuccessTask.task_type == task_type,
        ]
        if source_type and source_id:
            conditions.append(and_(StudentSuccessTask.source_type == source_type, StudentSuccessTask.source_id == source_id))
        else:
            normalized = title.strip()
            title_conditions = [StudentSuccessTask.title == normalized]
            if due_at:
                title_conditions.append(StudentSuccessTask.due_at == due_at)
            conditions.append(or_(*title_conditions))
        result = await self.db.execute(select(StudentSuccessTask).where(and_(*conditions)).limit(1))
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> StudentSuccessTask:
        record = StudentSuccessTask(**kwargs)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, user_id: str, task_id: int) -> bool:
        result = await self.db.execute(delete(StudentSuccessTask).where(
            and_(StudentSuccessTask.id == task_id, StudentSuccessTask.user_id == user_id)
        ))
        await self.db.commit()
        return bool(result.rowcount)
