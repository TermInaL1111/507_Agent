"""Tests for campus_location_service.py — pure logic, no DB needed."""
import pytest
import sys
from unittest.mock import MagicMock, patch

# Prevent db_config import cascade
sys.modules['aiomysql'] = MagicMock()
mock_engine = MagicMock()
with patch('sqlalchemy.ext.asyncio.create_async_engine', return_value=mock_engine):
    with patch('sqlalchemy.ext.asyncio.async_sessionmaker', return_value=MagicMock()):
        from app.services.campus_location_service import (
            CAMPUS_LOCATIONS, CampusLocation,
            list_campus_locations, get_campus_location,
            search_campus_locations, find_best_location,
        )


class TestListCampusLocations:
    def test_returns_all_locations(self):
        locs = list_campus_locations()
        assert len(locs) >= 15  # 8 nanwangshan + 7 future_city

    def test_each_location_has_id_name_campus(self):
        for loc in list_campus_locations():
            assert 'id' in loc
            assert 'name' in loc
            assert 'campus' in loc

    def test_campus_field_values(self):
        locs = list_campus_locations()
        campuses = {l['campus'] for l in locs}
        assert 'nanwangshan' in campuses
        assert 'future_city' in campuses


class TestGetCampusLocation:
    def test_existing_id_returns_location(self):
        loc = get_campus_location("library")
        assert loc is not None
        assert loc['name'] == "图书馆"
        assert loc['campus'] == "nanwangshan"

    def test_nonexistent_id_returns_none(self):
        assert get_campus_location("nonexistent_xyz") is None

    def test_future_city_location(self):
        loc = get_campus_location("future-library")
        assert loc is not None
        assert loc['campus'] == "future_city"
        assert "图书馆" in loc['name']


class TestSearchCampusLocations:
    def test_keyword_finds_by_name(self):
        results = search_campus_locations("图书馆")
        names = [r['name'] for r in results]
        assert any("图书馆" in n for n in names)

    def test_keyword_finds_by_alias(self):
        results = search_campus_locations("一教")
        names = [r['name'] for r in results]
        assert any("第一教学楼" in n for n in names)

    def test_empty_keyword_returns_all(self):
        results = search_campus_locations("")
        assert len(results) >= 15

    def test_nonexistent_keyword_returns_empty(self):
        results = search_campus_locations("火星基地")
        assert len(results) == 0

    def test_campus_filter_nanwangshan(self):
        results = search_campus_locations("楼")
        nanwangshan = [r for r in results if r.get('campus') == 'nanwangshan']
        assert len(nanwangshan) > 0


class TestFindBestLocation:
    def test_exact_name_match_returns_first(self):
        result = find_best_location("图书馆")
        assert result is not None
        assert "图书馆" in result['name']

    def test_partial_match_works(self):
        result = find_best_location("食堂")
        assert result is not None
        assert "食堂" in result['name']

    def test_future_city_match(self):
        result = find_best_location("未来城")
        assert result is not None
        assert result['campus'] == 'future_city'

    def test_no_match_returns_none(self):
        assert find_best_location("xyz不存在的") is None


class TestCampusLocationDataclass:
    def test_to_dict_includes_map_url(self):
        loc = CAMPUS_LOCATIONS[0]
        d = loc.to_dict()
        assert 'mapUrl' in d
        assert d['id'] == loc.id
        assert d['name'] == loc.name
