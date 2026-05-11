# Document Generation Framework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded leave-request generation with a configurable template-based document framework driven by Agent conversation, with schedule integration for auto-detecting course leave details.

**Architecture:** New `documents/` directory at project root holds per-type config (template.docx + spec.md + fields.json). A generic `DocumentGenerator` fills `{{placeholders}}` in templates. A single `doc_preview` Agent tool does two-phase flow: preview (RAG match + auto-fill from Django + auto-detect from schedule + LLM extract) then generate (fill template). Old leave-specific files are removed.

**Key enhancement over spec:** For course leave variant, the tool queries the user's actual schedule to auto-detect which course they're missing — teacher name, course time, location are pulled from schedule data instead of requiring manual input.

**Tech Stack:** Python 3.12, python-docx, FastAPI, LangChain tool decorator, ChromaDB, Vue 3 + Element Plus

---

### Task 1: Create configuration layer — documents/leave/

**Files:**
- Create: `documents/leave/template.docx`
- Create: `documents/leave/spec.md`
- Create: `documents/leave/fields.json`
- Modify: `docker-compose.yml` (volume mount + env var)

- [ ] **Step 1: Create documents/leave/ directory**

```bash
mkdir -p /root/zhsx/documents/leave
```

- [ ] **Step 2: Write fields.json**

Write `/root/zhsx/documents/leave/fields.json`:

```json
{
  "display_name": "请假条",
  "required": ["name", "student_id", "class_name", "reason", "start_date", "end_date"],
  "optional": ["teacher_name", "course_name", "recipient_type", "duration_days", "start_time", "end_time", "student_phone", "parent_phone", "signature", "sign_date"],
  "auto_fill": ["name", "student_id", "class_name"],
  "variants": {
    "course_leave": {
      "label": "课程请假",
      "required": ["recipient_type"],
      "optional": ["teacher_name", "course_name", "start_time", "end_time"],
      "auto_detect_from_schedule": true
    },
    "long_leave": {
      "label": "长假期请假",
      "required": [],
      "optional": ["destination", "relative_relation", "relative_phone"]
    }
  }
}
```

- [ ] **Step 3: Write spec.md**

Write `/root/zhsx/documents/leave/spec.md`:

```markdown
---
document_type: leave
display_name: 请假条
---

## 格式要求
- 课程请假条需注明：收件人（任课教师或学工组）、请假时间、原因、学生签名、日期
- 长假期请假条需注明：离校/返校时间、亲属联系方式、去向、班主任和辅导员签字
- 必须包含学生签名栏和日期
- 课程请假需注明任课教师姓名（若交给任课老师）
- 长期请假需包含家长联系方式及班主任审批栏

## 学校规定
根据《学生手册》请假管理规定：
- 学生请假须经任课教师同意或向学工组备案
- 长期离校需经班主任和辅导员双重审批
- 返校后及时销假
- 未按要求履行请假手续者，按学校规定视情节轻重给予违纪处分
```

- [ ] **Step 4: Create template.docx with placeholders**

Write `/tmp/create_leave_template.py`:

```python
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(3)

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("学 生 请 假 条")
run.font.size = Pt(16)
run.bold = True

doc.add_paragraph("尊敬的 {{teacher_name}} 老师：")
doc.add_paragraph("")

doc.add_paragraph("    我是 {{class_name}} 班学生 {{name}}，学号 {{student_id}}，因 {{reason}}，需请假 {{duration_days}} 天，时间从 {{start_date}} {{start_time}} 至 {{end_date}} {{end_time}}。")
doc.add_paragraph("")

doc.add_paragraph("    本人已经将请假事宜及时告知家长，且本人承诺请假期间注意安全，若有安全事故发生，个人按照学校有关管理规定承担相应责任。")
doc.add_paragraph("    特此请假。")
doc.add_paragraph("")

doc.add_paragraph("本人联系方式：{{student_phone}}    家长联系方式：{{parent_phone}}")
doc.add_paragraph("")

doc.add_paragraph("本人签名：{{signature}}")
doc.add_paragraph("日期：{{sign_date}}")

doc.save("/root/zhsx/documents/leave/template.docx")
print("template.docx created")
```

Run:

```bash
cd /root/zhsx && python3 /tmp/create_leave_template.py
```

Expected: prints "template.docx created"

- [ ] **Step 5: Add documents volume mount to docker-compose.yml**

In `/root/zhsx/docker-compose.yml`, under the `backend` service `volumes` section, add:

```yaml
    volumes:
      - backend_data:/app/data
      - ./Training Program:/Training Program:ro
      - ./documents:/app/documents:ro
```

And add to `environment`:

```yaml
      DOCUMENTS_DIR: /app/documents
```

- [ ] **Step 6: Commit**

```bash
cd /root/zhsx && git add documents/ docker-compose.yml && git commit -m "feat: add documents configuration layer — leave template + spec + fields"
```

---

### Task 2: Create DocumentGenerator service

**Files:**
- Create: `backend/app/services/document_generator.py`
- Test: `backend/tests/test_document_generator.py`

- [ ] **Step 1: Write failing test**

