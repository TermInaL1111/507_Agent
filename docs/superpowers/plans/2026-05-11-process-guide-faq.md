# Process Guide + FAQ Recommendations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add RAG-driven process guides (step-by-step campus affair procedures) and FAQ recommendations (high-frequency question chips on homepage and in conversations).

**Architecture:** Both features share the existing ChromaDB + RAG pipeline. Process guides use `rag_summary_tools` with enhanced system prompt to output structured `process_guide` cards. FAQ is stored as JSON in `backend_data` volume, extracted by LLM at document import time, and served via a new `faq_recommend` Agent tool.

**Tech Stack:** Python 3.12, FastAPI, LangChain, ChromaDB, Vue 3 + Element Plus

---

### Task 1: Create FAQ API router

**Files:**
- Create: `backend/app/router/faq.py`

- [ ] **Step 1: Write FAQ router**

Write `/root/zhsx/backend/app/router/faq.py`:

```python
"""FAQ management API — CRUD for /app/data/faq.json"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

faq_router = APIRouter(prefix="/api/faq", tags=["faq"])

_FAQ_PATH = Path(os.getenv("FAQ_PATH", "/app/data/faq.json"))
_FAQ_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_faq() -> dict:
    if _FAQ_PATH.exists():
        return json.loads(_FAQ_PATH.read_text(encoding="utf-8"))
    return {"updated_at": "", "questions": []}


def _save_faq(data: dict):
    _FAQ_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@faq_router.get("")
async def get_faq():
    """Return all FAQ questions. Pinned first, then sorted by sort field."""
    faq = _load_faq()
    questions = faq.get("questions", [])
    questions.sort(key=lambda q: (not q.get("pinned", False), q.get("sort", 99)))
    return {"updated_at": faq.get("updated_at"), "questions": questions}


@faq_router.post("/pin")
async def pin_faq(data: dict):
    """Update pin/sort for a FAQ question.
    Body: { question_id: str, pinned: bool, sort: int }"""
    faq = _load_faq()
    qid = data.get("question_id")
    for q in faq.get("questions", []):
        if q.get("id") == qid:
            if "pinned" in data:
                q["pinned"] = data["pinned"]
            if "sort" in data:
                q["sort"] = data["sort"]
            _save_faq(faq)
            return {"ok": True, "question_id": qid}
    raise HTTPException(status_code=404, detail="Question not found")


@faq_router.post("/regenerate")
async def regenerate_faq():
    """Re-extract FAQ questions from all documents in ChromaDB."""
    from app.agent.agent_tools import _extract_faq_from_documents
    questions = await _extract_faq_from_documents()
    faq = {"updated_at": datetime.now().isoformat(), "questions": questions}
    _save_faq(faq)
    return {"ok": True, "count": len(questions)}
```

- [ ] **Step 2: Verify import**

```bash
cd /root/zhsx/backend && python3 -c "from app.router.faq import faq_router; print('OK')"
```

Expected: OK

- [ ] **Step 3: Register router in main.py**

Read `/root/zhsx/backend/main.py`. Add after the other router imports:

```python
from app.router.faq import faq_router
```

Add after the other `app.include_router(...)` calls:

```python
app.include_router(faq_router)
```

- [ ] **Step 4: Commit**

```bash
cd /root/zhsx && git add backend/app/router/faq.py backend/main.py && git commit -m "feat: add FAQ CRUD API — get/pin/regenerate"
```

---

### Task 2: Add FAQ extraction logic to agent_tools.py

**Files:**
- Modify: `backend/app/agent/agent_tools.py`

- [ ] **Step 1: Add the FAQ extraction helper function**

In `/root/zhsx/backend/app/agent/agent_tools.py`, add before `_FIELD_LABELS`:

```python
async def _extract_faq_from_documents() -> list[dict]:
    """Extract FAQ questions from indexed documents using LLM."""
    try:
        # Get all indexed document chunks
        from app.rag.vector_store import document_spec_store
        results = document_spec_store.collection.get()
    except Exception:
        return []

    if not results or not results.get("documents"):
        return []

    # Build document summary (first 3000 chars combined)
    all_text = "\n\n".join(results["documents"][:10])
    summary = all_text[:3000]

    # Use ChatTongyi to extract questions
    try:
        from langchain_community.chat_models import ChatTongyi
        llm = ChatTongyi(model="qwen3-max")
        prompt = (
            "从以下校园办事指南内容中，提取 5-10 个学生最常问的高频问题。"
            "每个问题应该简洁明确（15字以内），覆盖文档中提到的不同事务。"
            "只返回问题列表，每行一个问题，不要加序号，不要加其他内容。\n\n"
            f"{summary}"
        )
        response = await llm.ainvoke(prompt)
        lines = [line.strip() for line in response.content.split("\n") if line.strip()]
        questions = []
        for i, line in enumerate(lines):
            line = line.lstrip("0123456789.、) ）")
            if len(line) > 5:
                questions.append({
                    "id": f"faq_{uuid.uuid4().hex[:8]}",
                    "question": line[:80],
                    "category": "",
                    "pinned": False,
                    "sort": (i + 1) * 10,
                })
        return questions
    except Exception as e:
        logger.warning(f"FAQ extraction failed: {e}")
        return []
```

Note: add `import uuid` near the top of the function since it's already imported in `doc_preview` but at function scope. Let's add `import uuid` at module level instead.

- [ ] **Step 2: Add top-level imports**

In the imports section of `agent_tools.py`, ensure `uuid` is imported at module level:

```python
import uuid
```

If not already at module level (only inside functions), add it after `import os`.

- [ ] **Step 3: Commit**

```bash
cd /root/zhsx && git add backend/app/agent/agent_tools.py && git commit -m "feat: add _extract_faq_from_documents helper"
```

---

### Task 3: Wire FAQ extraction into document import flow

**Files:**
- Modify: `backend/app/router/chat.py` (the `/training-program/import` endpoint)

- [ ] **Step 1: Add FAQ extraction call after ChromaDB indexing**

Read `/root/zhsx/backend/app/router/chat.py` to find the training program import endpoint. Add after the successful ChromaDB indexing step:

```python
    # Extract FAQ questions from indexed documents
    faq_added = 0
    try:
        from app.agent.agent_tools import _extract_faq_from_documents
        from app.router.faq import _load_faq, _save_faq
        new_questions = await _extract_faq_from_documents()
        if new_questions:
            faq = _load_faq()
            existing_ids = {q["id"] for q in faq.get("questions", [])}
            # Only add questions not already in FAQ
            added = [q for q in new_questions if q["id"] not in existing_ids]
            faq["questions"] = faq.get("questions", []) + added
            faq["updated_at"] = datetime.datetime.now().isoformat()
            _save_faq(faq)
            faq_added = len(added)
    except Exception as e:
        logger.warning(f"FAQ extraction during import failed: {e}")
```

Include `faq_added` in the response data.

- [ ] **Step 2: Commit**

```bash
cd /root/zhsx && git add backend/app/router/chat.py && git commit -m "feat: trigger FAQ extraction on document import"
```

---

### Task 4: Add `faq_recommend` Agent tool

**Files:**
- Modify: `backend/app/agent/agent_tools.py`

- [ ] **Step 1: Write the faq_recommend tool**

Add after `_extract_faq_from_documents` in `agent_tools.py`:

```python
@tool(description="""推荐高频相关问题。
- query 为空时返回全部 FAQ（置顶优先）
- query 非空时返回语义相似的高频问题列表
当用户提问模糊、对话刚开始、或 RAG 检索无结果时调用。""")
async def faq_recommend(query: str = "") -> str:
    try:
        from app.router.faq import _load_faq
        faq = _load_faq()
        all_questions = faq.get("questions", [])

        if not query or not query.strip():
            # Return all, pinned first
            all_questions.sort(key=lambda q: (not q.get("pinned", False), q.get("sort", 99)))
            items = all_questions[:8]
        else:
            # Simple keyword matching (fallback if ChromaDB embedding unavailable)
            matched = []
            for q in all_questions:
                score = len(set(query) & set(q.get("question", ""))) / max(len(query), 1)
                if score > 0.1:
                    matched.append((score, q))
            matched.sort(key=lambda x: (-x[1].get("pinned", False), -x[0], x[1].get("sort", 99)))
            items = [q for _, q in matched[:5]]
            if not items:
                # Fallback to pinned
                items = [q for q in all_questions if q.get("pinned")][:5]

        return json.dumps({
            "type": "faq_recommendations",
            "title": "你可能想问：" if query else "常见问题",
            "questions": items,
        }, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"faq_recommend failed: {e}")
        return "暂时无法加载常见问题。"
```

- [ ] **Step 2: Commit**

```bash
cd /root/zhsx && git add backend/app/agent/agent_tools.py && git commit -m "feat: add faq_recommend Agent tool"
```

---

### Task 5: Register faq_recommend in Agent + update system prompt

**Files:**
- Modify: `backend/app/agent/agent.py`
- Modify: `backend/app/prompt/main_prompt.txt`

- [ ] **Step 1: Add to tool list in agent.py**

In `/root/zhsx/backend/app/agent/agent.py`, in the import block (line 14-28), add:

```python
    faq_recommend,
```

In `_get_default_tools()`, add `faq_recommend,` to the tool list.

- [ ] **Step 2: Update system prompt**

In `/root/zhsx/backend/app/prompt/main_prompt.txt`, add after the existing sections:

```
### FAQ 推荐
- `faq_recommend` — 推荐高频问题。query为空返回全部置顶FAQ；query非空返回语义相似问题。
触发时机：
- 用户说"你好"/"在吗"/空消息 → faq_recommend(query="")
- 用户提问后检索无结果 → faq_recommend(query=用户原文)
- 用户说"还有什么"/"还有别的吗" → faq_recommend(query=用户原文)

### 办事流程指引
当用户询问校园办事流程（缓考、奖学金、请假等）时：
1. 调用 rag_summary_tools 检索相关办事指南
2. 将结果整理为 process_guide JSON 格式：{type:"process_guide", title, category, source, steps:[{number, title, materials[], contact, entry, notes}], disclaimer}
3. 每个步骤包含：📄所需材料、👤办理对象、🔗办理入口、⚠️注意事项
4. 如果文档无明确步骤划分，用自然语言段落说明
5. 不同学院流程不同时需注明
```

Add to "典型场景处理":

```
**办事流程**："缓考怎么申请" → rag_summary_tools → process_guide 结构化步骤
**FAQ 推荐**："你好" → faq_recommend(query="") → 展示推荐问题
```

- [ ] **Step 3: Commit**

```bash
cd /root/zhsx && git add backend/app/agent/agent.py backend/app/prompt/main_prompt.txt && git commit -m "feat: register faq_recommend + add process guide prompt guidance"
```

---

### Task 6: Frontend — Add process_guide and faq_recommendations card rendering

**Files:**
- Modify: `front/src/views/AIChat.vue`

- [ ] **Step 1: Add card type mappings**

In `normalizeCardType()`, add to the `mapping` object:

```js
    process_guide: 'process_guide',
    faq_recommendations: 'faq_recommendations',
```

In `getResultCardTypeLabel()`, add to `labelMap`:

```js
    process_guide: '办事流程指引',
    faq_recommendations: '相关问题推荐',
```

- [ ] **Step 2: Add normalization logic**

In `normalizeResultCard()`, before the final `return null`, add:

