from pydantic import BaseModel, StrictBool
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.success_response import success_response
from app.db.db_config import get_db
from app.core.logger_handler import logger
from app.services.user_settings_service import (
    get_auto_timeline_from_logs_enabled,
    set_auto_timeline_from_logs_enabled,
)
from app.utils.auth_utils import get_current_user_id, get_user_info_from_redis, security

user_router = APIRouter(tags=["user"], prefix="/user")
user_settings_router = APIRouter(tags=["user-settings"], prefix="/api/user")


class UserSettingsUpdate(BaseModel):
    autoGenerateTimelineEnabled: StrictBool

@user_router.get("/detail/")
async def get_user_info(user_id: str = Depends(get_current_user_id), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取用户信息"""
    # 借助 uuid 去查询redis 中存储的用户信息
    user_info = await get_user_info_from_redis(user_id, credentials)
    return success_response(
        message="获取用户信息成功",
        data=user_info,
    )


@user_settings_router.get("/settings")
async def get_user_settings(
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
):
    enabled = await get_auto_timeline_from_logs_enabled(db, user_id)
    return success_response(data={"autoGenerateTimelineEnabled": enabled})


@user_settings_router.patch("/settings")
async def update_user_settings(
        payload: UserSettingsUpdate,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
):
    try:
        enabled = await set_auto_timeline_from_logs_enabled(
            db,
            user_id,
            payload.autoGenerateTimelineEnabled,
        )
        return success_response(
            message="用户设置已保存",
            data={"autoGenerateTimelineEnabled": enabled},
        )
    except Exception as exc:
        logger.warning("【用户设置】更新失败，用户ID: %s，错误: %s", user_id, exc)
        raise
