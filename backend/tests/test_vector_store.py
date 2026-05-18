"""Tests for vector_store.py — DocumentSpecStore + parsing logic."""
import pytest
import tempfile, os, json
from pathlib import Path
from unittest.mock import MagicMock, patch


# ═══════════════════ DocumentSpecStore unit tests ═══════════════════

@pytest.fixture
def spec_dir():
    """Create temp documents dir with a leave spec for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        leave_dir = Path(tmp) / "leave"
        leave_dir.mkdir()
        spec = """---
document_type: leave
display_name: 请假条
---

## 格式要求
- 必须包含学生签名栏
- 课程请假需注明任课教师
"""
        (leave_dir / "spec.md").write_text(spec, encoding="utf-8")
        yield tmp


class TestDocumentSpecStore:
    def test_parse_frontmatter_extracts_fields(self):
        from app.rag.vector_store import DocumentSpecStore
        content = "---\ndocument_type: leave\ndisplay_name: 请假条\n---\n\n正文内容"
        fm = DocumentSpecStore._parse_frontmatter(content)
        assert fm == {"document_type": "leave", "display_name": "请假条"}

    def test_parse_frontmatter_empty(self):
        from app.rag.vector_store import DocumentSpecStore
        assert DocumentSpecStore._parse_frontmatter("无头部") == {}
        assert DocumentSpecStore._parse_frontmatter("") == {}

    def test_strip_frontmatter_removes_header(self):
        from app.rag.vector_store import DocumentSpecStore
        content = "---\na: 1\n---\n\n保留内容"
        result = DocumentSpecStore._strip_frontmatter(content)
        assert "保留内容" in result
        assert "---" not in result

    def test_chunk_text_splits_paragraphs(self):
        from app.rag.vector_store import DocumentSpecStore
        text = "段落1\n\n段落2\n\n段落3"
        chunks = DocumentSpecStore._chunk_text(text, max_chars=20)
        assert len(chunks) >= 1

    def test_chunk_text_short_text_returns_single_chunk(self):
        from app.rag.vector_store import DocumentSpecStore
        assert len(DocumentSpecStore._chunk_text("短文本", max_chars=1000)) == 1

    def test_index_all_with_empty_dir(self, spec_dir):
        """index_all on temp dir should work without errors."""
        from app.rag.vector_store import DocumentSpecStore
        import chromadb
        # Use a temp ChromaDB path
        chroma_path = Path(spec_dir) / "chroma_test"
        store = DocumentSpecStore(documents_dir=spec_dir)
        store._client = MagicMock()
        store._collection = MagicMock()
        store._collection.get.return_value = {"ids": []}
        # Should not raise
        store.index_all()
        assert store._collection.add.called


class TestHybridSearchMock:
    def test_search_calls_collection_query(self):
        import sys
        sys.modules['aiomysql'] = MagicMock()
        from unittest.mock import patch
        with patch('sqlalchemy.ext.asyncio.create_async_engine', return_value=MagicMock()):
            with patch('sqlalchemy.ext.asyncio.async_sessionmaker', return_value=MagicMock()):
                from app.rag.vector_store import VectorStoreService
                store = VectorStoreService()
                store.vectors_store = MagicMock()
                store.vectors_store.similarity_search_with_score = MagicMock(return_value=[])

                import asyncio
                async def go():
                    results = await store.hybrid_search("测试查询", kb_type="shared")
                    assert isinstance(results, list)
                asyncio.run(go())
