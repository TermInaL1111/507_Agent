import os
import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.success_response import success_response
from app.services.source_file_service import ensure_download_permission, get_source_file, list_visible_source_files
from app.utils.auth_utils import get_current_user_id


source_file_router = APIRouter(prefix="/api/source-file", tags=["source-file"])


@source_file_router.get("/list")
async def list_source_files(
        kb_type: str = Query(default=""),
        user_id: str = Depends(get_current_user_id),
):
    files = await list_visible_source_files(user_id, kb_type=kb_type)
    return success_response(data={"files": files})


@source_file_router.get("/download/{file_id}")
async def download_source_file(file_id: str, user_id: str = Depends(get_current_user_id)):
    source_file = await get_source_file(file_id)
    if source_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    ensure_download_permission(source_file, user_id)

    if not source_file.file_path or not os.path.isfile(source_file.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    filename = source_file.original_filename or source_file.stored_filename
    encoded_filename = quote(filename)
    return FileResponse(
        source_file.file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@source_file_router.get("/preview/{file_id}")
async def preview_source_file(file_id: str, user_id: str = Depends(get_current_user_id)):
    source_file = await get_source_file(file_id)
    if source_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    ensure_download_permission(source_file, user_id)

    if not source_file.file_path or not os.path.isfile(source_file.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    filename = source_file.original_filename or source_file.stored_filename
    encoded_filename = quote(filename)
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(
        source_file.file_path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"},
    )
