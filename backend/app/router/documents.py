import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from app.core.rate_limit import rate_limit

documents_router = APIRouter(prefix="/api/documents", tags=["documents"])

_TEMP_DIR = Path(os.getenv("DOCUMENTS_TEMP_DIR", "/tmp/documents"))
_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def get_temp_dir() -> Path:
    return _TEMP_DIR


@documents_router.get("/download/{file_id}")
async def download_document(
    file_id: str,
    _: None = Depends(rate_limit(limit=30, window=60)),
):
    file_path = _TEMP_DIR / f"{file_id}.docx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期，请重新生成。")

    return FileResponse(
        path=str(file_path),
        filename=f"{file_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
