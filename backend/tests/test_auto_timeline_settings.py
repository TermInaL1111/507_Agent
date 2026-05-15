import asyncio

import pytest
from pydantic import ValidationError


def test_auto_timeline_default_preserves_existing_behavior(monkeypatch):
    from app.services.user_settings_service import default_auto_timeline_from_logs_enabled

    monkeypatch.delenv("AUTO_TIMELINE_FROM_LOGS_DEFAULT", raising=False)
    assert default_auto_timeline_from_logs_enabled() is True


def test_auto_timeline_default_can_be_configured(monkeypatch):
    from app.services.user_settings_service import default_auto_timeline_from_logs_enabled

    monkeypatch.setenv("AUTO_TIMELINE_FROM_LOGS_DEFAULT", "false")
    assert default_auto_timeline_from_logs_enabled() is False


def test_settings_update_rejects_non_boolean_value():
    from app.router.user import UserSettingsUpdate

    with pytest.raises(ValidationError):
        UserSettingsUpdate(autoGenerateTimelineEnabled="false")


def test_disabled_schedule_ai_does_not_parse_or_store_pending(monkeypatch):
    from app.services import schedule_ai_service

    async def disabled(_db, _user_id):
        return False

    def fail_parse(*_args, **_kwargs):
        raise AssertionError("parser should not be called when setting is disabled")

    monkeypatch.setattr(schedule_ai_service, "is_auto_timeline_enabled", disabled)
    monkeypatch.setattr(schedule_ai_service, "parse_schedule_items_from_text", fail_parse)

    key = "user-1:session-1"
    schedule_ai_service.PENDING_SCHEDULE_ACTIONS[key] = {"kind": "incomplete", "query": "old"}

    result = asyncio.run(
        schedule_ai_service.handle_schedule_ai_message(
            db=object(),
            user_id="user-1",
            session_id="session-1",
            query="确认",
            history=[],
        )
    )

    assert result.handled is False
    assert key not in schedule_ai_service.PENDING_SCHEDULE_ACTIONS
