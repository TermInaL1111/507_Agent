from fastapi import APIRouter
from fastapi.responses import RedirectResponse

leave_redirect_router = APIRouter(prefix="/api/leave", tags=["leave-compat"])


@leave_redirect_router.get("/download/{file_id}")
async def redirect_leave_download(file_id: str):
    return RedirectResponse(
        url=f"/api/documents/download/{file_id}",
        status_code=307,  # temporary redirect — 30-day compatibility
    )