Write `/root/zhsx/backend/tests/test_document_generator.py`:

```python
import io
from pathlib import Path
import pytest
from docx import Document


@pytest.fixture
def templates_dir(tmp_path):
    doc_dir = tmp_path / "leave"
    doc_dir.mkdir(parents=True)
    doc = Document()
    doc.add_paragraph("Name: {{name}}")
    doc.add_paragraph("ID: {{student_id}}")
    doc.save(str(doc_dir / "template.docx"))
    return tmp_path


def test_document_generator_fills_placeholders(templates_dir):
    from app.services.document_generator import DocumentGenerator

    gen = DocumentGenerator(templates_dir, templates_dir / "tmp")
    output = gen.generate("leave", {"name": "张三", "student_id": "20230001"})

    assert output.exists()
    result = Document(str(output))
    text = "\n".join(p.text for p in result.paragraphs)
    assert "张三" in text
    assert "20230001" in text
    assert "{{name}}" not in text


def test_document_generator_unfilled_placeholders_become_blanks(templates_dir):
    from app.services.document_generator import DocumentGenerator

    gen = DocumentGenerator(templates_dir, templates_dir / "tmp")
    output = gen.generate("leave", {})

    result = Document(str(output))
    text = "\n".join(p.text for p in result.paragraphs)
    assert "________" in text


def test_document_generator_sign_date_auto_filled(templates_dir):
    from datetime import date
    from app.services.document_generator import DocumentGenerator

    doc_dir = templates_dir / "leave2"
    doc_dir.mkdir(parents=True)
    doc = Document()
    doc.add_paragraph("Date: {{sign_date}}")
    doc.save(str(doc_dir / "template.docx"))

    gen = DocumentGenerator(templates_dir, templates_dir / "tmp")
    output = gen.generate("leave2", {"reason": "sick"})

    result = Document(str(output))
    text = "\n".join(p.text for p in result.paragraphs)
    today_str = date.today().strftime("%Y年%m月%d日")
    assert today_str in text
```

Run:

```bash
cd /root/zhsx/backend && uv run pytest tests/test_document_generator.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: Write DocumentGenerator implementation**

Write `/root/zhsx/backend/app/services/document_generator.py`:

```python
import uuid
from datetime import date
from pathlib import Path

from docx import Document


class DocumentGenerator:
    """Generic template filler. Reads template.docx, replaces {{placeholders}}, saves result."""

    def __init__(self, documents_dir: Path, temp_dir: Path):
        self.documents_dir = Path(documents_dir)
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, doc_type: str, fields: dict[str, str]) -> Path:
        template_path = self.documents_dir / doc_type / "template.docx"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        doc = Document(str(template_path))

        # Auto-fill sign_date if not provided
        if not fields.get("sign_date"):
            fields = {**fields, "sign_date": date.today().strftime("%Y年%m月%d日")}

        # Replace in paragraphs
        for paragraph in doc.paragraphs:
            self._replace_in_paragraph(paragraph, fields)

        # Replace in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._replace_in_paragraph(paragraph, fields)

        output_path = self.temp_dir / f"{doc_type}_{uuid.uuid4().hex[:12]}.docx"
        doc.save(str(output_path))
        return output_path

    @staticmethod
    def _replace_in_paragraph(paragraph, fields: dict[str, str]) -> None:
        for key, value in fields.items():
            placeholder = f"{{{{{key}}}}}"
            display = value if value else "________"
            for run in paragraph.runs:
                if placeholder in run.text:
                    run.text = run.text.replace(placeholder, display)
```

- [ ] **Step 3: Run tests to verify pass**

```bash
cd /root/zhsx/backend && uv run pytest tests/test_document_generator.py -v
```

Expected: 3 PASS

- [ ] **Step 4: Commit**

```bash
cd /root/zhsx && git add backend/app/services/document_generator.py backend/tests/test_document_generator.py && git commit -m "feat: add DocumentGenerator — generic template filling engine"
```

---

### Task 3: Create documents API router (download endpoint + old path redirect)

**Files:**
- Create: `backend/app/router/documents.py`
- Create: `backend/app/router/leave_redirect.py`

- [ ] **Step 1: Write the documents router**

Write `/root/zhsx/backend/app/router/documents.py`:

```python
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from app.core.rate_limit import rate_limit

documents_router = APIRouter(prefix="/api/documents", tags=["documents"])

_TEMP_DIR = Path(os.getenv("DOCUMENTS_TEMP_DIR", "/tmp/documents"))
_TEMP_DIR.mkdir(parents=True, exist_ok=True)


