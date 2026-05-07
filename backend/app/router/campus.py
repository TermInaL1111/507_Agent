import requests

from fastapi import APIRouter, HTTPException, Query

from app.core.success_response import success_response
from app.services.campus_location_service import (
    get_campus_location,
    list_campus_locations,
    search_campus_locations,
)
from app.services.campus_route_service import get_walking_route, resolve_route_point


campus_router = APIRouter(prefix="/api/campus", tags=["campus"])


@campus_router.get("/locations")
async def get_locations():
    return success_response(data={"locations": list_campus_locations()})


@campus_router.get("/locations/search")
async def search_locations(keyword: str = Query("", description="校园地点关键词")):
    return success_response(data={"locations": search_campus_locations(keyword)})


@campus_router.get("/locations/{location_id}")
async def get_location(location_id: str):
    location = get_campus_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="campus location not found")
    return success_response(data={"location": location})


@campus_router.get("/route/walking")
async def get_campus_walking_route(
        from_id: str | None = Query(None, description="起点校园地点 ID"),
        to_id: str | None = Query(None, description="终点校园地点 ID"),
        origin: str | None = Query(None, description="起点坐标，经度,纬度"),
        destination: str | None = Query(None, description="终点坐标，经度,纬度"),
        origin_name: str = Query("", description="起点名称"),
        destination_name: str = Query("", description="终点名称"),
):
    try:
        origin_point = resolve_route_point(location_id=from_id, coordinate=origin, name=origin_name)
        destination_point = resolve_route_point(location_id=to_id, coordinate=destination, name=destination_name)
        route = get_walking_route(origin_point, destination_point)
        return success_response(data={"route": route})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="AMap route service request failed") from exc
