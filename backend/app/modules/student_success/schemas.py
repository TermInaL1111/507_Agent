from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


TaskType = Literal[
    "course", "schedule", "deadline", "campus_notice", "cultivation_plan",
    "document", "manual", "ai_suggestion", "other",
]
SourceType = Literal[
    "schedule", "consultation_log", "campus_channel", "cultivation_plan",
    "manual", "ai_chat", "document", "other",
]
TaskStatus = Literal["pending", "confirmed", "completed", "ignored", "expired"]
TaskPriority = Literal["low", "medium", "high", "urgent"]


class StudentTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    due_at: datetime | None = None
    priority: TaskPriority = "medium"
    task_type: TaskType = "manual"


class StudentTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    due_at: datetime | None = None
    priority: TaskPriority | None = None
    task_type: TaskType | None = None
    status: TaskStatus | None = None


class StudentTaskOut(BaseModel):
    id: int
    title: str
    description: str = ""
    task_type: str
    source_type: str
    source_id: str = ""
    due_at: datetime | None = None
    priority: str
    status: str
    ai_generated: bool = False
    requires_confirmation: bool = False
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None
    ignored_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StudentTaskListResponse(BaseModel):
    total: int
    items: list[StudentTaskOut] = Field(default_factory=list)


class StudentTaskGenerateRequest(BaseModel):
    sources: list[SourceType] = Field(default_factory=lambda: ["schedule", "campus_channel", "cultivation_plan"])
    days: int = Field(default=7, ge=1, le=30)


class StudentTaskGenerateResponse(BaseModel):
    success: bool = True
    generated_count: int = 0
    skipped_count: int = 0
    message: str = "学生成功中心任务建议已生成"
    items: list[StudentTaskOut] = Field(default_factory=list)


class StudentSuccessOverview(BaseModel):
    todayTasks: list[StudentTaskOut] = Field(default_factory=list)
    upcomingTasks: list[StudentTaskOut] = Field(default_factory=list)
    overdueTasks: list[StudentTaskOut] = Field(default_factory=list)
    aiSuggestions: list[StudentTaskOut] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
