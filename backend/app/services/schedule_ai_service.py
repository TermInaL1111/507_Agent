import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.models import ScheduleEventCreate
from app.services.schedule_service import create_event, find_conflicts


WEEKDAY_ALIASES = {
    "\u4e00": ("Monday", 0),
    "1": ("Monday", 0),
    "\u4e8c": ("Tuesday", 1),
    "2": ("Tuesday", 1),
    "\u4e09": ("Wednesday", 2),
    "3": ("Wednesday", 2),
    "\u56db": ("Thursday", 3),
    "4": ("Thursday", 3),
    "\u4e94": ("Friday", 4),
    "5": ("Friday", 4),
    "\u516d": ("Saturday", 5),
    "6": ("Saturday", 5),
    "\u65e5": ("Sunday", 6),
    "\u5929": ("Sunday", 6),
    "7": ("Sunday", 6),
}

WEEKDAY_LABELS = {
    "Monday": "\u5468\u4e00",
    "Tuesday": "\u5468\u4e8c",
    "Wednesday": "\u5468\u4e09",
    "Thursday": "\u5468\u56db",
    "Friday": "\u5468\u4e94",
    "Saturday": "\u5468\u516d",
    "Sunday": "\u5468\u65e5",
}

TYPE_KEYWORDS = {
    "meeting": ["\u4f1a\u8bae", "\u73ed\u4f1a", "\u4f8b\u4f1a", "\u627e\u8f85\u5bfc\u5458", "\u627e\u8001\u5e08", "\u7b7e\u8bf7\u5047\u6761"],
    "exam": ["\u8003\u8bd5", "\u6d4b\u9a8c", "\u8003\u6838"],
    "study": ["\u590d\u4e60", "\u81ea\u4e60", "\u5b66\u4e60", "\u9879\u76ee\u5f00\u53d1"],
    "activity": ["\u6d3b\u52a8", "\u8bb2\u5ea7", "\u793e\u56e2", "\u6bd4\u8d5b", "\u5403\u996d", "\u805a\u9910", "\u9a91\u81ea\u884c\u8f66", "\u9a91\u8f66", "\u4e1c\u6e56"],
    "course": ["\u4e0a\u8bfe", "\u8bfe\u7a0b", "\u9ad8\u7b49\u6570\u5b66", "\u6570\u5b66", "C\u8bed\u8a00", "c\u8bed\u8a00", "\u7f16\u7a0b"],
}

ADD_INTENT_PATTERN = re.compile(r"(\u52a0\u5165|\u6dfb\u52a0|\u8bb0\u5f55|\u5b89\u6392|\u5199\u5165|\u4fdd\u5b58).{0,10}(\u65e5\u7a0b|\u65f6\u95f4\u8868|\u8bfe\u8868|\u5b89\u6392)?|\u5e2e\u6211(\u8bb0|\u52a0|\u5b89\u6392|\u5199\u5165)")
CONFIRM_PATTERN = re.compile(r"^(\u786e\u8ba4|\u786e\u5b9a|\u53ef\u4ee5|\u662f\u7684|\u4ecd\u7136\u6dfb\u52a0|\u7ee7\u7eed\u6dfb\u52a0|\u52a0\u5165|\u6dfb\u52a0|\u597d)$")
CANCEL_PATTERN = re.compile(r"^(\u53d6\u6d88|\u4e0d\u8981|\u4e0d\u7528|\u7b97\u4e86|\u5426|\u4e0d\u6dfb\u52a0)$")
SEPARATORS = "\uff0c,。\uff1b;\n"

PENDING_SCHEDULE_ACTIONS: dict[str, dict] = {}


@dataclass
class ScheduleAIResult:
    handled: bool
    message: str = ""


def _pending_key(user_id: str, session_id: str) -> str:
    return f"{user_id}:{session_id}"


def _today() -> date:
    return datetime.now().date()


def _weekday_from_date(value: date) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][value.weekday()]


