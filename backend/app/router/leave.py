"""请假条生成 API"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.logger_handler import logger
from app.core.rate_limit import rate_limit
from app.core.success_response import success_response
from app.schemas.leave import LeaveGenerateRequest
from app.services.leave_service import generate_leave_docx
from app.utils.auth_utils import get_current_user_id

leave_router = APIRouter(prefix="/api/leave", tags=["leave"])

_TEMP_DIR = Path("/tmp/leave_docx")
_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _clean_old_files():
    """清理超过 30 分钟的临时文件。"""
    import time
    now = time.time()
    for f in _TEMP_DIR.glob("*.docx"):
        if now - f.stat().st_mtime > 1800:
            f.unlink(missing_ok=True)


@leave_router.post("/generate")
async def generate_leave(
    req: LeaveGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    """生成请假条 docx，返回下载链接。"""
    _clean_old_files()

    buf, filename = generate_leave_docx(
        leave_type=req.leave_type,
        course=req.course_leave,
        long_req=req.long_leave,
    )

    file_id = uuid.uuid4().hex[:12]
    file_path = _TEMP_DIR / f"{file_id}.docx"
    file_path.write_bytes(buf.getvalue())

    logger.info(f"【请假条生成】{user_id} → {filename} ({file_id})")

    return success_response(data={
        "file_id": file_id,
        "filename": filename,
        "download_url": f"/api/leave/download/{file_id}",
    })


@leave_router.get("/download/{file_id}")
async def download_leave(
    file_id: str,
    _: None = Depends(rate_limit(limit=30, window=60)),
):
    """下载生成的请假条 docx。"""
    file_path = _TEMP_DIR / f"{file_id}.docx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期，请重新生成。")
    return FileResponse(
        path=str(file_path),
        filename="请假条.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
