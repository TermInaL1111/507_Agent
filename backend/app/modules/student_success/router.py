from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.success_response import success_response
from app.db.db_config import get_db
from app.modules.student_success.schemas import StudentTaskCreate, StudentTaskGenerateRequest, StudentTaskUpdate
from app.modules.student_success.service import StudentSuccessService
from app.utils.auth_utils import get_current_user_id


student_success_router = APIRouter(prefix="/api/student-success", tags=["student-success"])


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@student_success_router.get("/tasks")
async def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    task_type: str | None = None,
    source_type: str | None = None,
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    priority: str | None = None,
    ai_generated: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    filters = {
        "status": status_filter,
        "task_type": task_type,
        "source_type": source_type,
        "from_date": _parse_dt(from_date),
        "to_date": _parse_dt(to_date),
        "priority": priority,
        "ai_generated": ai_generated,
    }
    return success_response(data=await StudentSuccessService(db).list_tasks(user_id, filters, limit, offset))


@student_success_router.post("/tasks")
async def create_task(
    payload: StudentTaskCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await StudentSuccessService(db).create_manual_task(user_id, payload)
    return success_response(message="任务已创建", data=task.model_dump())


@student_success_router.patch("/tasks/{task_id}")
async def update_task(
    task_id: int,
    payload: StudentTaskUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await StudentSuccessService(db).update_task(user_id, task_id, payload)
    return success_response(message="任务已更新", data=task.model_dump())


@student_success_router.post("/tasks/{task_id}/confirm")
async def confirm_task(
    task_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await StudentSuccessService(db).confirm_task(user_id, task_id)
    return success_response(message="任务已确认", data=task.model_dump())


@student_success_router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    deleted = await StudentSuccessService(db).delete_task(user_id, task_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return success_response(message="任务已删除")


@student_success_router.post("/generate")
async def generate_tasks(
    payload: StudentTaskGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    items, skipped = await StudentSuccessService(db).generate_suggestions(user_id, list(payload.sources), payload.days)
    return success_response(data={
        "success": True,
        "generated_count": len(items),
        "skipped_count": skipped,
        "message": "学生成功中心任务建议已生成",
        "items": [item.model_dump() for item in items],
    })


@student_success_router.get("/overview")
async def overview(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return success_response(data=await StudentSuccessService(db).overview(user_id))
