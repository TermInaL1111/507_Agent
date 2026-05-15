import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger_handler import logger
from app.models.chat_history import UserSettings


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def default_auto_timeline_from_logs_enabled() -> bool:
    # Backward compatibility: the existing product behavior was enabled by default.
    # Deployments that want new users to opt in can set this env var to false.
    return _env_bool("AUTO_TIMELINE_FROM_LOGS_DEFAULT", True)


async def get_or_create_user_settings(db: AsyncSession, user_id: str) -> UserSettings:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    if settings:
        return settings

    settings = UserSettings(
        user_id=user_id,
        auto_timeline_from_logs_enabled=default_auto_timeline_from_logs_enabled(),
    )
    db.add(settings)
    await db.flush()
    logger.info("【用户设置】已初始化用户设置，用户ID: %s", user_id)
    return settings


async def get_auto_timeline_from_logs_enabled(db: AsyncSession, user_id: str) -> bool:
    settings = await get_or_create_user_settings(db, user_id)
    return bool(settings.auto_timeline_from_logs_enabled)


async def set_auto_timeline_from_logs_enabled(db: AsyncSession, user_id: str, enabled: bool) -> bool:
    settings = await get_or_create_user_settings(db, user_id)
    settings.auto_timeline_from_logs_enabled = enabled
    await db.flush()
    logger.info("【用户设置】自动生成时间节点开关已更新，用户ID: %s，enabled=%s", user_id, enabled)
    return bool(settings.auto_timeline_from_logs_enabled)


async def is_auto_timeline_enabled(db: AsyncSession, user_id: str) -> bool:
    try:
        enabled = await get_auto_timeline_from_logs_enabled(db, user_id)
        if not enabled:
            logger.info("【自动时间节点】用户设置已关闭，跳过自动识别，用户ID: %s", user_id)
        return enabled
    except Exception as exc:
        logger.warning("【自动时间节点】读取用户设置失败，按安全策略跳过自动识别，用户ID: %s，错误: %s", user_id, exc)
        return _env_bool("AUTO_TIMELINE_FROM_LOGS_FAIL_OPEN", False)
