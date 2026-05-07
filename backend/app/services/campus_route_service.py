from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from app.services.campus_location_service import CAMPUS_LOCATIONS, CampusLocation


AMAP_WALKING_ROUTE_URL = "https://restapi.amap.com/v3/direction/walking"


@dataclass(frozen=True)
class RoutePoint:
    longitude: float
    latitude: float
    name: str = ""

    @property
    def amap_value(self) -> str:
        return f"{self.longitude},{self.latitude}"

    def to_dict(self) -> dict:
        return {
            "longitude": self.longitude,
            "latitude": self.latitude,
            "name": self.name,
        }


def _location_to_point(location: CampusLocation) -> RoutePoint:
    return RoutePoint(
        longitude=location.longitude,
        latitude=location.latitude,
        name=location.name,
    )


def _parse_coordinate(value: str, name: str = "") -> RoutePoint:
    try:
        longitude, latitude = value.split(",", 1)
        return RoutePoint(longitude=float(longitude), latitude=float(latitude), name=name)
    except (TypeError, ValueError) as exc:
        raise ValueError("coordinate must be formatted as longitude,latitude") from exc


def _find_location(location_id: str) -> CampusLocation | None:
    return next((item for item in CAMPUS_LOCATIONS if item.id == location_id), None)


def resolve_route_point(location_id: str | None = None, coordinate: str | None = None, name: str = "") -> RoutePoint:
    if location_id:
        location = _find_location(location_id)
        if not location:
            raise ValueError(f"campus location not found: {location_id}")
        return _location_to_point(location)
    if coordinate:
        return _parse_coordinate(coordinate, name=name)
    raise ValueError("route point is required")


def _parse_polyline(polyline: str) -> list[list[float]]:
    points: list[list[float]] = []
    for raw_point in polyline.split(";"):
        if not raw_point:
            continue
        try:
            longitude, latitude = raw_point.split(",", 1)
            points.append([float(longitude), float(latitude)])
        except ValueError:
            continue
    return points


def get_walking_route(origin: RoutePoint, destination: RoutePoint) -> dict:
    key = os.getenv("AMAP_WEB_SERVICE_KEY")
    if not key:
        raise RuntimeError("AMAP_WEB_SERVICE_KEY is not configured")

    response = requests.get(
        AMAP_WALKING_ROUTE_URL,
        params={
            "origin": origin.amap_value,
            "destination": destination.amap_value,
            "key": key,
            "output": "json",
        },
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "1":
        message = payload.get("info") or payload.get("infocode") or "AMap route planning failed"
        raise RuntimeError(message)

    paths = payload.get("route", {}).get("paths") or []
    if not paths:
        raise RuntimeError("No walking route found")

    first_path = paths[0]
    steps = first_path.get("steps") or []
    polyline: list[list[float]] = []
    instructions = []
    for step in steps:
        instructions.append(step.get("instruction", ""))
        polyline.extend(_parse_polyline(step.get("polyline", "")))

    return {
        "origin": origin.to_dict(),
        "destination": destination.to_dict(),
        "distance": int(float(first_path.get("distance") or 0)),
        "duration": int(float(first_path.get("duration") or 0)),
        "polyline": polyline,
        "steps": [item for item in instructions if item],
        "provider": "amap_web_service",
    }
