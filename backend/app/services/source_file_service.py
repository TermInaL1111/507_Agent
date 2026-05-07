import os
import re
import uuid
from typing import Optional

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_, select

from app.db.db_config import AsyncSessionLocal
from app.models.chat_history import SourceFile
from app.utils.file_handler import get_file_md5_hex
from app.utils.path_tool import get_abstract_path


SOURCE_FILE_DIR = get_abstract_path("data/source_files")


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "source-file")
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip() or "source-file"


async def create_source_file_record(
        file: UploadFile,
        user_id: str,
        kb_type: str = "personal",
        category: str = "",
        is_public: Optional[bool] = None,
) -> SourceFile:
    os.makedirs(SOURCE_FILE_DIR, exist_ok=True)

    original_filename = _safe_filename(file.filename or "source-file")
    file_id = f"file_{uuid.uuid4().hex}"
    ext = os.path.splitext(original_filename)[1]
    stored_filename = f"{file_id}{ext}"
    stored_path = os.path.join(SOURCE_FILE_DIR, stored_filename)

    await file.seek(0)
    async with aiofiles.open(stored_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await out.write(chunk)
    await file.seek(0)

    file_md5 = await get_file_md5_hex(stored_path)
    public = kb_type == "school_policy" if is_public is None else is_public

    record = SourceFile(
        file_id=file_id,
        user_id=user_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=stored_path,
        kb_type=kb_type,
        category=category or "",
        file_md5=file_md5,
        is_public=public,
    )

    async with AsyncSessionLocal() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)

    return record


async def get_source_file(file_id: str) -> Optional[SourceFile]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SourceFile).where(SourceFile.file_id == file_id))
        return result.scalar_one_or_none()


def serialize_source_file(source_file: SourceFile) -> dict:
    return {
        "file_id": source_file.file_id,
        "original_filename": source_file.original_filename,
        "stored_filename": source_file.stored_filename,
        "kb_type": source_file.kb_type,
        "category": source_file.category or "",
        "file_md5": source_file.file_md5,
        "is_public": bool(source_file.is_public),
        "created_at": source_file.created_at.isoformat() if source_file.created_at else "",
        "download_url": f"/api/source-file/download/{source_file.file_id}",
        "preview_url": f"/api/source-file/preview/{source_file.file_id}",
    }


async def list_visible_source_files(user_id: str, kb_type: str = "") -> list[dict]:
    stmt = select(SourceFile).where(
        or_(
            SourceFile.user_id == user_id,
            SourceFile.is_public == True,  # noqa: E712
            SourceFile.kb_type == "school_policy",
        )
    )
    if kb_type:
        stmt = stmt.where(SourceFile.kb_type == kb_type)
    stmt = stmt.order_by(SourceFile.created_at.desc())

    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        return [serialize_source_file(item) for item in result.scalars().all()]


async def find_source_file_by_name(doc_name: str, kb_type: str = "") -> Optional[SourceFile]:
    if not doc_name:
        return None

    stmt = select(SourceFile).where(SourceFile.original_filename == doc_name)
    if kb_type:
        stmt = stmt.where(SourceFile.kb_type == kb_type)
    stmt = stmt.order_by(SourceFile.created_at.desc())

    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        return result.scalars().first()


def ensure_download_permission(source_file: SourceFile, user_id: str) -> None:
    if source_file.kb_type == "school_policy" or source_file.is_public:
        return
    if source_file.kb_type == "personal" and source_file.user_id == user_id:
        return
    if source_file.kb_type == "course" and (source_file.is_public or source_file.user_id == user_id):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to download this file",
    )
