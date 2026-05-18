from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProcessDocumentConfig:
    process_code: str
    doc_type: str
    display_name: str
    template_name: str = "template.docx"
    required_fields: tuple[str, ...] = field(default_factory=tuple)
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    message: str = "文书已生成，请下载后按学校要求提交；系统不会自动提交学校系统。"


FIELD_LABELS = {
    "name": "姓名",
    "student_id": "学号",
    "class_name": "班级",
    "contact_phone": "联系电话",
    "location": "报修地点",
    "facility_type": "设施类型",
    "problem_description": "问题描述",
    "preferred_time": "期望处理时间",
    "certificate_type": "证明类型",
    "purpose": "证明用途",
    "copies": "申请份数",
    "receiving_org": "接收单位或用途说明",
    "delivery_method": "领取方式",
    "venue_name": "预约场地",
    "activity_name": "活动名称",
    "usage_purpose": "场地用途",
    "start_datetime": "开始时间",
    "end_datetime": "结束时间",
    "attendees": "预计人数",
    "equipment": "设备需求",
    "organization": "所属组织或班级",
}


PROCESS_DOCUMENTS: dict[str, ProcessDocumentConfig] = {
    "repair_request": ProcessDocumentConfig(
        process_code="repair_request",
        doc_type="repair",
        display_name="报修申请单",
        required_fields=(
            "name",
            "student_id",
            "class_name",
            "contact_phone",
            "location",
            "facility_type",
            "problem_description",
        ),
        aliases={
            "name": ("student_name", "applicant_name"),
            "contact_phone": ("phone", "student_phone"),
            "location": ("repair_location", "address"),
            "facility_type": ("repair_type", "device_type"),
            "problem_description": ("description", "problem", "reason"),
        },
        defaults={"preferred_time": "请以后勤平台可选时间为准", "attachment_note": "如有现场照片，请在学校后勤平台提交时上传。"},
        message="报修申请单已生成，请下载后按学校后勤平台或宿管要求提交；系统不会自动提交后勤系统。",
    ),
    "certificate_application": ProcessDocumentConfig(
        process_code="certificate_application",
        doc_type="certificate",
        display_name="证明申请信息单",
        required_fields=(
            "name",
            "student_id",
            "class_name",
            "contact_phone",
            "certificate_type",
            "purpose",
            "copies",
        ),
        aliases={
            "name": ("student_name", "applicant_name"),
            "contact_phone": ("phone", "student_phone"),
            "certificate_type": ("type", "proof_type"),
            "purpose": ("usage", "reason"),
            "copies": ("count", "copy_count"),
        },
        defaults={"receiving_org": "请按实际用途填写或在提交前补充", "delivery_method": "请以学校官方系统或教务部门要求为准"},
        message="证明申请信息单已生成，请下载后按学校教务部门或官方系统要求提交；具体办理地点和入口请以学校官方通知为准。",
    ),
    "venue_booking": ProcessDocumentConfig(
        process_code="venue_booking",
        doc_type="venue",
        display_name="场地预约申请草稿",
        required_fields=(
            "name",
            "student_id",
            "contact_phone",
            "organization",
            "venue_name",
            "activity_name",
            "usage_purpose",
            "start_datetime",
            "end_datetime",
            "attendees",
        ),
        aliases={
            "name": ("student_name", "applicant_name", "responsible_person"),
            "contact_phone": ("phone", "student_phone"),
            "organization": ("class_name", "club", "department"),
            "venue_name": ("venue", "place", "classroom"),
            "usage_purpose": ("purpose", "reason"),
            "start_datetime": ("start_time", "start_date"),
            "end_datetime": ("end_time", "end_date"),
            "attendees": ("people_count", "participants"),
            "equipment": ("equipment_requirements", "device_need"),
        },
        defaults={"equipment": "无特殊设备需求", "notes": "当前仅生成申请草稿，需按学校官方预约渠道提交。"},
        message="场地预约申请草稿已生成，请下载后按学校官方预约系统或场地管理部门要求提交；系统不会显示预约成功。",
    ),
}


def get_process_document_config(process_code: str) -> ProcessDocumentConfig | None:
    return PROCESS_DOCUMENTS.get(process_code)


def normalize_process_document_fields(config: ProcessDocumentConfig, data: dict[str, Any]) -> dict[str, Any]:
    fields = dict(config.defaults)
    raw = dict(data or {})
    fields.update(raw)
    for target, aliases in config.aliases.items():
        if fields.get(target):
            continue
        for alias in aliases:
            if raw.get(alias):
                fields[target] = raw[alias]
                break
    return fields


def missing_process_document_fields(config: ProcessDocumentConfig, fields: dict[str, Any]) -> list[str]:
    return [key for key in config.required_fields if not str(fields.get(key, "")).strip()]


def format_process_missing_fields(config: ProcessDocumentConfig, missing: list[str]) -> str:
    labels = [FIELD_LABELS.get(key, key) for key in missing]
    return f"为了生成{config.display_name}，还需要补充：" + "、".join(labels) + "。请补充后我再生成正式文档。"
