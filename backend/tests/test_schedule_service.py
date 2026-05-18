"""TDD tests for schedule_service.py — mock DB, pure logic tests."""
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Prevent database connection on import by mocking db_config
sys.modules['aiomysql'] = MagicMock()
mock_engine = MagicMock()
mock_sessionmaker = MagicMock()
with patch('sqlalchemy.ext.asyncio.create_async_engine', return_value=mock_engine):
    with patch('sqlalchemy.ext.asyncio.async_sessionmaker', return_value=mock_sessionmaker):
        from app.services.schedule_service import (
            _time_to_minutes, _event_to_response,
            find_conflicts, create_event, list_week_events,
        )
from app.schemas.models import ScheduleEventCreate


# ═══════════════════ UNIT TESTS ═══════════════════

class TestTimeToMinutes:
    def test_standard_times(self):
        assert _time_to_minutes("08:00") == 480
        assert _time_to_minutes("00:00") == 0
        assert _time_to_minutes("23:59") == 1439

    def test_edge_cases(self):
        assert _time_to_minutes("00:01") == 1
        assert _time_to_minutes("12:00") == 720
        assert _time_to_minutes("00:00") == 0


class TestEventToResponse:
    def test_maps_all_fields(self):
        mock = MagicMock()
        mock.id = 1; mock.title = "数据结构"; mock.type = "course"
        mock.date = "2026-05-14"; mock.weekday = "Wednesday"
        mock.start_time = "10:00"; mock.end_time = "11:40"
        mock.location = "公教1-404"; mock.teacher = "王老师"
        mock.repeat = "weekly"; mock.source = "manual"; mock.remark = ""

        r = _event_to_response(mock)
        assert r.title == "数据结构"
        assert r.weekday == "Wednesday"
        assert r.startTime == "10:00"
        assert r.endTime == "11:40"
        assert r.location == "公教1-404"


class TestFindConflicts:
    def _make_mock_result(self, orm_obj):
        """Mock scalars().all() correctly — scalars() returns sync, not coroutine."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [orm_obj]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    def test_overlap_detected(self):
        mock_db = AsyncMock()
        mock_orm = MagicMock()
        mock_orm.id = 1; mock_orm.title = "现有课"; mock_orm.weekday = "Wednesday"
        mock_orm.start_time = "10:00"; mock_orm.end_time = "12:00"
        mock_orm.type = "course"; mock_orm.date = ""
        mock_orm.location = ""; mock_orm.teacher = ""
        mock_orm.repeat = "weekly"; mock_orm.source = "manual"; mock_orm.remark = ""
        mock_db.execute.return_value = self._make_mock_result(mock_orm)

        async def run():
            conflicts = await find_conflicts(mock_db, "u1", "Wednesday", "10:30", "11:30")
            assert len(conflicts) > 0
        import asyncio; asyncio.run(run())

    def test_no_overlap(self):
        mock_db = AsyncMock()
        mock_orm = MagicMock()
        mock_orm.id = 1; mock_orm.title = "早课"; mock_orm.weekday = "Wednesday"
        mock_orm.start_time = "08:00"; mock_orm.end_time = "09:30"
        mock_orm.type = "course"; mock_orm.date = ""; mock_orm.location = ""
        mock_orm.teacher = ""; mock_orm.repeat = "weekly"; mock_orm.source = "manual"; mock_orm.remark = ""
        mock_db.execute.return_value = self._make_mock_result(mock_orm)

        async def run():
            conflicts = await find_conflicts(mock_db, "u1", "Wednesday", "10:00", "12:00")
            assert len(conflicts) == 0
        import asyncio; asyncio.run(run())

    def test_adjacent_no_conflict(self):
        mock_db = AsyncMock()
        mock_orm = MagicMock()
        mock_orm.id = 1; mock_orm.title = "A课"; mock_orm.weekday = "Monday"
        mock_orm.start_time = "08:00"; mock_orm.end_time = "10:00"
        mock_orm.type = "course"; mock_orm.date = ""; mock_orm.location = ""
        mock_orm.teacher = ""; mock_orm.repeat = "weekly"; mock_orm.source = "manual"; mock_orm.remark = ""
        mock_db.execute.return_value = self._make_mock_result(mock_orm)

        async def run():
            conflicts = await find_conflicts(mock_db, "u1", "Monday", "10:00", "12:00")
            assert len(conflicts) == 0
        import asyncio; asyncio.run(run())


class TestScheduleEventCreateSchema:
    def test_valid_payload(self):
        p = ScheduleEventCreate(title="测试", type="course", date="", weekday="Monday",
                                startTime="08:00", endTime="09:35", location="", teacher="",
                                repeat="weekly", source="manual", remark="")
        assert p.title == "测试"
        assert p.startTime == "08:00"

    def test_repeat_none_allowed(self):
        p = ScheduleEventCreate(title="单次", type="activity", date="2026-05-20",
                                weekday="", startTime="14:00", endTime="16:00",
                                location="", teacher="", repeat="none", source="manual", remark="")
        assert p.repeat == "none"