@documents_router.get("/download/{file_id}")
async def download_document(
    file_id: str,
    _: None = Depends(rate_limit(limit=30, window=60)),
):
    """Download a generated document."""
    file_path = _TEMP_DIR / f"{file_id}.docx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期，请重新生成。")

    return FileResponse(
        path=str(file_path),
        filename=f"{file_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def cleanup_old_files(temp_dir: Path | None = None, max_age_seconds: int = 1800):
    """Delete files older than max_age_seconds."""
    import time
    d = temp_dir or _TEMP_DIR
    now = time.time()
    for f in d.glob("*.docx"):
        if now - f.stat().st_mtime > max_age_seconds:
            f.unlink(missing_ok=True)
```

- [ ] **Step 2: Write the backward-compatible redirect**

Write `/root/zhsx/backend/app/router/leave_redirect.py`:

```python
"""Redirect old /api/leave/download/* → new /api/documents/download/* (30-day compat window)."""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

leave_redirect_router = APIRouter(prefix="/api/leave", tags=["leave-compat"])


@leave_redirect_router.get("/download/{file_id}")
async def redirect_leave_download(file_id: str):
    return RedirectResponse(
        url=f"/api/documents/download/{file_id}",
        status_code=307,  # temporary redirect
    )
```

Note: `status_code=307` (Temporary Redirect), not 301, because the old path will eventually be removed.

- [ ] **Step 3: Commit**

```bash
cd /root/zhsx && git add backend/app/router/documents.py backend/app/router/leave_redirect.py && git commit -m "feat: add documents download endpoint + leave redirect compatibility"
```

---

### Task 4: Support infrastructure — Django user client + ChromaDB spec indexing + schedule lookup

**Files:**
- Create: `backend/app/utils/django_user_client.py`
- Modify: `backend/app/rag/vector_store.py` (add DocumentSpecStore)
- Modify: `backend/main.py` (index on startup)

- [ ] **Step 1: Write Django user profile client**

Write `/root/zhsx/backend/app/utils/django_user_client.py`:

```python
import os
import requests
from app.core.logger_handler import logger

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8001")


def fetch_user_profile(user_id: str) -> dict | None:
    """Fetch user profile from Django. Returns dict with name, student_id, class_name or None."""
    try:
        url = f"{DJANGO_API_URL}/user/profile/{user_id}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            logger.info(f"Fetched user profile for {user_id}")
            return resp.json()
        logger.warning(f"Django profile fetch failed: {resp.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Django profile fetch error: {e}")
        return None
```

- [ ] **Step 2: Add DocumentSpecStore to vector_store.py**

Read `/root/zhsx/backend/app/rag/vector_store.py` first, then append at the bottom:

```python
# ── Document Spec Store ──────────────────────────────────────────

import json
import os
import re
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings


class DocumentSpecStore:
    """ChromaDB-backed store for document type specs (spec.md files)."""
    COLLECTION_NAME = "document_specs"

    def __init__(self, documents_dir: str | None = None):
        self.documents_dir = Path(documents_dir or os.getenv("DOCUMENTS_DIR", "/app/documents"))
        chroma_dir = os.getenv("CHROMA_DB_PATH", "./chromadb")
        self._client = chromadb.PersistentClient(
            path=str(Path(chroma_dir) / "document_specs"),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(self.COLLECTION_NAME)
        return self._collection

    def index_all(self):
        """Scan documents/*/spec.md and index into ChromaDB."""
        ids, documents, metadatas = [], [], []
        for spec_path in sorted(self.documents_dir.glob("*/spec.md")):
            doc_type = spec_path.parent.name
            content = spec_path.read_text(encoding="utf-8")
            frontmatter = self._parse_frontmatter(content)
            body = self._strip_frontmatter(content)
            chunks = self._chunk_text(body)
            for i, chunk in enumerate(chunks):
                ids.append(f"{doc_type}_{i}")
                documents.append(chunk)
                metadatas.append({
                    "document_type": frontmatter.get("document_type", doc_type),
                    "display_name": frontmatter.get("display_name", doc_type),
                    "source_file": str(spec_path),
                    "chunk_index": i,
                })

        if ids:
            try:
                existing = self.collection.get()["ids"]
                if existing:
                    self.collection.delete(ids=existing)
            except Exception:
                pass
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(self, query: str, k: int = 3) -> list[dict]:
        """Search for matching document specs. Returns list of {id, text, score, metadata}."""
        results = self.collection.query(query_texts=[query], n_results=k)
        items = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                items.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "score": results["distances"][0][i] if results["distances"] else 0.0,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                })
        return items

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not m:
            return {}
        result = {}
        for line in m.group(1).strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip()
        return result

    @staticmethod
    def _strip_frontmatter(content: str) -> str:
        return re.sub(r'^---\s*\n.*?\n---\s*\n?', '', content, flags=re.DOTALL).strip()

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 1000) -> list[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= max_chars:
                current = f"{current}\n\n{p}".strip()
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)
        return chunks or [text]


# Singleton — populated at startup
document_spec_store = DocumentSpecStore()
```

- [ ] **Step 3: Add spec indexing to FastAPI startup**

In `/root/zhsx/backend/main.py`, add import:

```python
from app.rag.vector_store import document_spec_store
```

Add inside `startup_event()`, after the existing init calls:

```python
    # Index document specs
    try:
        document_spec_store.index_all()
        logger.info("Document specs indexed successfully")
    except Exception as e:
        logger.warning(f"Document spec indexing skipped: {e}")
