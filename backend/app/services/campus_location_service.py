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
    campus: str = "nanwangshan"
    latitude: float = 0.0
    longitude: float = 0.0
    description: str = ""
    address: str = ""
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            object.__setattr__(self, 'tags', [])

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
    # ── 未来城校区 (锦程街68号) ──
    CampusLocation(
        id="future-library",
        name="未来城图书馆",
        aliases=["未来城校图书馆", "新图书馆"],
        type="library",
        campus="future_city",
        latitude=30.4580,
        longitude=114.6140,
        description="现代化智能图书馆，设有多媒体学习区。",
        address="校区中心广场旁",
        tags=["自习", "借阅", "多媒体"],
    ),
    CampusLocation(
        id="future-canteen",
        name="未来城第一食堂",
        aliases=["未来城食堂", "新食堂"],
        type="canteen",
        campus="future_city",
        latitude=30.4570,
        longitude=114.6135,
        description="三层综合餐厅，各地特色美食。",
        address="学生生活区",
        tags=["餐饮", "美食"],
    ),
    CampusLocation(
        id="future-teaching-a",
        name="未来城教学楼A区",
        aliases=["未来城教学A", "新教A"],
        type="teaching_building",
        campus="future_city",
        latitude=30.4585,
        longitude=114.6155,
        description="智慧教室，支持线上线下混合教学。",
        address="校区东侧",
        tags=["智慧教室", "多媒体", "上课"],
    ),
    CampusLocation(
        id="future-dormitory",
        name="未来城学生公寓",
        aliases=["未来城宿舍", "研究生公寓"],
        type="dormitory",
        campus="future_city",
        latitude=30.4585,
        longitude=114.6130,
        description="研究生公寓，2人间。",
        address="生活区北侧",
        tags=["研究生", "公寓", "宿舍"],
    ),
    CampusLocation(
        id="future-sports",
        name="未来城体育中心",
        aliases=["未来城体育馆", "新体育馆"],
        type="sports",
        campus="future_city",
        latitude=30.4595,
        longitude=114.6128,
        description="游泳馆、网球馆、室内体育馆。",
        address="校区西北侧",
        tags=["游泳", "网球", "健身"],
    ),
    CampusLocation(
        id="future-service",
        name="未来城综合服务楼",
        aliases=["未来城超市", "快递站"],
        type="other",
        campus="future_city",
        latitude=30.4575,
        longitude=114.6138,
        description="超市、打印店、快递驿站、银行ATM。",
        address="生活区中心",
        tags=["购物", "打印", "快递"],
    ),
    CampusLocation(
        id="future-admin",
        name="未来城行政楼",
        aliases=["未来城办公楼", "新行政楼"],
        type="office",
        campus="future_city",
        latitude=30.4565,
        longitude=114.6145,
        description="学院办公室、教务处、学生事务中心。",
        address="校区南门入口",
        tags=["办公", "教务", "事务"],
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
