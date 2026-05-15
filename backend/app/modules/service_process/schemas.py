from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ProcessStatus = Literal["draft", "collecting", "ready_to_submit", "submitted", "completed", "cancelled"]


class ServiceProcessOut(BaseModel):
    id: int
    name: str
    code: str
    category: str
    description: str = ""
    target_user: str = ""
    department: str = ""
    location: str = ""
    contact: str = ""
    required_materials: list[Any] = Field(default_factory=list)
    steps: list[Any] = Field(default_factory=list)
    faq: list[Any] = Field(default_factory=list)
    source_type: str = "seed"
    source_id: str = ""
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserProcessInstanceOut(BaseModel):
    id: int
    user_id: str
    process_id: int
    process: ServiceProcessOut | None = None
    status: str
    current_step: int = 0
    collected_data: dict[str, Any] = Field(default_factory=dict)
    generated_document_id: str = ""
    related_schedule_id: int | None = None
    related_task_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class ProcessInstanceUpdate(BaseModel):
    status: ProcessStatus | None = None
    current_step: int | None = Field(default=None, ge=0)
    collected_data: dict[str, Any] | None = None


class ProcessReminderRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    due_at: datetime
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
