from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.campus_location_service import (
    CampusLocation,
    build_map_url,
    find_best_location,
    search_campus_locations,
)


NAVIGATION_INTENT_PATTERN = re.compile(
    r"(在哪|哪里|怎么走|带我去|我要去|去.+怎么|导航|路线|位置|地图|从.+到.+)"
)


@dataclass
class CampusAIResult:
    handled: bool
    message: str = ""
    result_card: dict | None = None

    def payload(self) -> dict:
        return {
            "answer": self.message,
            "result_card": self.result_card,
        }


def _location_summary(location: CampusLocation) -> str:
    return (
        f"已找到【{location.name}】：\n"
        f"地址：{location.address}\n"
        f"说明：{location.description}\n\n"
        f"[查看地图]({build_map_url(location)})"
    )


def _navigation_card(target: CampusLocation, start: CampusLocation | None = None) -> dict:
    route_title = f"{start.name} 到 {target.name}" if start else f"步行前往 {target.name}"
    return {
        "type": "navigation",
        "title": "校园导航",
        "summary": target.description,
        "start": start.name if start else "",
        "end": target.name,
        "mapUrl": build_map_url(target, start, show_route=bool(start)),
        "routes": [
            {
                "title": route_title,
                "duration": "站内地图查看",
                "distance": "",
                "steps": [
                    f"地址：{target.address}",
                    "点击查看地图后将在站内地图中规划步行路线。",
                ],
            }
        ],
    }


def _extract_route_points(query: str) -> tuple[str, str] | None:
    match = re.search(r"从(.+?)到(.+?)(?:怎么走|路线|导航|在哪|$)", query)
    if not match:
        return None
    return match.group(1).strip(" ，,。."), match.group(2).strip(" ，,。.")


def _extract_target_keywords(query: str) -> str:
    text = query.strip()
    text = re.sub(r"^(带我去|我要去|我想去|去)", "", text)
    text = re.sub(r"(在哪里|在哪|哪里|怎么走|导航|路线|位置|地图|吧|吗|？|\?)", "", text)
    return text.strip(" ，,。.")


def handle_campus_ai_message(query: str) -> CampusAIResult:
    if not NAVIGATION_INTENT_PATTERN.search(query):
        return CampusAIResult(False)

    route_points = _extract_route_points(query)
    if route_points:
        start_keyword, target_keyword = route_points
        start = find_best_location(start_keyword)
        target = find_best_location(target_keyword)
        if start and target:
            message = (
                f"已为你找到从【{start.name}】到【{target.name}】的校园步行导航入口。\n\n"
                f"终点地址：{target.address}\n"
                f"说明：{target.description}\n\n"
                f"[查看站内路线]({build_map_url(target, start, show_route=True)})"
            )
            return CampusAIResult(True, message, _navigation_card(target, start))
        missing = []
        if not start:
            missing.append(f"起点“{start_keyword}”")
        if not target:
            missing.append(f"终点“{target_keyword}”")
        return CampusAIResult(True, f"我还没有匹配到{ '、'.join(missing) }，请补充更准确的校园地点名称。")

    keyword = _extract_target_keywords(query)
    matches = search_campus_locations(keyword, limit=5)
    if not matches:
        return CampusAIResult(True, "我还没有匹配到这个校园地点，请补充更准确的地点名称，例如“图书馆”“第二教学楼”“食堂”。")

    if len(matches) > 1 and matches[0]["name"] not in keyword and not any(alias in keyword for alias in matches[0]["aliases"]):
        names = "、".join(item["name"] for item in matches)
        return CampusAIResult(True, f"我找到了多个可能的地点：{names}。请告诉我你要去其中哪一个。")

    target = find_best_location(keyword)
    if not target:
        return CampusAIResult(True, "我还没有匹配到这个校园地点，请补充更准确的地点名称。")

    return CampusAIResult(True, _location_summary(target), _navigation_card(target))


def campus_result_to_history(result: CampusAIResult) -> str:
    if result.result_card:
        return json.dumps(result.payload(), ensure_ascii=False)
    return result.message