```

- [ ] **Step 4: Add schedule lookup helper for course leave**

In `/root/zhsx/backend/app/agent/agent_tools.py`, add a helper function (will be used in Task 5):

```python
async def _lookup_schedule_for_leave(user_id: str, target_date: str | None = None) -> list[dict]:
    """Look up user's schedule to auto-detect course details for course leave.
    Returns list of matching schedule events with teacher/course/time info.
    """
    import datetime
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_labels = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                      "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}

    target_wd = None
    if target_date:
        try:
            dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
            target_wd = weekdays[dt.weekday()]
        except ValueError:
            pass

    if not target_wd:
        target_wd = weekdays[datetime.datetime.now().weekday()]

    async with AsyncSessionLocal() as db:
        events = await svc_list_week_events(db, user_id)

    matching = []
    for e in events:
        if e.weekday == target_wd:
            matching.append({
                "title": e.title,
                "weekday": weekday_labels.get(e.weekday, e.weekday),
                "start_time": e.startTime,
                "end_time": e.endTime,
                "location": e.location or "",
                "date": e.date or target_date or "",
            })

    return matching
```

This function is placed in `agent_tools.py` so it can share the existing `_current_user_id`, `AsyncSessionLocal`, and `svc_list_week_events` imports. The doc_preview tool (Task 5) calls it to find which course(s) the student has at the specified time.

- [ ] **Step 5: Commit**

```bash
cd /root/zhsx && git add backend/app/utils/django_user_client.py backend/app/rag/vector_store.py backend/main.py backend/app/agent/agent_tools.py && git commit -m "feat: add Django user client + ChromaDB doc spec indexing + schedule lookup helper"
```

---

### Task 5: Replace generate_leave_request tool with doc_preview

**Files:**
- Modify: `backend/app/agent/agent_tools.py`

- [ ] **Step 1: Remove old generate_leave_request**

In `/root/zhsx/backend/app/agent/agent_tools.py`:

Remove import lines:
```python
from app.schemas.leave import CourseLeaveRequest, LongLeaveRequest
from app.services.leave_service import generate_leave_docx
```

Remove the entire `_TEMP_DIR` constant and `generate_leave_request` function (lines 235-345 of the current file).

- [ ] **Step 2: Add new imports and constants at top of file**

Add after the existing import block:

```python
import json
import os
from pathlib import Path
from app.services.document_generator import DocumentGenerator
from app.utils.django_user_client import fetch_user_profile
```

Add near other module-level constants:

```python
_DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", "/app/documents"))
_DOCUMENTS_TEMP_DIR = Path(os.getenv("DOCUMENTS_TEMP_DIR", "/tmp/documents"))
```

- [ ] **Step 3: Add helper functions**

Add after the `_lookup_schedule_for_leave` function (already added in Task 4):

```python
def _load_fields_config(doc_type: str) -> dict:
    """Load fields.json for a document type."""
    fields_path = _DOCUMENTS_DIR / doc_type / "fields.json"
    if not fields_path.exists():
        return {}
    return json.loads(fields_path.read_text(encoding="utf-8"))


def _match_document_type(query: str) -> tuple:
    """RAG-match query to document type. Returns (doc_type | None, spec_snippet | None)."""
    try:
        # Lazy import to avoid circular dependency at module load time
        from app.rag.vector_store import document_spec_store
        results = document_spec_store.search(query, k=3)
        if results and len(results) > 0:
            metadata = results[0].get("metadata", {})
            doc_type = metadata.get("document_type", "")
            snippet = results[0].get("text", "")
            return doc_type, snippet
    except Exception:
        pass
    return None, None
```

Note: `document_spec_store` is imported lazily inside `_match_document_type` to avoid circular import — `vector_store.py` imports from `rag_service.py` which may reference modules that import from `agent_tools.py`.

- [ ] **Step 4: Write the doc_preview tool**

Add after `recommend_courses`:

```python
# ── Document generation tool ──────────────────────────────────────

