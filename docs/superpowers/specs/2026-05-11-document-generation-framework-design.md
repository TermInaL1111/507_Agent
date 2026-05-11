# Document Generation Framework — Design Spec

## Overview

Replace the hardcoded leave-request-only generation with a **configurable document generation framework**. New document types are added by dropping 3 files into a directory — zero code changes. The Agent drives the entire flow through conversation, not form-filling.

## Scope

- Build the generic framework: template engine, RAG-based document type matching, Agent tool
- Migrate the existing leave request (请假条) to use the new framework
- Delete the standalone `/leave-request` form page; all interaction moves to Agent chat
- Other document types (scholarship, activity, etc.) are added later by placing files — not in this spec

---

## 1. Configuration Layer

### Directory Structure

Base path: `/root/zhsx/documents/` (project root). Mounted read-only into backend container at `/app/documents/` via docker-compose volume.

```
documents/                          # /root/zhsx/documents/
├── leave/                          # document type = directory name
│   ├── template.docx               # Word template with {{placeholders}}
│   ├── spec.md                     # format spec + school regulations → RAG indexed
│   │   ---
│   │   document_type: leave
│   │   display_name: 请假条
│   │   ---
│   │   # 请假条规范
│   │   ...
│   └── fields.json                 # field definitions
├── scholarship/                    # future: add by dropping folder
│   └── ...
└── activity/                       # future: add by dropping folder
    └── ...
```

### fields.json Schema

```json
{
  "display_name": "请假条",
  "required": ["name", "student_id", "class_name", "reason", "start_date", "end_date"],
  "optional": ["teacher_name", "recipient_type", "duration_days", "start_time", "end_time", "student_phone", "parent_phone", "signature", "sign_date"],
  "auto_fill": ["name", "student_id", "class_name"],
  "variants": {
    "course_leave": {
      "label": "课程请假",
      "required": ["recipient_type"],
      "optional": ["teacher_name"]
    },
    "long_leave": {
      "label": "长假期请假",
      "required": [],
      "optional": ["destination", "relative_relation", "relative_phone"]
    }
  }
}
```

**auto_fill** fields are fetched from Django user service via `user_id` — the Agent never asks for them.

**Variant selection**: When `variants` is present, the LLM determines which variant applies from conversation context (e.g., "请假一天" → `course_leave`, "请假一周回家" → `long_leave`). The LLM includes `variant` in the extracted params. Each variant adds its own `required`/`optional` fields on top of the base fields.

### spec.md Format

Each `spec.md` has YAML frontmatter for structured metadata, followed by free-text format requirements:

```markdown
---
document_type: leave
display_name: 请假条
---

## 格式要求
- 必须包含学生签名栏
- 课程请假：需注明任课教师
- 长期请假：需包含家长联系方式及班主任审批栏
...
```

The full text is chunked and indexed into ChromaDB for RAG retrieval.

---

## 2. Template Engine

### Placeholder Syntax

Templates use `{{field_name}}` placeholders. Both paragraph text and table cells are supported.

### DocumentGenerator Class

```python
class DocumentGenerator:
    """Generic template filler. Reads template.docx, replaces {{placeholders}}, saves result."""

    def __init__(self, documents_dir: Path, temp_dir: Path):
        ...

    def generate(self, doc_type: str, fields: dict[str, str]) -> Path:
        """
        1. Load template at documents/<doc_type>/template.docx
        2. For each paragraph, replace {{key}} with fields[key]
        3. For each table cell, same replacement
        4. Handle today's date: if {{sign_date}} present and not in fields, fill with current date
        5. Save to temp_dir/<doc_type>_<uuid>.docx
        6. Return output path
        """
```

### Key Behaviors

- **Preserves formatting**: only text content is replaced; font, size, margins, alignment from template are kept
- **Tables supported**: iterates `doc.tables` same as `doc.paragraphs`
- **Missing fields**: unfilled placeholders become underlined blanks in output (`____`)
- **Date auto-fill**: `{{sign_date}}` defaults to `datetime.date.today()` if not provided in fields
- **Cleanup**: files older than 30 minutes are deleted on each generation call (same as current)

---

## 3. RAG Document Type Matching

### Indexing

On FastAPI startup event (`app.add_event_handler("startup", ...)`), scan `<documents_dir>/*/spec.md`, split each spec into chunks (with YAML frontmatter as metadata), and upsert into a dedicated ChromaDB collection `document_specs`. Also expose `POST /api/documents/reindex` for manual reindex after adding new document types without restart.

### Matching Flow

```
user query → vector search (ChromaDB) → top-3 candidates → Qwen3-Reranker → best match
```

- If best match score > threshold: read its `fields.json`, proceed
- If score below threshold: return list of available document types, let user choose
- YAML frontmatter `document_type` acts as ground-truth label for evaluation

### Reranker Guard

The Qwen3-Reranker step prevents false matches. A query like "帮我查一下奖学金政策" (inquiring about scholarships) should not match the scholarship application template. The reranker distinguishes "query about X" from "generate document X".

---

## 4. Agent Tool: `doc_preview`

### Tool Signature

```python
@tool
def doc_preview(
    query: str,           # user's original request, used for RAG matching
    confirmed: bool = False,
    params: dict = {}     # key-value field pairs (only meaningful when confirmed=True)
) -> str:
```

### Two-Phase Behavior

**Phase 1 — Preview (confirmed=False):**

