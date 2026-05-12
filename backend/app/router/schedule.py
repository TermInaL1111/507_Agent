from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.success_response import success_response
from app.db.db_config import get_db
from app.schemas.models import ScheduleConflictResponse, ScheduleEventCreate
from app.services.schedule_service import create_event, delete_event, find_conflicts, list_week_events, validate_event_payload
from app.utils.auth_utils import get_current_user_id


schedule_router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@schedule_router.get("/week")
async def get_week_schedule(
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
        week_offset: int = 0,
):
    events = await list_week_events(db, user_id, week_offset=week_offset)
    return success_response(data={"events": events})


@schedule_router.get("/today")
async def get_today_schedule(
        weekday: str,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
):
    events = [event for event in await list_week_events(db, user_id) if event.weekday == weekday]
    return success_response(data={"events": events})


@schedule_router.post("/events")
async def add_schedule_event(
        payload: ScheduleEventCreate,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
):
    try:
        conflicts = await find_conflicts(db, user_id, payload.weekday, payload.startTime, payload.endTime)
        event = await create_event(db, user_id, payload)
        return success_response(data={"event": event, "conflicts": conflicts})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@schedule_router.delete("/events/{event_id}")
async def remove_schedule_event(
        event_id: int,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
):
    deleted = await delete_event(db, user_id, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="schedule event not found")
    return success_response(message="Schedule event deleted")


@schedule_router.post("/conflicts", response_model=ScheduleConflictResponse)
async def check_schedule_conflicts(
        payload: ScheduleEventCreate,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
):
    try:
        validate_event_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    conflicts = await find_conflicts(db, user_id, payload.weekday, payload.startTime, payload.endTime)
    return ScheduleConflictResponse(hasConflict=bool(conflicts), conflicts=conflicts)