@tool(description="""通用文书生成工具。根据对话生成校园文书（请假条、申请、证明等）。

工作方式：
1. 首次调用: doc_preview(query=用户原文) → 返回预览卡片
2. 用户确认后: doc_preview(query=用户原文, confirmed=True, params={所有字段,_doc_type,_variant})

你必须在第一次调用后等待用户确认，不要跳过确认步骤。params中包含variant字段用于区分子类型（如course_leave/long_leave）。
对于课程请假，系统会自动从课表中查找对应课程信息（教师、时间、课程名）。""")
async def doc_preview(
    query: str,
    confirmed: bool = False,
    params: dict = None,
) -> str:
    import uuid
    import datetime

    if params is None:
        params = {}

    user_id = _current_user_id.get()

    # ── Phase 2: Generate ──
    if confirmed and params:
        doc_type = params.pop("_doc_type", None)
        variant = params.pop("_variant", None)
        if not doc_type:
            doc_type, _ = _match_document_type(query)
        if not doc_type:
            return "无法确定文书类型，请重新描述你的需求。"

        fields_config = _load_fields_config(doc_type)
        required = list(fields_config.get("required", []))

        if variant and "variants" in fields_config:
            variant_cfg = fields_config["variants"].get(variant, {})
            required = required + list(variant_cfg.get("required", []))

        missing = [f for f in required if not params.get(f)]
        if missing:
            labels = ", ".join(_FIELD_LABELS.get(f, f) for f in missing)
            return f"以下必填字段缺失：{labels}。请补充后重新确认。"

        gen = DocumentGenerator(_DOCUMENTS_DIR, _DOCUMENTS_TEMP_DIR)
        output_path = gen.generate(doc_type, params)
        file_id = output_path.stem
        file_size = output_path.stat().st_size
        size_str = f"{file_size / 1024:.1f} KB" if file_size > 1024 else f"{file_size} B"

        display_name = fields_config.get("display_name", doc_type)
        return json.dumps({
            "type": "document_result",
            "doc_type": doc_type,
            "display_name": display_name,
            "file_name": f"{file_id}.docx",
            "file_size": size_str,
            "download_url": f"/api/documents/download/{file_id}",
            "expires_in": "30 分钟",
        }, ensure_ascii=False)

    # ── Phase 1: Preview ──
    doc_type, spec_snippet = _match_document_type(query)
    if not doc_type:
        return "暂不支持该文书类型。目前支持的文书：请假条。请描述你需要生成哪种文书。"

    fields_config = _load_fields_config(doc_type)
    if not fields_config:
        return f"文书类型「{doc_type}」的字段配置缺失，请联系管理员。"

    display_name = fields_config.get("display_name", doc_type)
    auto_fill_keys = fields_config.get("auto_fill", [])
    required_keys = list(fields_config.get("required", []))
    optional_keys = list(fields_config.get("optional", []))

    # Determine variant
    variant = params.get("variant", "")
    variant_label = ""
    auto_detect_schedule = False
    if "variants" in fields_config:
        if not variant:
            variant = next(iter(fields_config["variants"].keys()))
        variant_cfg = fields_config["variants"].get(variant, {})
        variant_label = variant_cfg.get("label", variant)
        required_keys = required_keys + list(variant_cfg.get("required", []))
        optional_keys = optional_keys + list(variant_cfg.get("optional", []))
        auto_detect_schedule = variant_cfg.get("auto_detect_from_schedule", False)

    # Step A: Auto-fill from Django user profile
    auto_filled = []
    if user_id and auto_fill_keys:
        try:
            profile = fetch_user_profile(user_id)
            if profile:
                key_map = {"name": "name", "student_id": "student_id", "class_name": "class_name"}
                for key in auto_fill_keys:
                    profile_key = key_map.get(key, key)
                    value = profile.get(profile_key, "")
                    if value:
                        params[key] = value
                        auto_filled.append({
                            "key": key, "label": _FIELD_LABELS.get(key, key),
                            "value": str(value), "source": "account",
                        })
        except Exception:
            pass

    # Step B: Auto-detect from schedule (course leave only)
    schedule_courses = []
    if auto_detect_schedule and user_id:
        target_date = params.get("start_date", "")
        try:
            schedule_courses = await _lookup_schedule_for_leave(user_id, target_date or None)
        except Exception:
            pass

        if schedule_courses:
            # If LLM specified a time range, filter matching courses
            target_start = params.get("start_time", "")
            target_end = params.get("end_time", "")
            if target_start or target_end:
                schedule_courses = [
                    c for c in schedule_courses
                    if (not target_start or c["start_time"] == target_start)
                    and (not target_end or c["end_time"] == target_end)
                ]

            if len(schedule_courses) == 1:
                c = schedule_courses[0]
                for field_key, course_key in [
                    ("teacher_name", "title"), ("start_time", "start_time"),
                    ("end_time", "end_time"), ("course_name", "title"),
                ]:
                    val = c.get(course_key, "")
                    if val and field_key in optional_keys + required_keys:
                        params[field_key] = val
                # Add as auto-detected info in preview
                auto_filled.append({
                    "key": "course_info", "label": "匹配课表",
                    "value": f"{c['weekday']} {c['start_time']}-{c['end_time']} {c['title']}",
                    "source": "schedule",
                })

            elif len(schedule_courses) > 1:
                # Multiple matches — show as extracted options
                for c in schedule_courses:
                    extracted.append({
                        "key": "course_option", "label": "可选课程",
                        "value": f"{c['weekday']} {c['start_time']}-{c['end_time']} {c['title']}",
                        "source": "schedule",
                    })

    # Step C: Extract from LLM-provided params (from conversation understanding)
    extracted = list(params.get("_extracted", []))  # re-use if already set
    for key in required_keys + optional_keys:
        if key in auto_fill_keys:
            continue
        val = params.get(key, "")
        if val and not any(e["key"] == key for e in extracted):
            extracted.append({
                "key": key, "label": _FIELD_LABELS.get(key, key),
                "value": str(val),
            })

    # Step D: Determine missing
    missing = []
    for key in required_keys:
        if key not in auto_fill_keys and not params.get(key):
            missing.append({
                "key": key, "label": _FIELD_LABELS.get(key, key), "required": True,
            })

    hint = "回复"确认"生成文档，或回复补充信息" if missing else "回复"确认"生成文档，或回复修改"

    return json.dumps({
        "type": "document_preview",
        "doc_type": doc_type,
        "display_name": display_name,
        "variant": variant,
        "variant_label": variant_label,
        "fields": {
            "auto_filled": auto_filled,
            "extracted": extracted,
            "missing": missing,
        },
        "spec_reference": spec_snippet or "",
        "hint": hint,
    }, ensure_ascii=False)


