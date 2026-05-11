# Process Guide + FAQ Recommendations — Design Spec

## Overview

Add two RAG-driven features sharing the same data source (official 办事指南 documents):

1. **Process Guide** — step-by-step procedure guidance for campus affairs, rendered as structured `process_guide` cards
2. **FAQ Recommendations** — high-frequency questions shown on homepage and in conversations, configurable via JSON

Both reuse the existing ChromaDB + RAG pipeline. No new Agent tool for process guide (uses `rag_summary_tools` with improved prompt); one new `faq_recommend` tool for FAQ.

## Scope

- Import official campus affair documents (PDF/Word) → ChromaDB index + LLM FAQ extraction
- Dialogue: Agent retrieves procedures → outputs `process_guide` card or plain text
- Homepage: FAQ chips above chat input area
- Dialogue: `faq_recommend` tool for vague queries or empty results
- FAQ management: pin/sort via API, regenerate from documents
- Only one doc type (办事指南) added initially — designed for extension

---

## 1. Data Model

### FAQ Storage — `backend_data/faq.json`

```json
{
  "updated_at": "2026-05-11T12:00:00",
  "questions": [
    {
      "id": "faq_001",
      "question": "如何申请缓考？",
      "category": "考试管理",
      "pinned": true,
      "sort": 1
    }
  ]
}
```

- `pinned`: true = always shown first with 📌 marker
- `sort`: lower number = higher priority
- Answers NOT stored — clicked FAQ sends query to Agent for live RAG retrieval
- Stored at `/app/data/faq.json` inside backend container (`backend_data` volume, writable)
- `documents/` volume stays read-only for PDFs and templates

---

## 2. Document Import Flow

```
POST /api/training-program/import (existing, extended)
    │
    ├── PDF parse → ChromaDB index (existing)
    │
    └── NEW: LLM FAQ extraction
          ├── Take document summary (first 2000 chars)
          ├── Call ChatTongyi with prompt: "从以下办事指南中提取 3-5 个学生最常问的问题，仅返回问题列表"
          ├── Deduplicate against existing faq.json
          ├── Merge into faq.json
          └── Return: { ..., faq_added: 3 }
```

---

## 3. API Layer

### New Endpoints

```
GET  /api/faq
  → returns faq.json content (homepage display)

POST /api/faq/pin
  body: { question_id, pinned: bool, sort: int }
  → updates faq.json

POST /api/faq/regenerate
  → re-extracts all FAQs from ChromaDB documents, rewrites faq.json
```

All endpoints read/write `/app/data/faq.json` (writable `backend_data` volume). No database table needed.

---

## 4. Process Guide — `process_guide` Result Card

### Card Structure

```json
{
  "type": "process_guide",
  "title": "缓考申请流程",
  "category": "考试管理",
  "source": "《学生手册》考试管理规定",
  "steps": [
    {
      "number": 1,
      "title": "申请缓考资格",
      "materials": ["缓考申请表", "医院证明"],
      "contact": "所在学院教务办",
      "entry": "教务系统 → 缓考申请",
      "notes": "需考前 3 天内提交"
    }
  ],
  "disclaimer": "不同学院可能有不同要求，请以所在学院通知为准。"
}
```

### Card Rendering

- Blue left border, ordered steps
- Each step shows: 📄 Materials, 👤 Contact, 🔗 Entry, ⚠️ Notes
- Source citation at top
- Disclaimer at bottom

### System Prompt Guidance

```
当用户询问办事流程时：
1. 调用 rag_summary_tools 检索相关文档
2. 将结果整理为结构化步骤，尽量包含：所需材料、办理对象、办理入口、注意事项
3. 如果文档中有明确的步骤划分，用 process_guide 格式返回 JSON
4. 如果文档是叙述性文本无明确步骤，用自然语言分段说明（但尽量提供入口信息）
5. 如果不同学院流程不同，注明差异
```

### Degradation Strategy

When RAG document lacks structured steps → Agent responds in natural language paragraphs. Frontend renders as normal markdown text, NOT a process_guide card.

---

## 5. FAQ Recommendations — `faq_recommendations` Result Card

### Tool Definition

```python
@tool(description="""推荐高频相关问题。
- query 为空: 返回全部 FAQ（置顶优先）
- query 非空: 返回语义相似的高频问题列表
当用户提问模糊、对话刚开始、或 RAG 检索无结果时调用。""")
async def faq_recommend(query: str = "") -> str:
```

### Internal Logic

```
faq_recommend(query)
    │
    ├── query == "" → read faq.json, return all (pinned first)
    │
    └── query != ""
         ├── Vectorize query using ChromaDB embedding
         ├── Match against faq.json questions
         ├── Return top-5 matches if similarity > threshold
         └── Fallback: return pinned questions
```

### Card Structure

```json
{
  "type": "faq_recommendations",
  "title": "你可能想问：",
  "questions": [
    {"id": "faq_001", "question": "缓考申请流程是什么？", "category": "考试管理", "pinned": true}
  ]
}
```

### Agent Trigger Timing (System Prompt)

- User says "你好" / empty message → `faq_recommend(query="")`
- RAG returns no results → `faq_recommend(query=用户原文)`
- User says "还有什么" / "还有别的吗" → `faq_recommend(query=用户原文)`

### Card Rendering

- Clickable question chips
- Click sends the question as a new chat message
- Pinned questions get 📌 marker

---

## 6. Frontend

### Chat Input Area (AIChat.vue)

```
┌──────────────────────────────────┐
│  💬 常见问题                      │
│  [📌 如何缓考] [奖学金材料]        │
│  [选课流程] [宿舍规定]             │
├──────────────────────────────────┤
│  [输入框__________________] [发送] │
└──────────────────────────────────┘
```

- FAQ area loaded from `GET /api/faq` on mount
- Click chip → set input value + auto-send
- Collapsible: user can hide FAQ area
- Always visible above input (not just on first load)

### process_guide Card Template

Added to AIChat.vue result_card rendering, alongside existing card types.

### faq_recommendations Card Template

Added to AIChat.vue result_card rendering.

### normalizeResultCard

Add `process_guide` and `faq_recommendations` to `normalizeCardType()` mapping.

---

## 7. Files Changed

| File | Change | Description |
|------|--------|-------------|
| `documents/faq.json` | **New** | FAQ configuration file |
| `backend/app/router/faq.py` | **New** | FAQ CRUD API |
| `backend/app/agent/agent_tools.py` | Modify | Add `faq_recommend` tool |
| `backend/app/agent/agent.py` | Modify | Register `faq_recommend` in tool list |
| `backend/app/router/chat.py` | Modify | FAQ extraction on document import |
| `backend/app/prompt/main_prompt.txt` | Modify | Process guide format guidance + faq_recommend triggers |
| `front/src/views/AIChat.vue` | Modify | FAQ area above input + 2 new card types |
| `front/src/views/Home.vue` | Modify | FAQ display (if separate homepage) |
| `backend/main.py` | Modify | Register faq router |

---

## 8. Non-Goals

- Full CMS for FAQ management (only JSON + API)
- FAQ analytics (click tracking, popularity)
- Multi-language FAQ
- FAQ per user personalization
