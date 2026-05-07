from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_history import ScheduleEvent
from app.schemas.models import ScheduleEventCreate, ScheduleEventResponse


WEEKDAYS = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
}


def _time_to_minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


def _event_to_response(event: ScheduleEvent) -> ScheduleEventResponse:
    return ScheduleEventResponse(
        id=event.id,
        title=event.title,
        type=event.type,
        date=event.date or "",
        weekday=event.weekday,
        startTime=event.start_time,
        endTime=event.end_time,
        location=event.location or "",
        teacher=event.teacher or "",
        repeat=event.repeat or "weekly",
        source=event.source or "manual",
        remark=event.remark or "",
    )


def validate_event_payload(payload: ScheduleEventCreate) -> None:
    if payload.weekday not in WEEKDAYS:
        raise ValueError("weekday must be one of Monday-Sunday")
    if _time_to_minutes(payload.startTime) >= _time_to_minutes(payload.endTime):
        raise ValueError("startTime must be earlier than endTime")


async def list_week_events(db: AsyncSession, user_id: str) -> list[ScheduleEventResponse]:
    result = await db.execute(
        select(ScheduleEvent)
        .where(ScheduleEvent.user_id == user_id)
        .order_by(ScheduleEvent.weekday, ScheduleEvent.start_time)
    )
    return [_event_to_response(event) for event in result.scalars().all()]


async def find_conflicts(
        db: AsyncSession,
        user_id: str,
        weekday: str,
        start_time: str,
        end_time: str,
        exclude_id: int | None = None,
) -> list[ScheduleEventResponse]:
    result = await db.execute(
        select(ScheduleEvent).where(
            and_(
                ScheduleEvent.user_id == user_id,
                ScheduleEvent.weekday == weekday,
            )
        )
    )
    start_minutes = _time_to_minutes(start_time)
    end_minutes = _time_to_minutes(end_time)
    conflicts = []
    for event in result.scalars().all():
        if exclude_id and event.id == exclude_id:
            continue
        event_start = _time_to_minutes(event.start_time)
        event_end = _time_to_minutes(event.end_time)
        if start_minutes < event_end and end_minutes > event_start:
            conflicts.append(_event_to_response(event))
    return conflicts


async def create_event(db: AsyncSession, user_id: str, payload: ScheduleEventCreate) -> ScheduleEventResponse:
    validate_event_payload(payload)
    event = ScheduleEvent(
        user_id=user_id,
        title=payload.title,
        type=payload.type,
        date=payload.date,
        weekday=payload.weekday,
        start_time=payload.startTime,
        end_time=payload.endTime,
        location=payload.location,
        teacher=payload.teacher,
        repeat=payload.repeat,
        source=payload.source,
        remark=payload.remark,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _event_to_response(event)


async def delete_event(db: AsyncSession, user_id: str, event_id: int) -> bool:
    result = await db.execute(
        select(ScheduleEvent).where(
            and_(ScheduleEvent.id == event_id, ScheduleEvent.user_id == user_id)
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        return False
    await db.delete(event)
    await db.commit()
    return True