```js
  if (type === 'process_guide') {
    return {
      ...baseCard,
      category: rawCard.category || '',
      source: rawCard.source || '',
      steps: toArray(rawCard.steps || []).map((s, idx) => ({
        number: s?.number || idx + 1,
        title: s?.title || `步骤 ${idx + 1}`,
        materials: toArray(s?.materials || []),
        contact: s?.contact || '',
        entry: s?.entry || '',
        notes: s?.notes || '',
      })),
      disclaimer: rawCard.disclaimer || '',
    };
  }

  if (type === 'faq_recommendations') {
    return {
      ...baseCard,
      title: rawCard.title || '你可能想问：',
      questions: toArray(rawCard.questions || []).map(q => ({
        id: q?.id || '',
        question: q?.question || '',
        category: q?.category || '',
        pinned: q?.pinned || false,
      })),
    };
  }
```

- [ ] **Step 3: Add card templates**

Find the last result_card template in the HTML. Add after the `document_result` card block:

```html
                  <!-- 办事流程卡片 -->
                  <div v-else-if="message.resultCard.type === 'process_guide'" class="result-card result-card--process-guide">
                    <div class="result-card__header">
                      <span class="result-card__type-tag">📋 {{ message.resultCard.title }}</span>
                      <el-tag v-if="message.resultCard.category" size="small" type="info">{{ message.resultCard.category }}</el-tag>
                    </div>
                    <div v-if="message.resultCard.source" class="process-source">
                      来源：{{ message.resultCard.source }}
                    </div>
                    <div v-for="step in message.resultCard.steps" :key="step.number" class="process-step">
                      <div class="process-step__title">Step {{ step.number }} — {{ step.title }}</div>
                      <div class="process-step__detail" v-if="step.materials.length">
                        <span class="process-icon">📄</span> 材料：{{ step.materials.join('、') }}
                      </div>
                      <div class="process-step__detail" v-if="step.contact">
                        <span class="process-icon">👤</span> 办理对象：{{ step.contact }}
                      </div>
                      <div class="process-step__detail" v-if="step.entry">
                        <span class="process-icon">🔗</span> 入口：{{ step.entry }}
                      </div>
                      <div class="process-step__detail" v-if="step.notes">
                        <span class="process-icon">⚠️</span> {{ step.notes }}
                      </div>
                    </div>
                    <div v-if="message.resultCard.disclaimer" class="process-disclaimer">
                      ⚠️ {{ message.resultCard.disclaimer }}
                    </div>
                  </div>

                  <!-- FAQ 推荐卡片 -->
                  <div v-else-if="message.resultCard.type === 'faq_recommendations'" class="result-card result-card--faq">
                    <div class="faq-title">{{ message.resultCard.title }}</div>
                    <div class="faq-chips">
                      <span
                        v-for="q in message.resultCard.questions"
                        :key="q.id"
                        class="faq-chip"
                        :class="{ 'faq-chip--pinned': q.pinned }"
                        @click="sendFaqQuestion(q.question)"
                      >
                        <span v-if="q.pinned" class="faq-pin">📌 </span>{{ q.question }}
                      </span>
                    </div>
                  </div>
```

- [ ] **Step 4: Add sendFaqQuestion function**

In `<script setup>`, add:

```js
const sendFaqQuestion = (question) => {
  userInput.value = question;
  sendMessage();
};
```

- [ ] **Step 5: Add CSS**

In `<style scoped>`, add:

```css
.result-card--process-guide { border-left-color: #409eff; }
.process-source { font-size: 12px; color: #909399; margin-bottom: 12px; }
.process-step { margin: 12px 0; padding: 10px; background: #f5f7fa; border-radius: 6px; }
.process-step__title { font-weight: 600; font-size: 14px; margin-bottom: 6px; color: #303133; }
.process-step__detail { font-size: 13px; color: #606266; margin: 3px 0; padding-left: 4px; }
.process-icon { margin-right: 4px; }
.process-disclaimer { font-size: 12px; color: #e6a23c; margin-top: 12px; padding-top: 8px; border-top: 1px dashed #e4e7ed; }
.result-card--faq { border-left-color: #67c23a; }
.faq-title { font-size: 13px; color: #606266; margin-bottom: 10px; }
.faq-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.faq-chip { display: inline-block; padding: 6px 14px; background: #ecf5ff; color: #409eff; border-radius: 20px; font-size: 13px; cursor: pointer; transition: background 0.2s; }
.faq-chip:hover { background: #d9ecff; }
.faq-chip--pinned { background: #fef0f0; color: #e6a23c; }
.faq-pin { font-size: 12px; }
```

- [ ] **Step 6: Commit**

```bash
cd /root/zhsx && git add front/src/views/AIChat.vue && git commit -m "feat: add process_guide and faq_recommendations card rendering"
```

---

### Task 7: Frontend — Add FAQ chips above input area

**Files:**
- Modify: `front/src/views/AIChat.vue`

- [ ] **Step 1: Add FAQ data fetch**

In `<script setup>`, add:

```js
const faqQuestions = ref([]);

const loadFaqQuestions = async () => {
  try {
    const token = userStore.getToken;
    const resp = await fetch(`${window.location.origin}/api/faq`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      const data = await resp.json();
      faqQuestions.value = (data.questions || []).slice(0, 6);
    }
  } catch {}
};

// Call on mount
onMounted(() => {
  loadFaqQuestions();
  // ... existing onMounted logic
});
```

- [ ] **Step 2: Add FAQ chips HTML above input area**

Find the `.input-area` div. Add ABOVE the `.input-container`:

```html
        <div v-if="faqQuestions.length" class="faq-bar">
          <span class="faq-bar__label">💬</span>
          <span
            v-for="q in faqQuestions"
            :key="q.id"
            class="faq-bar__chip"
            :class="{ 'faq-bar__chip--pinned': q.pinned }"
            @click="sendFaqQuestion(q.question)"
          >
            {{ q.pinned ? '📌 ' : '' }}{{ q.question }}
          </span>
        </div>
```

- [ ] **Step 3: Add CSS for FAQ bar**

```css
.faq-bar { display: flex; align-items: center; gap: 8px; padding: 8px 0; flex-wrap: wrap; }
.faq-bar__label { font-size: 13px; color: #909399; }
.faq-bar__chip { padding: 4px 12px; background: #f0f2f5; border-radius: 16px; font-size: 12px; color: #606266; cursor: pointer; white-space: nowrap; }
.faq-bar__chip:hover { background: #ecf5ff; color: #409eff; }
.faq-bar__chip--pinned { background: #fef0f0; color: #e6a23c; }
```

- [ ] **Step 4: Commit**

```bash
cd /root/zhsx && git add front/src/views/AIChat.vue && git commit -m "feat: add FAQ chips above chat input area"
```

---

### Task 8: Rebuild, deploy, and verify

- [ ] **Step 1: Rebuild Docker images**

```bash
cd /root/zhsx && docker-compose build backend frontend 2>&1 | tail -5
```

Expected: both succeed.

- [ ] **Step 2: Redeploy**

```bash
docker rm -f 507-agent-backend 507-agent-frontend 2>/dev/null
cd /root/zhsx && docker-compose up -d backend frontend 2>&1
```

Expected: containers running.

- [ ] **Step 3: Verify FAQ endpoint**

```bash
curl -s http://localhost/api/faq | python3 -m json.tool | head -10
```

Expected: JSON response with questions array.

- [ ] **Step 4: Verify Agent tools registered**

```bash
docker logs 507-agent-backend 2>&1 | grep -i "faq\|Application startup complete" | tail -3
```

Expected: startup complete.

- [ ] **Step 5: Push**

```bash
cd /root/zhsx && git push origin agent-centric
```
