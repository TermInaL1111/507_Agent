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


def cleanup_old_files(temp_dir: Path | None = None, max_age_seconds: int = 1800) -> None:
    """Delete generated documents older than max_age_seconds."""
    import time

    directory = temp_dir or _TEMP_DIR
    now = time.time()
    for file_path in directory.glob("*.docx"):
        if now - file_path.stat().st_mtime > max_age_seconds:
            file_path.unlink(missing_ok=True)


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