def _date_from_weekday(target_index: int, next_week: bool = False) -> date:
    base = _today()
    delta = (target_index - base.weekday()) % 7
    if next_week:
        delta += 7
    return base + timedelta(days=delta)


def _format_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _time_to_minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


def _normalize_hour(hour: int, period: str) -> int:
    if period in ("\u4e0b\u5348", "\u665a\u4e0a", "\u4eca\u665a", "\u591c\u91cc") and hour < 12:
        return hour + 12
    if period == "\u4e2d\u5348" and hour < 11:
        return hour + 12
    if period in ("\u4e0a\u5348", "\u65e9\u4e0a", "\u51cc\u6668") and hour == 12:
        return 0
    return hour


def _parse_clock(match: re.Match, period_group: int, hour_group: int, minute_group: int) -> int:
    period = match.group(period_group) or ""
    hour = _normalize_hour(int(match.group(hour_group)), period)
    minute = int(match.group(minute_group) or 0)
    return hour * 60 + minute


def _parse_date(text: str) -> tuple[str, str]:
    now = _today()
    if "\u660e\u5929" in text:
        target = now + timedelta(days=1)
        return target.isoformat(), _weekday_from_date(target)
    if "\u540e\u5929" in text:
        target = now + timedelta(days=2)
        return target.isoformat(), _weekday_from_date(target)
    if "\u4eca\u5929" in text or "\u4eca\u665a" in text:
        return now.isoformat(), _weekday_from_date(now)

    full = re.search(r"(\d{4})[-/\u5e74](\d{1,2})[-/\u6708](\d{1,2})\u65e5?", text)
    if full:
        target = date(int(full.group(1)), int(full.group(2)), int(full.group(3)))
        return target.isoformat(), _weekday_from_date(target)

    month_day = re.search(r"(\d{1,2})\u6708(\d{1,2})[\u65e5\u53f7]?", text)
    if month_day:
        target = date(now.year, int(month_day.group(1)), int(month_day.group(2)))
        if target < now:
            target = date(now.year + 1, target.month, target.day)
        return target.isoformat(), _weekday_from_date(target)

    weekday_match = re.search(r"(\u8fd9\u5468|\u4e0b\u5468|\u4e0b\u661f\u671f|\u4e0b\u793c\u62dc|\u6bcf\u5468|\u6bcf\u661f\u671f|\u6bcf\u793c\u62dc|\u5468|\u661f\u671f|\u793c\u62dc)([\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5\u59291-7])", text)
    if weekday_match:
        weekday, index = WEEKDAY_ALIASES[weekday_match.group(2)]
        if weekday_match.group(1).startswith("\u6bcf"):
            return "", weekday
        target = _date_from_weekday(index, next_week=weekday_match.group(1).startswith("\u4e0b"))
        return target.isoformat(), weekday

    return "", ""


def _parse_time_ranges(text: str) -> list[dict]:
    period = r"(\u4e0a\u5348|\u65e9\u4e0a|\u4e2d\u5348|\u4e0b\u5348|\u665a\u4e0a|\u4eca\u665a|\u591c\u91cc|\u51cc\u6668)?"
    pattern = re.compile(
        rf"{period}\s*(\d{{1,2}})\s*(?:[:\uff1a\u70b9]\s*(\d{{1,2}})?\s*)?(\u534a)?\s*"
        rf"(?:\u5230|\u81f3|-|~|\u2014)\s*"
        rf"{period}\s*(\d{{1,2}})\s*(?:[:\uff1a\u70b9]\s*(\d{{1,2}})?\s*)?(\u534a)?"
    )
    ranges = []
    for match in pattern.finditer(text):
        start = _parse_clock(match, 1, 2, 3)
        if match.group(4):
            start += 30
        end_period = match.group(5) or match.group(1) or ""
        end_hour = _normalize_hour(int(match.group(6)), end_period)
        end_minute = int(match.group(7) or 0)
        if match.group(8):
            end_minute += 30
        end = end_hour * 60 + end_minute
        if end <= start and not match.group(5) and (match.group(1) or "") in ("\u4e0b\u5348", "\u665a\u4e0a", "\u4eca\u665a", "\u591c\u91cc"):
            end += 12 * 60
        ranges.append({"start": start, "end": end, "span": match.span(), "text": match.group(0)})
    return ranges


