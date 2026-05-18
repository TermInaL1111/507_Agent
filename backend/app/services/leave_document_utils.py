import datetime
import re
from typing import Any


LEAVE_FIELD_LABELS = {
    "duration_days": "请假天数",
    "start_time": "开始时间",
    "end_time": "结束时间",
    "student_phone": "本人联系方式",
    "parent_phone": "家长联系方式",
    "teacher_name": "任课老师姓名",
}


def normalize_recipient_type(recipient_type: str, sub_variants: dict, default_recipient_type: str = "") -> str:
    """Map user-facing recipient labels to configured template keys."""
    value = str(recipient_type or "").strip().lower()
    if value in sub_variants:
        return value

    aliases = {
        "teacher": {"teacher", "任课老师", "任课教师", "老师", "授课老师", "课程老师"},
        "student_affairs": {"student_affairs", "affairs", "学工组", "学生工作组", "辅导员", "导员", "学院", "学院备案"},
    }
    for key, values in aliases.items():
        if key in sub_variants and value in {str(v).lower() for v in values}:
            return key

    for key, cfg in sub_variants.items():
        label = str(cfg.get("label", "")).strip().lower()
        if label and (value == label or value in label or label in value):
            return key

    return default_recipient_type if default_recipient_type in sub_variants else next(iter(sub_variants.keys()), "")


def resolve_leave_template_name(fields_config: dict, variant: str, recipient_type: str = "") -> str:
    variants = fields_config.get("variants", {})
    if not variant and variants:
        variant = next(iter(variants.keys()))
    vcfg = variants.get(variant, {})
    template = vcfg.get("template", "")
    sub_variants = vcfg.get("sub_variants", {})
    if sub_variants:
        normalized = normalize_recipient_type(recipient_type, sub_variants, vcfg.get("default_recipient_type", ""))
        template = sub_variants.get(normalized, {}).get("template", template)
        if not template:
            default_key = vcfg.get("default_recipient_type", "")
            template = sub_variants.get(default_key, {}).get("template", "")
    return template or "template.docx"


def normalize_leave_fields(fields: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Fill derived fields needed for a print-ready leave note."""
    normalized = dict(fields or {})
    text = " ".join(str(v) for v in [query, normalized.get("reason", "")] if v)

    _normalize_leave_times(normalized, text)
    if not normalized.get("duration_days"):
        normalized["duration_days"] = _calculate_duration_days(
            str(normalized.get("start_date", "")),
            str(normalized.get("end_date", "")),
            str(normalized.get("start_time", "")),
            str(normalized.get("end_time", "")),
        )
    return normalized


def formal_leave_missing_fields(
    fields_config: dict,
    variant: str,
    recipient_type: str,
    fields: dict[str, Any],
) -> list[str]:
    variants = fields_config.get("variants", {})
    vcfg = variants.get(variant, {}) if variant else {}
    missing = []
    required = list(vcfg.get("formal_required", []))
    sub_variants = vcfg.get("sub_variants", {})
    if sub_variants:
        normalized_recipient = normalize_recipient_type(recipient_type, sub_variants, vcfg.get("default_recipient_type", ""))
        required.extend(sub_variants.get(normalized_recipient, {}).get("formal_required", []))

    for key in required:
        if not str(fields.get(key, "")).strip():
            missing.append(key)
    return missing


def format_missing_leave_fields(missing: list[str]) -> str:
    labels = [LEAVE_FIELD_LABELS.get(key, key) for key in missing]
    return (
        "为了生成可直接打印提交的请假条，还需要补充："
        + "、".join(labels)
        + "。请补充后我再生成正式文档。"
    )


def _normalize_leave_times(fields: dict[str, Any], text: str) -> None:
    if fields.get("start_time") and fields.get("end_time"):
        fields["start_time"] = _clean_time(str(fields["start_time"]))
        fields["end_time"] = _clean_time(str(fields["end_time"]))
        return

    explicit = re.search(r"(\d{1,2})(?::|：|点)(\d{0,2})\s*(?:-|~|至|到)\s*(\d{1,2})(?::|：|点)(\d{0,2})", text)
    if explicit:
        fields.setdefault("start_time", _format_time(explicit.group(1), explicit.group(2)))
        fields.setdefault("end_time", _format_time(explicit.group(3), explicit.group(4)))
        return

    ranges = [
        (("全天", "一天", "整天"), ("08:00", "18:00")),
        (("上午", "早上"), ("08:00", "12:00")),
        (("下午",), ("14:00", "18:00")),
        (("晚上", "晚自习"), ("18:30", "21:30")),
    ]
    for keywords, (start, end) in ranges:
        if any(keyword in text for keyword in keywords):
            fields.setdefault("start_time", start)
            fields.setdefault("end_time", end)
            return


def _clean_time(value: str) -> str:
    value = value.strip().replace("：", ":").replace("时", "").replace("点", "")
    m = re.match(r"^(\d{1,2})(?::(\d{1,2}))?$", value)
    if not m:
        return value
    return _format_time(m.group(1), m.group(2) or "00")


def _format_time(hour: str, minute: str = "") -> str:
    return f"{int(hour):02d}:{int(minute or 0):02d}"


def _calculate_duration_days(start_date: str, end_date: str, start_time: str, end_time: str) -> str:
    try:
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date or start_date)
    except ValueError:
        return ""
    days = max((end - start).days + 1, 1)
    if days == 1:
        minutes = _time_to_minutes(end_time) - _time_to_minutes(start_time)
        if 0 < minutes <= 240:
            return "半天"
        return "1天"
    return f"{days}天"


def _time_to_minutes(value: str) -> int:
    m = re.match(r"^(\d{1,2}):(\d{1,2})$", value or "")
    if not m:
        return 0
    return int(m.group(1)) * 60 + int(m.group(2))
