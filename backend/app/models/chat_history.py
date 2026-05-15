from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(64), primary_key=True, index=True)
    # 通过 user_id 关联用户微服务，不做物理外键约束
    user_id = Column(String(64), index=True, nullable=False)

    title = Column(String(255), default="新的对话")
    metadata_ = Column(JSON, name="metadata")  # metadata 是 SQL 保留字，加下划线
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("chat_sessions.id"))

    # LangChain 标准字段
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column(JSON, name="metadata")

    created_at = Column(DateTime(timezone=True), server_default=func.now()) 

    # 关系
    session = relationship("ChatSession", back_populates="messages")


class SourceFile(Base):
    __tablename__ = "source_files"

    file_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    kb_type = Column(String(64), default="personal", index=True)
    category = Column(String(128), default="")
    file_md5 = Column(String(64), index=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScheduleEvent(Base):
    __tablename__ = "schedule_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(32), default="task", index=True)
    date = Column(String(16), default="", index=True)
    weekday = Column(String(16), index=True, nullable=False)
    start_time = Column(String(8), nullable=False)
    end_time = Column(String(8), nullable=False)
    location = Column(String(255), default="")
    teacher = Column(String(128), default="")
    repeat = Column(String(32), default="weekly")
    source = Column(String(32), default="manual")
    remark = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), unique=True, index=True, nullable=False)
    auto_timeline_from_logs_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StudentSuccessTask(Base):
    __tablename__ = "student_success_tasks"
    __table_args__ = (
        Index("ix_student_success_user_due", "user_id", "due_at"),
        Index("ix_student_success_user_status", "user_id", "status"),
        Index("ix_student_success_source", "source_type", "source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    task_type = Column(String(32), default="other", index=True)
    source_type = Column(String(32), default="manual", index=True)
    source_id = Column(String(128), default="", index=True)
    due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    priority = Column(String(16), default="medium", index=True)
    status = Column(String(16), default="pending", index=True)
    ai_generated = Column(Boolean, default=False, nullable=False, index=True)
    requires_confirmation = Column(Boolean, default=False, nullable=False, index=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    ignored_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column(JSON, name="metadata", default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class CampusChannelPost(Base):
    __tablename__ = "campus_channel_posts"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_campus_channel_content_hash"),
        UniqueConstraint("post_url", name="uq_campus_channel_post_url"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_platform = Column(String(32), default="qq_channel", index=True, nullable=False)
    channel_url = Column(String(512), default="", nullable=False)
    channel_name = Column(String(255), default="", nullable=False)
    section_name = Column(String(128), default="", index=True)
    post_url = Column(String(512), default="", nullable=False)
    post_id = Column(String(128), default="", index=True)
    author_name = Column(String(128), default="")
    title = Column(String(512), default="")
    content = Column(Text, default="")
    summary = Column(Text, default="")
    images = Column(JSON, default=list)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer, nullable=True)
    publish_time_text = Column(String(64), default="")
    publish_time = Column(DateTime(timezone=True), nullable=True, index=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    content_hash = Column(String(64), default="", nullable=False, index=True)
    is_indexed = Column(Boolean, default=False, nullable=False, index=True)
    raw_data = Column(JSON, default=dict)