_FIELD_LABELS = {
    "name": "姓名", "student_id": "学号", "class_name": "班级",
    "reason": "请假原因", "start_date": "开始日期", "end_date": "结束日期",
    "start_time": "开始时间", "end_time": "结束时间", "duration_days": "请假天数",
    "teacher_name": "教师姓名", "course_name": "课程名称", "recipient_type": "收件人",
    "student_phone": "本人电话", "parent_phone": "家长电话",
    "signature": "签名", "sign_date": "签字日期",
    "destination": "去向", "relative_relation": "亲属关系", "relative_phone": "亲属电话",
}
```

- [ ] **Step 5: Commit**

```bash
cd /root/zhsx && git add backend/app/agent/agent_tools.py && git commit -m "feat: replace generate_leave_request with generic doc_preview tool + schedule auto-detect"
```

---

### Task 6: Update Agent tool registration and system prompt

**Files:**
- Modify: `backend/app/agent/agent.py`
- Modify: `backend/app/prompt/main_prompt.txt`

- [ ] **Step 1: Update tool imports in agent.py**

In `/root/zhsx/backend/app/agent/agent.py`, replace import:
```python
    generate_leave_request,
```
with:
```python
    doc_preview,
```

In `_get_default_tools()`, replace:
```python
            generate_leave_request,
```
with:
```python
            doc_preview,
```

- [ ] **Step 2: Update system prompt**

In `/root/zhsx/backend/app/prompt/main_prompt.txt`, add after the "### 辅助工具" section:

```
### 文书生成
- `doc_preview` — 通用文书生成（请假条、申请、证明等）。参数：query（用户原始请求），confirmed（用户确认后设为true），params（确认后包含所有字段值的字典，含_doc_type和_variant）

工作流程：
1. 第一次调用 doc_preview(query=用户原文) → 获取预览
2. 将预览展示给用户（标注自动补全、对话提取、缺失字段）
3. 用户确认/补充信息后，第二次调用 doc_preview(query=用户原文, confirmed=True, params={所有字段加_doc_type和_variant})
4. 展示下载链接

课程请假时系统自动从课表匹配课程信息。你必须等待用户确认，不要跳过。
```

End of "典型场景处理" section, add:

```
**文书生成**："帮我写个请假条" → doc_preview(query="帮我写个请假条") → 展示预览卡片 → 等用户确认 → doc_preview(query=..., confirmed=True, params={...})
```

- [ ] **Step 3: Commit**

```bash
cd /root/zhsx && git add backend/app/agent/agent.py backend/app/prompt/main_prompt.txt && git commit -m "feat: register doc_preview tool + update system prompt"
```

---

### Task 7: Register documents router, remove old leave files

**Files:**
- Modify: `backend/main.py`
- Remove: `backend/app/router/leave.py`
- Remove: `backend/app/services/leave_service.py`
- Remove: `backend/app/schemas/leave.py`

- [ ] **Step 1: Update router registration in main.py**

In `/root/zhsx/backend/main.py`, replace:
```python
from app.router.leave import leave_router
```
with:
```python
from app.router.documents import documents_router
from app.router.leave_redirect import leave_redirect_router
```

Replace `app.include_router(leave_router)` with:
```python
app.include_router(documents_router)
app.include_router(leave_redirect_router)
```

- [ ] **Step 2: Remove old leave files**

```bash
rm /root/zhsx/backend/app/router/leave.py
rm /root/zhsx/backend/app/services/leave_service.py
rm /root/zhsx/backend/app/schemas/leave.py
```

- [ ] **Step 3: Verify imports are clean**

```bash
cd /root/zhsx/backend && python3 -c "from app.main import app; print('Import OK')" 2>&1
```

Expected: "Import OK" (may show warnings but should not error).

- [ ] **Step 4: Commit**

```bash
cd /root/zhsx && git add backend/main.py && git rm backend/app/router/leave.py backend/app/services/leave_service.py backend/app/schemas/leave.py && git commit -m "feat: register documents router, remove old leave-specific files"
```

---

### Task 8: Frontend — Add document_preview and document_result card rendering

**Files:**
- Modify: `front/src/views/AIChat.vue`

- [ ] **Step 1: Add new card types to normalizeCardType**

In `normalizeCardType()` (around line 340), add to the `mapping` object:

```js
    document_preview: 'document_preview',
    document_result: 'document_result',
```

- [ ] **Step 2: Add card type labels**

In `getResultCardTypeLabel()` (around line 383), add to `labelMap`:

```js
    document_preview: '文书预览',
    document_result: '文书已生成',
