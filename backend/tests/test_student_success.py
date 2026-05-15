import pytest
from pydantic import ValidationError


def test_student_task_schema_rejects_invalid_task_type():
    from app.modules.student_success.schemas import StudentTaskCreate

    with pytest.raises(ValidationError):
        StudentTaskCreate(title="测试", task_type="bad-type")


def test_student_task_schema_rejects_invalid_priority():
    from app.modules.student_success.schemas import StudentTaskCreate

    with pytest.raises(ValidationError):
        StudentTaskCreate(title="测试", priority="highest")


def test_student_success_task_output_shape():
    from app.modules.student_success.schemas import StudentTaskOut

    task = StudentTaskOut(
        id=1,
        title="完成数据库作业",
        task_type="manual",
        source_type="manual",
        priority="medium",
        status="pending",
    )

    assert task.title == "完成数据库作业"
    assert task.ai_generated is False
    assert task.requires_confirmation is False