def _parse_single_time(text: str) -> tuple[str, str]:
    period = r"(\u4e0a\u5348|\u65e9\u4e0a|\u4e2d\u5348|\u4e0b\u5348|\u665a\u4e0a|\u4eca\u665a|\u591c\u91cc|\u51cc\u6668)?"
    match = re.search(rf"{period}\s*(\d{{1,2}})\s*(?:[:\uff1a\u70b9]\s*(\d{{1,2}})?)", text)
    if not match:
        return "", ""
    start = _parse_clock(match, 1, 2, 3)
    return _format_time(start), _format_time(start + 60)


def _last_clause_before(text: str, index: int) -> str:
    start = max(text.rfind(separator, 0, index) for separator in SEPARATORS)
    return text[start + 1:index].strip()


def _clean_title(title: str) -> str:
    title = re.split(r"\u5e2e\u6211|\u8bf7\u5e2e|\u52a0\u5165|\u6dfb\u52a0|\u8bb0\u5f55|\u5199\u5165|\u4fdd\u5b58", title, maxsplit=1)[0]
    title = re.sub(r"^(?:\u6211|\u9700\u8981|\u8981|\u6253\u7b97|\u51c6\u5907|\u8ba1\u5212|\u60f3|\u53bb|\u5728|\u4e8b\u9879[:\uff1a])+", "", title)
    title = re.sub(r"^(?:\u548c|\u8ddf)[\u4e00-\u9fa5A-Za-z0-9]{1,6}(?:\u4e00\u8d77)?", "", title)
    title = title.rstrip("\u662f:\uff1a ")
    return title.strip(" \uff0c,\u3002.")


def _looks_like_time_context(title: str) -> bool:
    if not title:
        return True
    compact = re.sub(r"\s+", "", title)
    temporal = (
        "\u4eca\u5929",
        "\u660e\u5929",
        "\u540e\u5929",
        "\u4eca\u665a",
        "\u4e0a\u5348",
        "\u4e2d\u5348",
        "\u4e0b\u5348",
        "\u665a\u4e0a",
        "\u65e9\u4e0a",
        "\u51cc\u6668",
        "\u5468",
        "\u661f\u671f",
        "\u793c\u62dc",
        "\u7b2c\u4e00\u8282\u8bfe",
        "\u7b2c\u4e8c\u8282\u8bfe",
    )
    stripped = compact
    for word in temporal:
        stripped = stripped.replace(word, "")
    return not stripped or stripped in {"\u6211", "\u7684", "\u8981"}


def _first_clause_after_time(text: str, index: int) -> str:
    after = text[index:]
    stops = ["\uff0c", ",", "\u3002", ".", "\uff1b", ";", "\n"]
    end_indexes = [after.find(stop) for stop in stops if after.find(stop) >= 0]
    if end_indexes:
        after = after[:min(end_indexes)]
    return after.strip()


