from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

import aiofiles
from langchain_core.documents import Document

from app.rag.vector_store import VectorStoreService
from app.utils.file_handler import markdown_loader, pdf_loader, txt_loader
from app.utils.path_tool import get_abstract_path, get_project_root


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
STATUS_FILE = get_abstract_path("data/training_program_import_status.json")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
ARTICLE_PATTERN = re.compile(r"(第[一二三四五六七八九十百千万\d]+条)")
SECTION_PATTERN = re.compile(r"(?=^[一二三四五六七八九十]+、|^第[一二三四五六七八九十百千万\d]+[章节条])", re.M)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _repo_root() -> Path:
    return Path(get_project_root()).resolve().parent


def get_training_program_root() -> Path:
    repo_root = _repo_root()
    for name in ("training program", "Training Program"):
        candidate = repo_root / name
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return (repo_root / "training program").resolve()


def _normalize_relative_path(relative_path: str) -> str:
    value = (relative_path or "").replace("\\", "/").strip().strip("/")
    if not value or value.startswith("/") or re.search(r"(^|/)\.\.(/|$)", value):
        raise ValueError("invalid relativePath")
    return value


def resolve_training_program_file(relative_path: str) -> Path:
    root = get_training_program_root()
    safe_relative = _normalize_relative_path(relative_path)
    target = (root / safe_relative).resolve()
    if root not in target.parents:
        raise ValueError("relativePath is outside training program directory")
    if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("unsupported file type")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("training program file not found")
    return target


def _file_id(relative_path: str) -> str:
    return hashlib.md5(relative_path.encode("utf-8")).hexdigest()


def _clean_major_name(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"^\d+", "", stem)
    stem = re.sub(r"^\d+级教学计划[_-]?\d*[^_]*_", "", stem)
    stem = re.sub(r".*本科人才培养方案[-_]", "", stem)
    stem = re.sub(r"(本科人才)?培养方案|培养计划|教学计划|专业|（\d{4}版）|\(\d{4}版\)", "", stem)
    return stem.strip(" _-—（）()") or Path(filename).stem


async def _load_status() -> dict:
    if not os.path.exists(STATUS_FILE):
        return {}
    try:
        async with aiofiles.open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.loads(await f.read() or "{}")
    except Exception:
        return {}


async def _save_status(status: dict) -> None:
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    async with aiofiles.open(STATUS_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps(status, ensure_ascii=False, indent=2))


async def update_import_status(relative_path: str, **values) -> dict:
    status = await _load_status()
    current = status.get(relative_path, {})
    current.update(values)
    status[relative_path] = current
    await _save_status(status)
    return current


async def scan_training_program_files() -> list[dict]:
    root = get_training_program_root()
    status = await _load_status()
    if not root.exists():
        return []

    files: list[dict] = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item)):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        relative_path = path.relative_to(root).as_posix()
        parts = relative_path.split("/")
        college = parts[0] if len(parts) > 1 else "未分类"
        file_status = status.get(relative_path, {})
        files.append({
            "id": _file_id(relative_path),
            "fileName": path.name,
            "fileType": path.suffix.lower().lstrip("."),
            "college": college,
            "major": _clean_major_name(path.name),
            "relativePath": relative_path,
            "status": file_status.get("status", "not_imported"),
            "chunkCount": int(file_status.get("chunkCount", 0) or 0),
            "importedAt": file_status.get("importedAt", ""),
            "error": file_status.get("error", ""),
            "fileSize": path.stat().st_size,
        })
    return files


