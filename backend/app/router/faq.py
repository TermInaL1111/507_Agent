"""FAQ management API — CRUD for /app/data/faq.json"""
import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

faq_router = APIRouter(prefix="/api/faq", tags=["faq"])

_FAQ_PATH = Path(os.getenv("FAQ_PATH", "/app/data/faq.json"))


def _load_faq() -> dict:
    if _FAQ_PATH.exists():
        return json.loads(_FAQ_PATH.read_text(encoding="utf-8"))
    return {"updated_at": "", "questions": []}


def _save_faq(data: dict):
    _FAQ_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FAQ_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@faq_router.get("")
async def get_faq():
    faq = _load_faq()
    questions = faq.get("questions", [])
    questions.sort(key=lambda q: (not q.get("pinned", False), q.get("sort", 99)))
    return {"updated_at": faq.get("updated_at"), "questions": questions}


@faq_router.post("/pin")
async def pin_faq(data: dict):
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
    from app.agent.agent_tools import _extract_faq_from_documents
    questions = await _extract_faq_from_documents()
    faq = {"updated_at": datetime.now().isoformat(), "questions": questions}
    _save_faq(faq)
    return {"ok": True, "count": len(questions)}
