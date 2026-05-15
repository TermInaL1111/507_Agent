from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.success_response import success_response
from app.db.db_config import get_db
from app.modules.service_process.schemas import ProcessInstanceUpdate, ProcessReminderRequest
from app.modules.service_process.service import ServiceProcessService
from app.utils.auth_utils import get_current_user_id


service_process_router = APIRouter(prefix="/api/service-processes", tags=["service-processes"])


@service_process_router.get("")
async def list_processes(
    category: str | None = None,
    keyword: str | None = None,
    enabled: bool | None = Query(default=True),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    return success_response(data=await ServiceProcessService(db).list_processes(category, keyword, enabled))


@service_process_router.get("/instances/")
async def list_instances(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return success_response(data=await ServiceProcessService(db).list_instances(user_id))


@service_process_router.get("/instances/{instance_id}")
async def get_instance(instance_id: int, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    instance = await ServiceProcessService(db).get_instance(user_id, instance_id)
    return success_response(data=ServiceProcessService(db).instance_out(instance))


@service_process_router.patch("/instances/{instance_id}")
async def update_instance(
    instance_id: int,
    payload: ProcessInstanceUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return success_response(message="流程已保存", data=await ServiceProcessService(db).update_instance(user_id, instance_id, payload))


@service_process_router.post("/instances/{instance_id}/generate-document")
async def generate_document(instance_id: int, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return success_response(data=await ServiceProcessService(db).generate_document(user_id, instance_id))


@service_process_router.post("/instances/{instance_id}/add-reminder")
async def add_reminder(
    instance_id: int,
    payload: ProcessReminderRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return success_response(message="提醒已添加", data=await ServiceProcessService(db).add_reminder(user_id, instance_id, payload))


@service_process_router.get("/{process_id}")
async def get_process(process_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_user_id)):
    process = await ServiceProcessService(db).get_process(process_id)
    return success_response(data=ServiceProcessService.process_out(process))


@service_process_router.post("/{process_id}/start")
async def start_process(
    process_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return success_response(message="流程已启动", data=await ServiceProcessService(db).start_instance(user_id, process_id))
