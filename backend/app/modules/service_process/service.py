import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger_handler import logger
from app.models.chat_history import ServiceProcess, UserProcessInstance
from app.modules.service_process.schemas import ProcessInstanceUpdate, ProcessReminderRequest
from app.modules.student_success.schemas import StudentTaskCreate
from app.modules.student_success.service import StudentSuccessService


SENSITIVE_KEYS = {"contact", "phone", "id_card", "reason_detail"}


class ServiceProcessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def process_out(process: ServiceProcess) -> dict:
        return {
            "id": process.id,
            "name": process.name,
            "code": process.code,
            "category": process.category,
            "description": process.description or "",
            "target_user": process.target_user or "",
            "department": process.department or "",
            "location": process.location or "",
            "contact": process.contact or "",
            "required_materials": process.required_materials or [],
            "steps": process.steps or [],
            "faq": process.faq or [],
            "source_type": process.source_type or "seed",
            "source_id": process.source_id or "",
            "enabled": bool(process.enabled),
            "created_at": process.created_at,
            "updated_at": process.updated_at,
        }

    def instance_out(self, instance: UserProcessInstance) -> dict:
        return {
            "id": instance.id,
            "user_id": instance.user_id,
            "process_id": instance.process_id,
            "process": self.process_out(instance.process) if instance.process else None,
            "status": instance.status,
            "current_step": instance.current_step,
            "collected_data": instance.collected_data or {},
            "generated_document_id": instance.generated_document_id or "",
            "related_schedule_id": instance.related_schedule_id,
            "related_task_id": instance.related_task_id,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
            "completed_at": instance.completed_at,
        }

    async def list_processes(self, category: str | None = None, keyword: str | None = None, enabled: bool | None = True) -> list[dict]:
        stmt = select(ServiceProcess)
        conditions = []
        if enabled is not None:
            conditions.append(ServiceProcess.enabled.is_(enabled))
        if category:
            conditions.append(ServiceProcess.category == category)
        if keyword:
            like = f"%{keyword}%"
            conditions.append(or_(ServiceProcess.name.like(like), ServiceProcess.description.like(like), ServiceProcess.category.like(like)))
        if conditions:
            stmt = stmt.where(and_(*conditions))
        rows = (await self.db.execute(stmt.order_by(ServiceProcess.category, ServiceProcess.id))).scalars().all()
        return [self.process_out(row) for row in rows]

    async def get_process(self, process_id: int) -> ServiceProcess:
        process = await self.db.get(ServiceProcess, process_id)
        if not process or not process.enabled:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="process not found")
        return process

    async def start_instance(self, user_id: str, process_id: int) -> dict:
        process = await self.get_process(process_id)
        instance = UserProcessInstance(user_id=user_id, process_id=process.id, status="collecting", current_step=0, collected_data={})
        self.db.add(instance)
        await self.db.commit()
        result = await self.db.execute(
            select(UserProcessInstance).options(selectinload(UserProcessInstance.process)).where(UserProcessInstance.id == instance.id)
        )
        instance = result.scalar_one()
        logger.info("【办事流程】用户启动流程，用户ID: %s，process=%s，instance=%s", user_id, process.code, instance.id)
        return self.instance_out(instance)

    async def list_instances(self, user_id: str) -> list[dict]:
        rows = (await self.db.execute(
            select(UserProcessInstance)
            .options(selectinload(UserProcessInstance.process))
            .where(UserProcessInstance.user_id == user_id)
            .order_by(UserProcessInstance.updated_at.desc())
        )).scalars().all()
        return [self.instance_out(row) for row in rows]

    async def get_instance(self, user_id: str, instance_id: int) -> UserProcessInstance:
        result = await self.db.execute(select(UserProcessInstance).options(selectinload(UserProcessInstance.process)).where(
            and_(UserProcessInstance.id == instance_id, UserProcessInstance.user_id == user_id)
        ))
        instance = result.scalar_one_or_none()
        if not instance:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="process instance not found")
        return instance

    async def update_instance(self, user_id: str, instance_id: int, payload: ProcessInstanceUpdate) -> dict:
        instance = await self.get_instance(user_id, instance_id)
        data = payload.model_dump(exclude_unset=True)
        if "status" in data and data["status"]:
            instance.status = data["status"]
            if data["status"] == "completed":
                instance.completed_at = datetime.now()
        if data.get("current_step") is not None:
            instance.current_step = data["current_step"]
        if data.get("collected_data") is not None:
            instance.collected_data = self._sanitize_collected_data(data["collected_data"])
        await self.db.commit()
        result = await self.db.execute(
            select(UserProcessInstance).options(selectinload(UserProcessInstance.process)).where(UserProcessInstance.id == instance.id)
        )
        instance = result.scalar_one()
        logger.info("【办事流程】用户更新流程实例，用户ID: %s，instance=%s，status=%s", user_id, instance.id, instance.status)
        return self.instance_out(instance)

    @staticmethod
    def _sanitize_collected_data(data: dict) -> dict:
        clean = {}
        for key, value in (data or {}).items():
            if key in SENSITIVE_KEYS and isinstance(value, str):
                clean[key] = value[:120]
            elif isinstance(value, str):
                clean[key] = value[:500]
            else:
                clean[key] = value
        return clean

    async def generate_document(self, user_id: str, instance_id: int) -> dict:
        instance = await self.get_instance(user_id, instance_id)
        if instance.process.code != "leave_application":
            raise HTTPException(status_code=400, detail="当前流程暂不支持在线生成文书")
        fields = dict(instance.collected_data or {})
        from app.router.documents import get_temp_dir
        from app.services.document_generator import DocumentGenerator
        from app.services.leave_document_utils import (
            formal_leave_missing_fields,
            format_missing_leave_fields,
            normalize_leave_fields,
            resolve_leave_template_name,
        )
        documents_dir = Path("/app/documents")
        fields_config = json.loads((documents_dir / "leave" / "fields.json").read_text(encoding="utf-8"))
        variant = fields.pop("_variant", fields.get("variant", "course_leave")) or "course_leave"
        recipient_type = fields.pop("_recipient_type", fields.get("recipient_type", ""))
        fields = normalize_leave_fields(fields)
        missing = formal_leave_missing_fields(fields_config, variant, recipient_type, fields)
        if missing:
            raise HTTPException(status_code=400, detail=format_missing_leave_fields(missing))
        template_name = resolve_leave_template_name(fields_config, variant, recipient_type)
        gen = DocumentGenerator("/app/documents", get_temp_dir())
        output_path = gen.generate("leave", fields, template_name=template_name)
        file_id = output_path.stem
        instance.generated_document_id = file_id
        instance.status = "ready_to_submit"
        await self.db.commit()
        logger.info("【办事流程】请假流程生成文书，用户ID: %s，instance=%s", user_id, instance.id)
        return {
            "type": "document_result",
            "file_id": file_id,
            "file_name": f"{file_id}.docx",
            "download_url": f"/api/documents/download/{file_id}",
            "message": "请假条已生成，请下载后按学校要求提交；系统不会自动提交学校系统。",
        }

    async def add_reminder(self, user_id: str, instance_id: int, payload: ProcessReminderRequest) -> dict:
        instance = await self.get_instance(user_id, instance_id)
        task = await StudentSuccessService(self.db).create_manual_task(
            user_id,
            StudentTaskCreate(
                title=payload.title,
                description=f"来自办事流程：{instance.process.name}",
                due_at=payload.due_at,
                priority=payload.priority,
                task_type="manual",
            ),
        )
        instance.related_task_id = task.id
        await self.db.commit()
        logger.info("【办事流程】流程添加提醒任务，用户ID: %s，instance=%s，task=%s", user_id, instance.id, task.id)
        return {"task": task.model_dump()}