def _title_after_range(text: str, index: int) -> str:
    after = _first_clause_after_time(text, index)
    patterns = [
        r"(?:\u6253\u7b97|\u51c6\u5907|\u8ba1\u5212|\u60f3)\u53bb(.+)",
        r"(?:\u6253\u7b97|\u51c6\u5907|\u8ba1\u5212|\u60f3)(.+)",
        r"\u8981\u53bb(.+)",
        r"\u53bb(.+)",
        r"\u6709(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, after)
        if match:
            title = _clean_title(match.group(1))
            if title and not _looks_like_time_context(title):
                return title
    title = _clean_title(after)
    return "" if _looks_like_time_context(title) else title


def _title_for_range(text: str, item: dict) -> str:
    before = _last_clause_before(text, item["span"][0])
    title = _clean_title(before)
    if title and not _looks_like_time_context(title):
        return title

    return _title_after_range(text, item["span"][1])


def _parse_action_title(text: str) -> str:
    patterns = [
        r"(?:\u6253\u7b97|\u51c6\u5907|\u8ba1\u5212|\u60f3)\u53bb(.+?)(?:\uff0c|\u3002|,|\.|\u5e2e\u6211|\u52a0\u5165|\u6dfb\u52a0|\u8bb0\u5f55|\u5199\u5165|\u4fdd\u5b58|$)",
        r"(?:\u6253\u7b97|\u51c6\u5907|\u8ba1\u5212|\u60f3)(.+?)(?:\uff0c|\u3002|,|\.|\u5e2e\u6211|\u52a0\u5165|\u6dfb\u52a0|\u8bb0\u5f55|\u5199\u5165|\u4fdd\u5b58|$)",
        r"\u6211\u9700\u8981(.+?)(?:\uff0c|\u3002|,|\.|\u5e2e\u6211|\u52a0\u5165|\u6dfb\u52a0|\u8bb0\u5f55|\u5199\u5165|\u4fdd\u5b58|$)",
        r"(?:\u9700\u8981|\u8981\u53bb|\u53bb)(\u627e.+?)(?:\uff0c|\u3002|,|\.|\u5728|\u5e2e\u6211|\u52a0\u5165|\u6dfb\u52a0|\u8bb0\u5f55|\u5199\u5165|\u4fdd\u5b58|$)",
        r"(?:\u6709|\u53c2\u52a0|\u5b89\u6392\u4e00\u6b21)(.+?)(?:\uff0c|\u3002|,|\.|\u5728|\u5e2e\u6211|\u52a0\u5165|\u6dfb\u52a0|\u8bb0\u5f55|\u5199\u5165|\u4fdd\u5b58|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            title = _clean_title(match.group(1))
            if title:
                return title

    for keyword in ["\u7b7e\u8bf7\u5047\u6761", "\u8bf7\u5047\u6761", "\u9879\u76ee\u5f00\u53d1", "\u73ed\u4f1a", "\u8bb2\u5ea7", "\u8003\u8bd5", "\u590d\u4e60", "\u81ea\u4e60", "\u4f1a\u8bae", "\u6d3b\u52a8", "\u5403\u996d"]:
        if keyword in text:
            return "\u7b7e\u8bf7\u5047\u6761" if keyword == "\u8bf7\u5047\u6761" else keyword
    return ""


def _parse_location(text: str) -> str:
    match = re.search(r"(?:\u5730\u70b9[:\uff1a]|\u5728)([\u4e00-\u9fa5A-Za-z0-9\u697c\u5ba4\u533a\u9986\u5385A-Za-z -]{2,30})(?:\uff0c|\u3002|,|\.|$)", text)
    if not match:
        return ""
    value = match.group(1).strip()
    if "\u4e4b\u95f4" in value or value in {"\u4e24\u8005\u4e4b\u95f4", "\u4e24\u8282\u8bfe\u4e4b\u95f4", "\u4e2d\u95f4"}:
        return ""
    return value


def _parse_repeat(text: str) -> str:
    if re.search(r"(\u6bcf\u5468|\u6bcf\u661f\u671f|\u6bcf\u793c\u62dc)", text):
        return "weekly"
    if re.search(r"(\u6bcf\u5929|\u6bcf\u65e5)", text):
        return "daily"
    return "none"


def _parse_type(title: str, text: str) -> str:
    for event_type in ("meeting", "exam", "study", "activity", "course"):
        if any(keyword in title for keyword in TYPE_KEYWORDS[event_type]):
            return event_type
    target = f"{title} {text}"
    for event_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in target for keyword in keywords):
            return event_type
    return "other"


def _event_label(payload: ScheduleEventCreate) -> str:
    weekday_label = WEEKDAY_LABELS.get(payload.weekday, payload.weekday)
    if payload.repeat == "weekly":
        return f"\u6bcf{weekday_label} {payload.startTime}-{payload.endTime}"
    date_label = f"{payload.date} " if payload.date else ""
    return f"{date_label}{weekday_label} {payload.startTime}-{payload.endTime}"


def _make_payload(title: str, text: str, event_date: str, weekday: str, start: int, end: int, repeat: str) -> ScheduleEventCreate:
    clean_title = _clean_title(title)
    return ScheduleEventCreate(
        title=clean_title,
        type=_parse_type(clean_title, text),
        date=event_date,
        weekday=weekday,
        startTime=_format_time(start),
        endTime=_format_time(end),
        location=_parse_location(text),
        teacher="",
        repeat=repeat,
        source="ai_chat",
        remark="\u7531 AI \u667a\u80fd\u95ee\u7b54\u6dfb\u52a0",
    )


def parse_schedule_items_from_text(query: str, history_text: str = "") -> tuple[list[ScheduleEventCreate], list[str]]:
    text = f"{history_text}\n{query}" if ("\u521a\u624d" in query or "\u90a3\u4e2a" in query) else query
    event_date, weekday = _parse_date(text)
    ranges = _parse_time_ranges(text)
    repeat = _parse_repeat(text)
    items: list[ScheduleEventCreate] = []

    if event_date and weekday and len(ranges) >= 2 and any(word in text for word in ("\u4e24\u8005\u4e4b\u95f4", "\u4e24\u8282\u8bfe\u4e4b\u95f4", "\u4e24\u8282\u4e4b\u95f4", "\u4e2d\u95f4", "\u4e4b\u95f4")):
        action_title = _parse_action_title(text)
        if action_title and ranges[0]["end"] < ranges[1]["start"]:
            items.append(_make_payload(action_title, text, event_date, weekday, ranges[0]["end"], ranges[1]["start"], repeat))

    if event_date and weekday:
        for item in ranges:
            title = _title_for_range(text, item)
            if title and not any(payload.title == title and payload.startTime == _format_time(item["start"]) for payload in items):
                items.append(_make_payload(title, text, event_date, weekday, item["start"], item["end"], repeat))

    if not items and event_date and weekday:
        start_time, end_time = _parse_single_time(text)
        title = _parse_action_title(text) or (_title_for_range(text, ranges[0]) if ranges else "")
        if title and start_time and end_time:
            items.append(_make_payload(title, text, event_date, weekday, _time_to_minutes(start_time), _time_to_minutes(end_time), repeat))

    missing = []
    if not event_date and not weekday:
        missing.append("\u65e5\u671f\u6216\u661f\u671f")
    if not ranges and not any(_parse_single_time(text)):
        missing.extend(["\u5f00\u59cb\u65f6\u95f4", "\u7ed3\u675f\u65f6\u95f4"])
    if not items and "\u4e8b\u9879\u540d\u79f0" not in missing:
        missing.append("\u4e8b\u9879\u540d\u79f0")

    return sorted(items, key=lambda payload: _time_to_minutes(payload.startTime)), missing


def parse_schedule_from_text(query: str, history_text: str = "") -> tuple[Optional[ScheduleEventCreate], list[str]]:
    items, missing = parse_schedule_items_from_text(query, history_text)
    return (items[0], []) if items else (None, missing)


async def handle_schedule_ai_message(
        db: AsyncSession,
        user_id: str,
        session_id: str,
        query: str,
        history: list[tuple[str, str]],
) -> ScheduleAIResult:
    key = _pending_key(user_id, session_id)
    pending = PENDING_SCHEDULE_ACTIONS.get(key)

    if CANCEL_PATTERN.match(query.strip()) and pending:
        PENDING_SCHEDULE_ACTIONS.pop(key, None)
        return ScheduleAIResult(True, "\u5df2\u53d6\u6d88\u672c\u6b21\u65f6\u95f4\u8868\u6dfb\u52a0\u3002")

    if CONFIRM_PATTERN.match(query.strip()) and pending and pending.get("payloads"):
        pending = PENDING_SCHEDULE_ACTIONS.pop(key)
        return await _create_schedule_items(db, user_id, pending["payloads"])

    if pending and pending.get("kind") == "incomplete":
        combined_query = f"{pending['query']}\uff0c{query}"
        payloads, missing = parse_schedule_items_from_text(combined_query, "")
        if payloads and not missing:
            PENDING_SCHEDULE_ACTIONS.pop(key, None)
            return await _create_or_confirm_schedule_items(db, user_id, key, payloads)
        pending.update({"query": combined_query, "missing": missing})
        missing_text = "\u3001".join(missing)
        return ScheduleAIResult(True, f"\u6211\u8fd8\u7f3a\u5c11\uff1a{missing_text}\u3002\u8bf7\u7ee7\u7eed\u8865\u5145\u540e\u6211\u518d\u6dfb\u52a0\u3002")

    if not ADD_INTENT_PATTERN.search(query):
        return ScheduleAIResult(False)

    history_text = "\n".join(f"\u7528\u6237\uff1a{item[0]}\n\u52a9\u624b\uff1a{item[1]}" for item in history[-3:])
    payloads, missing = parse_schedule_items_from_text(query, history_text)
    if not payloads or missing:
        PENDING_SCHEDULE_ACTIONS[key] = {"kind": "incomplete", "query": query, "missing": missing}
        missing_text = "\u3001".join(missing)
        return ScheduleAIResult(True, f"\u6211\u53ef\u4ee5\u5e2e\u4f60\u52a0\u5165\u65f6\u95f4\u8868\uff0c\u4f46\u8fd8\u7f3a\u5c11\uff1a{missing_text}\u3002\u8bf7\u8865\u5145\u540e\u6211\u518d\u6dfb\u52a0\u3002")

    return await _create_or_confirm_schedule_items(db, user_id, key, payloads)


async def _create_or_confirm_schedule_items(
        db: AsyncSession,
        user_id: str,
        key: str,
        payloads: list[ScheduleEventCreate],
) -> ScheduleAIResult:
    conflict_messages = []
    for payload in payloads:
        conflicts = await find_conflicts(db, user_id, payload.weekday, payload.startTime, payload.endTime)
        if conflicts:
            conflict_text = "\uff1b".join(f"\u3010{item.title}\u3011{item.startTime}-{item.endTime}" for item in conflicts)
            conflict_messages.append(f"\u3010{payload.title}\u3011{payload.startTime}-{payload.endTime} \u51b2\u7a81\uff1a{conflict_text}")

    if conflict_messages:
        PENDING_SCHEDULE_ACTIONS[key] = {"kind": "conflict", "payloads": payloads}
        conflict_text = "\uff1b".join(conflict_messages)
        return ScheduleAIResult(True, f"\u68c0\u6d4b\u5230\u65f6\u95f4\u51b2\u7a81\uff1a{conflict_text}\u3002\u662f\u5426\u4ecd\u7136\u6dfb\u52a0\uff1f\u56de\u590d\u201c\u786e\u8ba4\u201d\u540e\u6211\u4f1a\u7ee7\u7eed\u52a0\u5165\u65f6\u95f4\u8868\u3002")

    return await _create_schedule_items(db, user_id, payloads)


async def _create_schedule_items(db: AsyncSession, user_id: str, payloads: list[ScheduleEventCreate]) -> ScheduleAIResult:
    created = []
    for payload in payloads:
        created.append(await create_event(db, user_id, payload))
    lines = "\n".join(f"- \u3010{event.title}\u3011{_event_label(event)}" for event in created)
    return ScheduleAIResult(True, f"\u5df2\u52a0\u5165 {len(created)} \u9879\u65f6\u95f4\u8868\uff1a\n{lines}")
