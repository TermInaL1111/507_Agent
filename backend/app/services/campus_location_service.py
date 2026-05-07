from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal
from urllib.parse import quote


CampusLocationType = Literal[
    "teaching_building",
    "library",
    "canteen",
    "dormitory",
    "gate",
    "sports",
    "office",
    "lab",
    "other",
]


@dataclass(frozen=True)
class CampusLocation:
    id: str
    name: str
    aliases: list[str]
    type: CampusLocationType
    latitude: float
    longitude: float
    description: str
    address: str
    tags: list[str]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["mapUrl"] = build_map_url(self)
        return data


CAMPUS_LOCATIONS: list[CampusLocation] = [
    CampusLocation(
        id="library",
        name="图书馆",
        aliases=["校图书馆", "图书信息中心", "自习馆"],
        type="library",
        latitude=30.5236,
        longitude=114.3994,
        description="学校主要学习、自习与图书借阅场所。",
        address="校园中区",
        tags=["学习", "自习", "借书", "图书馆"],
    ),
    CampusLocation(
        id="teaching-building-1",
        name="第一教学楼",
        aliases=["一教", "1教", "教学楼一"],
        type="teaching_building",
        latitude=30.5241,
        longitude=114.3977,
        description="公共基础课与通识课程常用教学楼。",
        address="校园教学区西侧",
        tags=["教学楼", "上课", "教室", "一教"],
    ),
    CampusLocation(
        id="teaching-building-2",
        name="第二教学楼",
        aliases=["二教", "2教", "教学楼二"],
        type="teaching_building",
        latitude=30.5248,
        longitude=114.4011,
        description="专业课程、公共课程与考试常用教学楼。",
        address="校园教学区东侧",
        tags=["教学楼", "上课", "教室", "二教", "考试"],
    ),
    CampusLocation(
        id="canteen",
        name="食堂",
        aliases=["学生食堂", "餐厅", "饭堂"],
        type="canteen",
        latitude=30.5227,
        longitude=114.4002,
        description="提供早餐、午餐、晚餐和校园简餐。",
        address="学生生活区",
        tags=["吃饭", "餐饮", "食堂", "午饭", "晚饭"],
    ),
    CampusLocation(
        id="dormitory",
        name="学生宿舍",
        aliases=["宿舍", "寝室", "学生公寓"],
        type="dormitory",
        latitude=30.5215,
        longitude=114.3988,
        description="学生住宿生活区域。",
        address="校园生活区",
        tags=["宿舍", "住宿", "寝室", "生活区"],
    ),
    CampusLocation(
        id="gymnasium",
        name="体育馆",
        aliases=["体育场馆", "室内体育馆", "运动馆"],
        type="sports",
        latitude=30.5254,
        longitude=114.3989,
        description="室内体育课程、训练和校园活动场地。",
        address="校园北侧体育区",
        tags=["运动", "体育", "健身", "体育馆"],
    ),
    CampusLocation(
        id="main-gate",
        name="校门",
        aliases=["学校大门", "正门", "东门"],
        type="gate",
        latitude=30.5221,
        longitude=114.4026,
        description="校园主要出入口。",
        address="校园东侧主入口",
        tags=["校门", "入口", "出入口", "正门"],
    ),
    CampusLocation(
        id="administration-building",
        name="行政楼",
        aliases=["办公楼", "行政办公楼", "校办"],
        type="office",
        latitude=30.5232,
        longitude=114.3967,
        description="学校行政办公、事务办理与会议接待区域。",
        address="校园行政办公区",
        tags=["行政", "办公", "办事", "会议"],
    ),
]


TYPE_KEYWORDS = {
    "teaching_building": ["教学楼", "上课", "教室", "课程"],
    "library": ["图书", "借书", "自习", "学习"],
    "canteen": ["吃饭", "食堂", "餐厅", "饭"],
    "dormitory": ["宿舍", "寝室", "公寓"],
    "gate": ["校门", "门口", "入口", "出入口"],
    "sports": ["运动", "体育", "健身", "球馆"],
    "office": ["行政", "办公", "办事"],
    "lab": ["实验", "实验室"],
    "other": ["其他"],
}


def build_map_url(location: CampusLocation, start: CampusLocation | None = None, show_route: bool = False) -> str:
    url = f"/campus-map?location={quote(location.id)}"
    if start:
        url += f"&from={quote(start.id)}"
    if show_route:
        url += "&route=1"
    return url


def list_campus_locations() -> list[dict]:
    return [location.to_dict() for location in CAMPUS_LOCATIONS]


def get_campus_location(location_id: str) -> dict | None:
    for location in CAMPUS_LOCATIONS:
        if location.id == location_id:
            return location.to_dict()
    return None


def _score_location(location: CampusLocation, keyword: str) -> int:
    normalized = keyword.strip().lower()
    if not normalized:
        return 0

    score = 0
    haystacks = [
        (location.name, 10),
        *[(alias, 8) for alias in location.aliases],
        *[(tag, 6) for tag in location.tags],
        (location.type, 5),
        *[(word, 5) for word in TYPE_KEYWORDS.get(location.type, [])],
        (location.description, 2),
        (location.address, 2),
    ]
    for value, weight in haystacks:
        if normalized == value.lower():
            score += weight * 3
        elif normalized in value.lower() or value.lower() in normalized:
            score += weight
    return score


def search_campus_locations(keyword: str, limit: int = 10) -> list[dict]:
    scored = [
        (score, index, location)
        for index, location in enumerate(CAMPUS_LOCATIONS)
        if (score := _score_location(location, keyword)) > 0
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [location.to_dict() for _, _, location in scored[:limit]]


def find_best_location(keyword: str) -> CampusLocation | None:
    results = search_campus_locations(keyword, limit=1)
    if not results:
        return None
    location_id = results[0]["id"]
    return next((item for item in CAMPUS_LOCATIONS if item.id == location_id), None)