1. RAG-match `query` → get `doc_type`
2. Load `documents/<doc_type>/fields.json`
3. For each `auto_fill` field → read `_current_user_id` from contextvar → call Django `GET /user/profile/{user_id}` (via internal HTTP, Django container at `django-user:8001`) → extract field values
4. For each remaining field → extract from `params` (LLM-provided from conversation) or mark as missing
5. If `variants` present, determine variant from `params.variant` (LLM-provided); merge variant-specific required/optional lists
6. Return **document_preview result_card** JSON

**Phase 2 — Generate (confirmed=True):**

1. Validate `params` against `fields.json` — all required must be present
2. Call `DocumentGenerator.generate(doc_type, params)`
3. Return **document_result result_card** JSON with download URL

### Return Format — Preview Card

```json
{
  "type": "document_preview",
  "doc_type": "leave",
  "display_name": "请假条",
  "variant": "course_leave",
  "fields": {
    "auto_filled": [
      {"key": "name", "label": "姓名", "value": "张三", "source": "account"},
      {"key": "student_id", "label": "学号", "value": "20230001", "source": "account"},
      {"key": "class_name", "label": "班级", "value": "计算机2301", "source": "account"}
    ],
    "extracted": [
      {"key": "reason", "label": "请假原因", "value": "看病"},
      {"key": "start_date", "label": "开始日期", "value": "2026-05-12"},
      {"key": "end_date", "label": "结束日期", "value": "2026-05-12"}
    ],
    "missing": [
      {"key": "teacher_name", "label": "教师姓名", "required": true}
    ]
  },
  "spec_reference": "《学生手册》请假管理规定：请假需经任课教师同意...",
  "hint": "回复"确认"生成文档，或回复补充信息（如："王老师"）"
}
```

### Return Format — Result Card

```json
{
  "type": "document_result",
  "doc_type": "leave",
  "display_name": "请假条",
  "file_name": "leave_a3f2b1c0.docx",
  "file_size": "2.4 KB",
  "download_url": "/api/documents/download/leave_a3f2b1c0",
  "spec_reference": "《学生手册》请假管理规定",
  "expires_in": "30 分钟"
}
```

---

## 5. API Layer

### New Endpoint

```
GET /api/documents/download/{file_id}
```

Generic download endpoint serving files from temp_dir. Reads file, streams response with appropriate Content-Disposition header.

### Migration

| Old | New |
|-----|-----|
| `POST /api/leave/generate` | Removed |
| `GET /api/leave/download/{file_id}` | → `GET /api/documents/download/{file_id}` (old path kept as redirect for 30 days) |
| `schemas/leave.py` | Removed |
| `services/leave_service.py` | Replaced by `DocumentGenerator` |
| `router/leave.py` | Replaced by `router/documents.py` |
| `agent_tools.py:generate_leave_request` | Replaced by `agent_tools.py:doc_preview` |

---

## 6. Frontend

### New result_card Types

**document_preview** — blue left border
- Auto-filled fields: green tag `auto`
- Extracted fields: blue tag `extracted`
- Missing fields: red tag `missing` with input prompt
- Spec reference snippet at bottom
- User can reply with corrections/additions inline

**document_result** — green left border
- File name + size
- Download button (primary action)
- Spec reference
- Expiry notice

### Deleted

- `LeaveRequest.vue` — standalone form page removed
- `/leave-request` route — removed from router
- Sidebar "文书辅助" entry — changed to open chat with context message

### Session Replay

Both new card types serialize into the stored assistant message JSON. Loading a historical session reconstructs the cards via `normalizeResultCard()`.

---

## 7. System Prompt Changes

Update `main_prompt.txt` to add:

```
## 文书生成工具

当用户提到以下关键词时，调用 doc_preview 工具：
- "写" + ("请假条"/"申请"/"证明"/"申报")
- "帮我生成" + 文书类型
- "需要" + 文书名称

工作流程：
1. 第一次调用 doc_preview(query=用户原文, confirmed=false)
2. 将返回的预览信息展示给用户
3. 用户确认后，第二次调用 doc_preview(query=用户原文, confirmed=true, params={所有字段})
4. 展示下载链接

你必须在第一次调用后等待用户确认，不要跳过确认步骤。
```

---

## 8. Files Changed

| File | Change | Description |
|------|--------|-------------|
| `backend/app/services/document_generator.py` | **New** | Generic template filling engine |
| `backend/app/router/documents.py` | **New** | Download endpoint + future upload |
| `backend/app/agent/agent_tools.py` | Modify | Replace `generate_leave_request` with `doc_preview` |
| `backend/app/prompt/main_prompt.txt` | Modify | Add document generation guidance |
| `documents/leave/template.docx` | **New** | Placeholder-based leave template |
| `documents/leave/spec.md` | **New** | Leave format spec for RAG |
| `documents/leave/fields.json` | **New** | Leave field definitions |
| `backend/app/services/leave_service.py` | Remove | Replaced by DocumentGenerator |
| `backend/app/router/leave.py` | Remove | Replaced by documents.py |
| `backend/app/schemas/leave.py` | Remove | Replaced by fields.json |
| `front/src/views/LeaveRequest.vue` | Remove | Replaced by Agent chat flow |
| `front/src/views/AIChat.vue` | Modify | Add `document_preview` / `document_result` card rendering |
| `front/src/router/index.js` | Modify | Remove `/leave-request` route |
| `front/src/App.vue` | Modify | Update sidebar "文书辅助" entry |
| `backend/main.py` | Modify | Register documents router, remove leave router |
| `docker-compose.yml` | Modify | Add `documents/` volume mount to backend container |

---

## 9. Non-Goals

- Multi-language template support (only Chinese for now)
- PDF output format (only .docx)
- Template editing UI (templates edited directly as .docx files)
- Supporting other document types beyond leave in this spec (framework supports it, but migration is follow-up)
