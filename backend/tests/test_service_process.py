import pytest
from pydantic import ValidationError


def test_process_instance_update_rejects_invalid_status():
    from app.modules.service_process.schemas import ProcessInstanceUpdate

    with pytest.raises(ValidationError):
        ProcessInstanceUpdate(status="bad")


def test_process_reminder_requires_title():
    from app.modules.service_process.schemas import ProcessReminderRequest

    with pytest.raises(ValidationError):
        ProcessReminderRequest(title="", due_at="2026-05-20T10:00:00")


def test_seed_contains_required_processes():
    from app.modules.service_process.seed import SEED_PROCESSES

    codes = {item["code"] for item in SEED_PROCESSES}
    assert {"leave_application", "repair_request", "certificate_application", "venue_booking"} <= codes
