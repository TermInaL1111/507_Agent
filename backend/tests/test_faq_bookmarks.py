"""Tests for FAQ router + bookmarks router — pure logic, no DB."""
import sys, json, tempfile, os
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.modules['aiomysql'] = MagicMock()
with patch('sqlalchemy.ext.asyncio.create_async_engine', return_value=MagicMock()):
    with patch('sqlalchemy.ext.asyncio.async_sessionmaker', return_value=MagicMock()):
        pass  # prevent import cascade


class TestFaqLoadSave:
    def test_load_empty_returns_default(self):
        """_load_faq returns default when file doesn't exist."""
        from app.router.faq import _load_faq, _FAQ_PATH
        original = str(_FAQ_PATH)
        try:
            import app.router.faq as faq_mod
            faq_mod._FAQ_PATH = Path("/tmp/nonexistent_faq_test.json")
            result = faq_mod._load_faq()
            assert "questions" in result
            assert result["updated_at"] == ""
        finally:
            faq_mod._FAQ_PATH = Path(original)

    def test_save_and_load_roundtrip(self):
        """_save_faq then _load_faq returns same data."""
        import app.router.faq as faq_mod
        tmp = Path("/tmp/faq_test_roundtrip.json")
        try:
            faq_mod._FAQ_PATH = tmp
            data = {"updated_at": "2026-05-14", "questions": [
                {"id": "q1", "question": "测试问题", "pinned": True, "sort": 1}
            ]}
            faq_mod._save_faq(data)
            loaded = faq_mod._load_faq()
            assert loaded["questions"][0]["question"] == "测试问题"
        finally:
            tmp.unlink(missing_ok=True)
            faq_mod._FAQ_PATH = Path(os.getenv("FAQ_PATH", "/app/data/faq.json"))


class TestBookmarkKey:
    def test_bookmark_key_format(self):
        """_bookmark_key returns correct Redis key format."""
        from app.router.bookmarks import _bookmark_key
        assert _bookmark_key("user123") == "bookmarks:user123"
        assert _bookmark_key("") == "bookmarks:"


class TestBookmarkAddRequest:
    def test_valid_request(self):
        from app.router.bookmarks import BookmarkAddRequest
        req = BookmarkAddRequest(content="测试答案", sources=[{"doc_name": "test.pdf"}])
        assert req.content == "测试答案"
        assert len(req.sources) == 1

    def test_empty_sources_allowed(self):
        from app.router.bookmarks import BookmarkAddRequest
        req = BookmarkAddRequest(content="答案")
        assert req.sources == []


class TestFaqSorting:
    def test_pinned_first_sort(self):
        """Questions sorted: pinned first, then by sort field."""
        questions = [
            {"id": "q1", "pinned": False, "sort": 10},
            {"id": "q2", "pinned": True, "sort": 20},
            {"id": "q3", "pinned": False, "sort": 5},
        ]
        questions.sort(key=lambda q: (not q.get("pinned", False), q.get("sort", 99)))
        assert questions[0]["id"] == "q2"  # pinned first
        assert questions[1]["id"] == "q3"  # sort=5 before sort=10
        assert questions[2]["id"] == "q1"