def _extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        texts = [node.text for node in paragraph.iter(f"{namespace}t") if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


async def _load_documents(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return await pdf_loader(str(path))
    if suffix == ".txt":
        return await txt_loader(str(path))
    if suffix == ".md":
        return await markdown_loader(str(path))
    if suffix == ".docx":
        text = await asyncio.to_thread(_extract_docx_text, path)
        return [Document(page_content=text, metadata={"source": str(path)})] if text.strip() else []
    return []


def _enhance_structured_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text or "").strip()


async def delete_training_program_vectors(relative_path: str) -> dict:
    safe_relative = _normalize_relative_path(relative_path)
    store = VectorStoreService()
    await asyncio.to_thread(store.vectors_store.delete, where={"relativePath": safe_relative})
    await update_import_status(
        safe_relative,
        status="not_imported",
        chunkCount=0,
        importedAt="",
        error="",
        deletedAt=_now(),
    )
    return {"relativePath": safe_relative, "status": "not_imported"}


async def import_training_program_file(relative_path: str, force: bool = False) -> dict:
    safe_relative = _normalize_relative_path(relative_path)
    path = resolve_training_program_file(safe_relative)
    files = await scan_training_program_files()
    file_info = next((item for item in files if item["relativePath"] == safe_relative), None)
    if not file_info:
        raise FileNotFoundError("training program file not found")

    if file_info["status"] == "imported" and not force:
        return file_info

    await update_import_status(safe_relative, status="importing", error="")
    try:
        await asyncio.to_thread(VectorStoreService().vectors_store.delete, where={"relativePath": safe_relative})

        documents = await _load_documents(path)
        if not documents:
            raise ValueError("文件解析结果为空")

        base_metadata = {
            "source": "training_program",
            "doc_name": file_info["fileName"],
            "fileName": file_info["fileName"],
            "file_name": file_info["fileName"],
            "college": file_info["college"],
            "major": file_info["major"],
            "relativePath": safe_relative,
            "fileType": file_info["fileType"],
            "kb_type": "training_program",
            "category": file_info["college"],
            "createdAt": _now(),
        }

        for doc in documents:
            doc.page_content = _enhance_structured_text(doc.page_content)
            if "page" in doc.metadata and doc.metadata["page"] is not None:
                try:
                    doc.metadata["page"] = int(doc.metadata["page"]) + 1
                except (TypeError, ValueError):
                    pass
            doc.metadata.update(base_metadata)

        store = VectorStoreService()
        split_docs = await store.spliter.split_documents(documents)
        if not split_docs:
            raise ValueError("文本切片结果为空")

        ids = []
        for index, doc in enumerate(split_docs):
            doc.metadata.update(base_metadata)
            doc.metadata["chunkIndex"] = index
            doc.metadata["chunk_index"] = index
            article_match = ARTICLE_PATTERN.search(doc.page_content or "")
            if article_match:
                doc.metadata["article"] = article_match.group(1)
            ids.append(f"training_program:{_file_id(safe_relative)}:{index}")

        await asyncio.to_thread(store.vectors_store.add_documents, split_docs, ids=ids)

        imported = await update_import_status(
            safe_relative,
            status="imported",
            chunkCount=len(split_docs),
            importedAt=_now(),
            error="",
            fileHash=await _file_hash(path),
        )
        return {**file_info, **imported, "status": "imported", "chunkCount": len(split_docs)}
    except Exception as exc:
        await update_import_status(
            safe_relative,
            status="failed",
            chunkCount=0,
            importedAt="",
            error=str(exc),
        )
        raise


async def _file_hash(path: Path) -> str:
    digest = hashlib.md5()
    async with aiofiles.open(path, "rb") as f:
        while chunk := await f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


async def import_training_program_batch(relative_paths: list[str], force: bool = False) -> dict:
    results = []
    for relative_path in relative_paths:
        try:
            item = await import_training_program_file(relative_path, force=force)
            results.append({"relativePath": relative_path, "success": True, "file": item})
        except Exception as exc:
            results.append({"relativePath": relative_path, "success": False, "error": str(exc)})
    return {
        "total": len(relative_paths),
        "successCount": sum(1 for item in results if item["success"]),
        "failedCount": sum(1 for item in results if not item["success"]),
        "results": results,
    }


async def get_import_status() -> dict:
    files = await scan_training_program_files()
    return {"files": files}
