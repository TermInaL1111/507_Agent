import asyncio
import json
import os
from typing import Dict, List, Tuple, Optional

from app.db.db_config import AsyncSessionLocal
from app.models.chat_history import ChatSession, ChatMessage
from app.core.logger_handler import logger


CONTEXT_SUMMARY_ENABLED = os.getenv("CONTEXT_SUMMARY_ENABLED", "true").lower() == "true"
CONTEXT_RECENT_PAIRS = int(os.getenv("CONTEXT_RECENT_PAIRS", "8"))
CONTEXT_SUMMARY_TRIGGER_PAIRS = int(os.getenv("CONTEXT_SUMMARY_TRIGGER_PAIRS", "12"))
CONTEXT_SUMMARY_MAX_CHARS = int(os.getenv("CONTEXT_SUMMARY_MAX_CHARS", "1600"))


class DatabaseSessionManager:
    """Database-backed chat session manager."""

    def __init__(self):
        self._lock = asyncio.Lock()

    @classmethod
    async def create(cls) -> "DatabaseSessionManager":
        instance = cls()
        logger.info("【数据库会话管理】初始化完成")
        return instance

    async def get_session(self, session_id: str, user_id: str) -> Dict:
        """Return full session history for UI replay and management APIs."""
        async with AsyncSessionLocal() as db:
            result = await db.run_sync(
                lambda session: session.query(ChatSession)
                .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
                .first()
            )

            if result:
                messages = await db.run_sync(
                    lambda session: session.query(ChatMessage)
                    .filter(ChatMessage.session_id == result.id)
                    .order_by(ChatMessage.created_at)
                    .all()
                )
                history = self._messages_to_pairs(messages)
                metadata = result.metadata_ or {}
                return {
                    "history": history,
                    "summary": metadata.get("context_summary", ""),
                }

            existing_session = await db.run_sync(
                lambda session: session.query(ChatSession).filter(ChatSession.id == session_id).first()
            )
            if existing_session:
                logger.warning("【数据库会话管理】会话 %s 不属于用户 %s", session_id, user_id)
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="当前会话不属于你",
                )

            new_session = ChatSession(
                id=session_id,
                user_id=user_id,
                title="新的对话",
            )
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            logger.info("【数据库会话管理】创建新会话: %s 属于用户: %s", session_id, user_id)
            return {"history": [], "summary": ""}

    async def add_message(self, session_id: str, user_id: str, user_message: str, assistant_message: str):
        """Append one user/assistant turn and then optionally compress older context."""
        async with AsyncSessionLocal() as db:
            existing_session = await db.run_sync(
                lambda session: session.query(ChatSession).filter(ChatSession.id == session_id).first()
            )

            if existing_session:
                if existing_session.user_id != user_id:
                    logger.warning("【数据库会话管理】会话 %s 不属于用户 %s，无法添加消息", session_id, user_id)
                    from fastapi import HTTPException, status

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="当前会话不属于你，无法添加消息",
                    )
                session = existing_session
            else:
                session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    title="新的对话",
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)

            if session.title == "新的对话":
                title_summary = user_message[:30].strip()
                if len(user_message) > 30:
                    title_summary += "..."
                session.title = title_summary

            db.add(ChatMessage(session_id=session.id, role="user", content=user_message))
            db.add(ChatMessage(session_id=session.id, role="assistant", content=assistant_message))

            await db.commit()
            logger.info("【数据库会话管理】添加消息到会话: %s 属于用户: %s", session_id, user_id)

        await self.maybe_compress_context(session_id, user_id)

    async def get_history(self, session_id: str, user_id: str) -> List[Tuple[str, str]]:
        """Return full conversation history."""
        session_data = await self.get_session(session_id, user_id)
        return session_data.get("history", [])

    async def get_agent_context(self, session_id: str, user_id: str) -> Dict:
        """Return compressed model context: older summary plus recent raw turns."""
        session_data = await self.get_session(session_id, user_id)
        history = session_data.get("history", [])
        summary = session_data.get("summary", "")
        if not CONTEXT_SUMMARY_ENABLED:
            return {"summary": "", "history": history}
        return {
            "summary": summary,
            "history": history[-CONTEXT_RECENT_PAIRS:] if CONTEXT_RECENT_PAIRS > 0 else history,
        }

    async def maybe_compress_context(self, session_id: str, user_id: str) -> None:
        """Summarize older turns into chat_sessions.metadata.context_summary.

        Original messages remain in chat_messages for replay and audit. Only model
        calls use the compressed view, which keeps long sessions cheaper and more
        stable without changing existing session APIs.
        """
        if not CONTEXT_SUMMARY_ENABLED:
            return
        try:
            async with self._lock:
                async with AsyncSessionLocal() as db:
                    session = await db.run_sync(
                        lambda s: s.query(ChatSession)
                        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
                        .first()
                    )
                    if not session:
                        return

                    messages = await db.run_sync(
                        lambda s: s.query(ChatMessage)
                        .filter(ChatMessage.session_id == session_id)
                        .order_by(ChatMessage.created_at)
                        .all()
                    )
                    min_messages = (CONTEXT_RECENT_PAIRS + CONTEXT_SUMMARY_TRIGGER_PAIRS) * 2
                    if len(messages) <= min_messages:
                        return

                    metadata = dict(session.metadata_ or {})
                    summarized_count = int(metadata.get("context_summary_message_count") or 0)
                    cutoff = max(len(messages) - CONTEXT_RECENT_PAIRS * 2, 0)
                    if cutoff <= summarized_count:
                        return
                    if cutoff - summarized_count < CONTEXT_SUMMARY_TRIGGER_PAIRS * 2:
                        return

                    old_messages = messages[summarized_count:cutoff]
                    previous_summary = metadata.get("context_summary", "")
                    new_summary = await self._summarize_messages(previous_summary, old_messages)
                    if not new_summary:
                        return

                    metadata["context_summary"] = new_summary[:CONTEXT_SUMMARY_MAX_CHARS]
                    metadata["context_summary_message_count"] = cutoff
                    session.metadata_ = metadata
                    await db.commit()
                    logger.info(
                        "【数据库会话管理】上下文已压缩: session=%s summarized_messages=%s",
                        session_id,
                        cutoff,
                    )
        except Exception as exc:
            logger.warning("【数据库会话管理】上下文压缩跳过: session=%s error=%s", session_id, exc)

    async def clear_session(self, session_id: str, user_id: str):
        async with AsyncSessionLocal() as db:
            session = await db.run_sync(
                lambda s: s.query(ChatSession)
                .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
                .first()
            )
            if session:
                await db.delete(session)
                await db.commit()
                logger.info("【数据库会话管理】会话 %s 已清除，属于用户: %s", session_id, user_id)

    async def get_all_session_ids(self, user_id: Optional[str] = None) -> List[str]:
        async with AsyncSessionLocal() as db:
            if user_id:
                sessions = await db.run_sync(
                    lambda s: s.query(ChatSession).filter(ChatSession.user_id == user_id).all()
                )
            else:
                sessions = await db.run_sync(lambda s: s.query(ChatSession).all())
            return [session.id for session in sessions]

    async def get_user_sessions(self, user_id: str) -> List[Dict]:
        async with AsyncSessionLocal() as db:
            sessions = await db.run_sync(
                lambda s: s.query(ChatSession).filter(ChatSession.user_id == user_id).all()
            )
            return [
                {
                    "id": session.id,
                    "title": session.title,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                }
                for session in sessions
            ]

    @staticmethod
    def _messages_to_pairs(messages: List[ChatMessage]) -> List[Tuple[str, str]]:
        history = []
        i = 0
        while i < len(messages):
            if messages[i].role == "user" and i + 1 < len(messages) and messages[i + 1].role == "assistant":
                history.append((messages[i].content, messages[i + 1].content))
                i += 2
            else:
                i += 1
        return history

    async def _summarize_messages(self, previous_summary: str, messages: List[ChatMessage]) -> str:
        transcript = "\n".join(
            f"{message.role}: {self._clean_message_for_summary(message.content)}"
            for message in messages
        )
        if not transcript.strip():
            return previous_summary

        prompt = (
            "请把以下学生智能服务 Agent 的早期对话压缩成一段可供后续对话使用的上下文摘要。\n"
            "要求：保留用户目标、已确认信息、重要偏好、未完成事项、已生成/已操作结果；"
            "删除寒暄和重复内容；不要记录敏感原文；控制在800字以内。\n\n"
            f"已有摘要：\n{previous_summary or '无'}\n\n"
            f"新增早期对话：\n{transcript[:6000]}"
        )

        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=os.getenv("CONTEXT_SUMMARY_MODEL", os.getenv("CHAT_MODEL", "deepseek-chat")),
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url=os.getenv("CHAT_BASE_URL", "https://api.deepseek.com/v1"),
                temperature=0.2,
            )
            response = await llm.ainvoke(prompt)
            content = getattr(response, "content", "") or ""
            return content.strip() or self._fallback_summary(previous_summary, transcript)
        except Exception as exc:
            logger.warning("【数据库会话管理】LLM 摘要失败，使用本地截断摘要: %s", exc)
            return self._fallback_summary(previous_summary, transcript)

    @staticmethod
    def _clean_message_for_summary(content: str) -> str:
        text = str(content or "")
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = str(parsed.get("content") or parsed.get("answer") or text)
        except Exception:
            pass
        return " ".join(text.split())[:1200]

    @staticmethod
    def _fallback_summary(previous_summary: str, transcript: str) -> str:
        combined = f"{previous_summary}\n{transcript}" if previous_summary else transcript
        return combined[-CONTEXT_SUMMARY_MAX_CHARS:]


database_session_manager = None


async def init_database_session_manager():
    global database_session_manager
    database_session_manager = await DatabaseSessionManager.create()
    return database_session_manager