```

- [ ] **Step 3: Add normalization logic**

In `normalizeResultCard()` (around line 424), add before `return null` at the end:

```js
  if (type === 'document_preview') {
    return {
      ...baseCard,
      docType: rawCard.doc_type || rawCard.docType || '',
      displayName: rawCard.display_name || rawCard.displayName || '',
      variant: rawCard.variant || '',
      variantLabel: rawCard.variant_label || rawCard.variantLabel || '',
      autoFilled: toArray(rawCard.fields?.auto_filled || rawCard.auto_filled || rawCard.autoFilled || []),
      extracted: toArray(rawCard.fields?.extracted || rawCard.extracted || []),
      missing: toArray(rawCard.fields?.missing || rawCard.missing || []),
      specReference: rawCard.spec_reference || rawCard.specReference || '',
      hint: rawCard.hint || '',
    };
  }

  if (type === 'document_result') {
    return {
      ...baseCard,
      docType: rawCard.doc_type || rawCard.docType || '',
      displayName: rawCard.display_name || rawCard.displayName || '',
      fileName: rawCard.file_name || rawCard.fileName || '',
      fileSize: rawCard.file_size || rawCard.fileSize || '',
      downloadUrl: rawCard.download_url || rawCard.downloadUrl || '',
      expiresIn: rawCard.expires_in || rawCard.expiresIn || '',
      specReference: rawCard.spec_reference || rawCard.specReference || '',
    };
  }
```

- [ ] **Step 4: Add card templates**

Locate the card rendering template section (around lines 86-148). Add after the last existing card type block:

```html
                  <!-- 文书预览卡片 -->
                  <div v-else-if="message.resultCard.type === 'document_preview'" class="result-card result-card--document-preview">
                    <div class="result-card__header">
                      <span class="result-card__type-tag">📄 {{ message.resultCard.displayName }}</span>
                      <el-tag v-if="message.resultCard.variantLabel" size="small" type="info">{{ message.resultCard.variantLabel }}</el-tag>
                    </div>

                    <div v-if="message.resultCard.autoFilled.length" class="doc-fields-section">
                      <div class="doc-fields-label">✅ 自动补全</div>
                      <div class="doc-field-row" v-for="f in message.resultCard.autoFilled" :key="f.key">
                        <span class="doc-field-label">{{ f.label }}：</span>
                        <el-tag size="small" :type="f.source === 'schedule' ? 'warning' : 'success'">{{ f.value }}</el-tag>
                        <span v-if="f.source === 'schedule'" class="doc-source-hint">来自课表</span>
                      </div>
                    </div>

                    <div v-if="message.resultCard.extracted.length" class="doc-fields-section">
                      <div class="doc-fields-label">🤖 从对话提取</div>
                      <div class="doc-field-row" v-for="f in message.resultCard.extracted" :key="f.key">
                        <span class="doc-field-label">{{ f.label }}：</span>
                        <el-tag size="small" type="primary">{{ f.value }}</el-tag>
                      </div>
                    </div>

                    <div v-if="message.resultCard.missing.length" class="doc-fields-section">
                      <div class="doc-fields-label">⚠️ 还需要补充</div>
                      <div class="doc-field-row" v-for="f in message.resultCard.missing" :key="f.key">
                        <span class="doc-field-label">{{ f.label }}：</span>
                        <el-tag size="small" type="danger">待填写</el-tag>
                      </div>
                    </div>

                    <div v-if="message.resultCard.specReference" class="doc-spec-ref">
                      📋 {{ message.resultCard.specReference }}
                    </div>
                    <div v-if="message.resultCard.hint" class="doc-hint">
                      💡 {{ message.resultCard.hint }}
                    </div>
                  </div>

                  <!-- 文书结果卡片 -->
                  <div v-else-if="message.resultCard.type === 'document_result'" class="result-card result-card--document-result">
                    <div class="result-card__header">
                      <span class="result-card__type-tag">📄 {{ message.resultCard.displayName }}已生成</span>
                      <span class="result-card__file-size">{{ message.resultCard.fileSize }}</span>
                    </div>
                    <div class="doc-result-info">
                      <div>文件名：{{ message.resultCard.fileName }}</div>
                      <div v-if="message.resultCard.specReference">📋 {{ message.resultCard.specReference }}</div>
                    </div>
                    <el-button type="primary" @click="handleDocDownload(message.resultCard.downloadUrl)">
                      📥 下载文档
                    </el-button>
                    <div class="doc-expiry">链接有效期 {{ message.resultCard.expiresIn }}</div>
                  </div>
```

- [ ] **Step 5: Add handleDocDownload function**

In the `<script setup>` section, add:

```js
const handleDocDownload = (url) => {
  const token = userStore.getToken;
  const fullUrl = url.startsWith('http') ? url : url;
  fetch(fullUrl, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(res => res.blob())
    .then(blob => {
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = '';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    })
    .catch(() => {
      window.open(fullUrl, '_blank', 'noopener,noreferrer');
    });
};
```

Note: `userStore` is already imported and available in AIChat.vue (line 295 of current file).

- [ ] **Step 6: Add scoped CSS**

In the `<style scoped>` section, add:

```css
.result-card--document-preview { border-left-color: #409eff; }
.result-card--document-result { border-left-color: #67c23a; }
.doc-fields-section { margin-bottom: 12px; }
.doc-fields-label { font-size: 13px; color: #606266; margin-bottom: 6px; font-weight: 500; }
.doc-field-row { display: flex; align-items: center; gap: 8px; margin: 4px 0; padding-left: 8px; }
.doc-field-label { font-size: 13px; color: #909399; min-width: 60px; }
.doc-source-hint { font-size: 11px; color: #e6a23c; margin-left: 4px; }
.doc-spec-ref { font-size: 12px; color: #909399; margin-top: 12px; padding-top: 8px; border-top: 1px dashed #e4e7ed; }
.doc-hint { font-size: 13px; color: #e6a23c; margin-top: 8px; }
.doc-result-info { margin-bottom: 12px; font-size: 13px; color: #606266; line-height: 1.8; }
.doc-expiry { font-size: 12px; color: #c0c4cc; margin-top: 6px; }
.result-card__file-size { font-size: 12px; color: #909399; }
```

- [ ] **Step 7: Commit**

```bash
cd /root/zhsx && git add front/src/views/AIChat.vue && git commit -m "feat: add document_preview and document_result card rendering in chat UI"
```

---

### Task 9: Frontend — Remove LeaveRequest page, update router and sidebar

**Files:**
- Remove: `front/src/views/LeaveRequest.vue`
- Modify: `front/src/router/index.js`
- Modify: `front/src/App.vue`
- Modify: `front/src/views/AIChat.vue` (handle query param)

- [ ] **Step 1: Remove LeaveRequest.vue**

```bash
rm /root/zhsx/front/src/views/LeaveRequest.vue
```

- [ ] **Step 2: Remove route from router**

In `/root/zhsx/front/src/router/index.js`, remove the `/leave-request` route block:

```js
  {
    path: '/leave-request',
    name: 'LeaveRequest',
    component: () => import('../views/LeaveRequest.vue'),
    meta: { title: '请假条生成', keepAlive: false }
  },
```

- [ ] **Step 3: Update sidebar in App.vue**

In `/root/zhsx/front/src/App.vue`, replace the "文书辅助" menu item (lines 33-36):

```html
        <el-menu-item index="/leave-request">
          <el-icon><Document /></el-icon>
          <span>文书辅助</span>
        </el-menu-item>
```

with:

```html
        <el-menu-item index="/aichat" @click="openDocChat">
          <el-icon><Document /></el-icon>
          <span>文书辅助</span>
        </el-menu-item>
```

In the `<script setup>` section, add:

```js
const openDocChat = () => {
  router.push({ path: '/aichat', query: { prompt: '帮我写一份文书' } });
};
```

Make sure `useRouter` is already imported. If only `useRoute` is imported, add `useRouter`.

- [ ] **Step 4: Handle query param in AIChat.vue**

In AIChat.vue `<script setup>`, add near other `onMounted` or initialization code:

```js
onMounted(() => {
  if (route.query.prompt && !userInput.value) {
    userInput.value = route.query.prompt;
  }
});
```

If `onMounted` is already used, merge into existing block. Make sure `useRoute` is imported.

- [ ] **Step 5: Commit**

```bash
cd /root/zhsx && git rm front/src/views/LeaveRequest.vue && git add front/src/router/index.js front/src/App.vue front/src/views/AIChat.vue && git commit -m "feat: remove standalone LeaveRequest page, route sidebar to Agent chat"
```

---

### Task 10: Rebuild, deploy, and verify

**Files:** none (verification only)

- [ ] **Step 1: Rebuild Docker images**

```bash
cd /root/zhsx && docker compose build backend frontend
```

Expected: both build successfully (frontend may take 3-5 min).

- [ ] **Step 2: Start all services**

```bash
cd /root/zhsx && docker compose up -d
```

Expected: 5 containers running (`docker compose ps`).

- [ ] **Step 3: Verify document spec indexing**

```bash
docker logs 507-agent-backend 2>&1 | grep -i "spec"
```

Expected: contains "Document specs indexed successfully".

- [ ] **Step 4: Verify old endpoint redirects**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/leave/download/test123
```

Expected: 307.

- [ ] **Step 5: Verify new endpoint exists**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/documents/download/test123
```

Expected: 404 (endpoint exists, file just doesn't exist).

- [ ] **Step 6: End-to-end Agent test**

Get a JWT token and send a streaming query:

```bash
cd /root/zhsx

# Get token (adjust credentials as needed)
TOKEN=$(curl -s -X POST http://localhost:8001/user/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access',''))")

# Send SSE query — should produce doc_preview tool_call
curl -s -N -X POST http://localhost:8000/api/agent/query/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"帮我写个请假条，明天下午去看病","session_id":"e2e-test-001"}' 2>&1 | head -30
```

Expected: SSE stream contains `"tool":"doc_preview"` and a `document_preview` type JSON in the response.

- [ ] **Step 7: Commit any final adjustments**

```bash
cd /root/zhsx && git status && git diff
```

If any fixes were needed during verification, commit them.

---

### Task 11: Push to remote

- [ ] **Step 1: Push all commits**

```bash
cd /root/zhsx && git push origin agent-centric
```

Expected: all commits pushed successfully.
