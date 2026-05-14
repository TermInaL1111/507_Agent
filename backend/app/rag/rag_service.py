import asyncio
import hashlib
import os
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langsmith import traceable

from app.core.logger_handler import logger
from app.rag.reorder_service import reorder_service
from app.rag.vector_store import VectorStoreService
from app.services.source_file_service import find_source_file_by_name, get_source_file
from app.utils.config import chroma_config
from app.utils.factory import chat_model
from app.utils.prompt_loader import load_prompt


class RagService:
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = None
        self.prompt_text = load_prompt(prompt_type="rag_summary_prompt")
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.chat_model = chat_model
        self.chain = self._init_chain()
        self.hyde_prompt_template = PromptTemplate.from_template(
            "Based on the question below, write a detailed hypothetical answer for retrieval.\n\n"
            "Question: {query}\n\nHypothetical answer:"
        )

    async def initialize_retriever(self, query: str = None):
        if self.retriever is None:
            self.retriever = await self.vector_store.get_retriever(query)

    def _init_chain(self):
        return self.prompt_template | self.chat_model | StrOutputParser()

    @traceable
    async def generate_hypothetical_document(self, query: str) -> str:
        try:
            hyde_chain = self.hyde_prompt_template | self.chat_model | StrOutputParser()
            return await hyde_chain.ainvoke({"query": query})
        except Exception as e:
            logger.error(f"[HyDE] failed: {e}")
            return query

    @traceable
    async def retrieve_document(self, query: str) -> list:
        try:
            documents = await self.vector_store.hybrid_search(query)
            logger.info(f"[RAG] retrieved {len(documents)} documents")
            return documents
        except Exception as e:
            logger.error(f"[RAG] retrieve failed: {e}", exc_info=True)
            return []

    @traceable
    async def reorder_documents(self, query: str, documents: list) -> list:
        if not chroma_config.get("reranker", {}).get("enabled", True):
            return documents

        result = await reorder_service.reorder_documents(query, documents)
        if result["success"]:
            return [doc.get("document", "") for doc in result["documents"]]
        logger.warning(f"[RAG] reorder failed: {result['error']}")
        return documents

    @staticmethod
    def _source_filename_score(filename: str) -> int:
        name = filename or ""
        score = 0
        if re.search(r"[\u4e00-\u9fff]", name):
            score += 12
        if name.lower().endswith(".pdf"):
            score += 6
        if name.lower().endswith(".pd_"):
            score -= 12
        if name.count("_") >= 5:
            score -= 10
        if re.fullmatch(r"[A-Fa-f0-9_]{16,}\.pdf", name):
            score -= 8
        if name in {"source-file", ""}:
            score -= 20
        return score

    @staticmethod
    def _source_content_key(content: str) -> str:
        normalized = re.sub(r"\s+", "", content or "")[:360]
        return hashlib.md5(normalized.encode("utf-8")).hexdigest() if normalized else ""

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        raw_terms = re.split(r"[\s，。；：、,.!?！？（）()《》【】]+", query or "")
        return [term for term in raw_terms if len(term) >= 4]

    @staticmethod
    def _detect_article(query: str) -> str:
        match = re.search(r"第[一二三四五六七八九十百千万\d]+条", query or "")
        return match.group(0) if match else ""

    @staticmethod
    def _best_snippet(content: str, query: str, max_length: int = 260) -> str:
        text = (content or "").strip()
        if not text:
            return ""

        article = RagService._detect_article(query)
        anchors = [article] if article else []
        anchors.extend(RagService._query_terms(query))

        anchor_index = -1
        for anchor in anchors:
            if not anchor:
                continue
            anchor_index = text.find(anchor)
            if anchor_index >= 0:
                break

        if anchor_index < 0:
            return text[:max_length]

        start = max(anchor_index - 80, 0)
        end = min(start + max_length, len(text))
        return text[start:end].strip()

    async def build_sources(self, documents: list, limit: int = 1, query: str = "") -> list[dict]:
        candidates = {}
        query_terms = self._query_terms(query)
        article = self._detect_article(query)

        for index, doc in enumerate(documents):
            metadata = dict(getattr(doc, "metadata", {}) or {})
            content = (getattr(doc, "page_content", "") or "").strip()
            doc_name = metadata.get("doc_name") or metadata.get("file_name")
            if not doc_name:
                source_path = metadata.get("source")
                doc_name = os.path.basename(source_path) if source_path else "source-file"

            kb_type = metadata.get("kb_type") or "personal"
            file_id = metadata.get("file_id")
            source_file = await get_source_file(file_id) if file_id else None
            if source_file:
                doc_name = source_file.original_filename or doc_name
                kb_type = source_file.kb_type or kb_type
                metadata["category"] = metadata.get("category") or source_file.category
            else:
                source_file = await find_source_file_by_name(doc_name, kb_type)
                if source_file:
                    file_id = source_file.file_id
                    doc_name = source_file.original_filename or doc_name
                    kb_type = source_file.kb_type
                    metadata["category"] = metadata.get("category") or source_file.category

            page = metadata.get("page")
            try:
                page = int(page) if page is not None else None
            except (TypeError, ValueError):
                page = None

            content_key = self._source_content_key(content)
            if not content_key:
                continue

            source_key = file_id or f"{doc_name}:{page}:{metadata.get('chunk_index', '')}"
            source_id_seed = f"{source_key}:{metadata.get('chunk_index', '')}:{content[:80]}"
            source_id = metadata.get("source_id") or f"chunk_{hashlib.md5(source_id_seed.encode('utf-8')).hexdigest()[:12]}"

            score = 100 - index
            score += self._source_filename_score(doc_name)
            score += 12 if article and metadata.get("article") == article else 0
            score += 5 if article and article in content else 0
            score += sum(3 for term in query_terms if term in content or term in doc_name)
            if metadata.get("source") == "training_program":
                score += 10
                score += sum(4 for term in query_terms if term in str(metadata.get("major", "")) or term in str(metadata.get("college", "")))

            if metadata.get("source_type") == "campus_channel":
                doc_name = metadata.get("doc_name") or f"校园频道 / {metadata.get('section_name', '')}"
                kb_type = "shared"

            source = {
                "source_id": source_id,
                "file_id": file_id,
                "doc_name": doc_name,
                "source": metadata.get("source") or "",
                "kb_type": kb_type,
                "category": metadata.get("category") or "",
                "page": page,
                "snippet": self._best_snippet(content, query),
                "downloadable": bool(file_id),
                "college": metadata.get("college") or "",
                "major": metadata.get("major") or "",
                "relativePath": metadata.get("relativePath") or "",
                "chunkIndex": metadata.get("chunkIndex", metadata.get("chunk_index", "")),
                "fileType": metadata.get("fileType") or "",
                "source_type": metadata.get("source_type") or "",
                "section_name": metadata.get("section_name") or "",
                "post_url": metadata.get("post_url") or "",
                "publish_time": metadata.get("publish_time") or "",
                "publish_time_text": metadata.get("publish_time_text") or "",
                "channel_name": metadata.get("channel_name") or "",
            }

            current = candidates.get(content_key)
            if not current or score > current[0]:
                candidates[content_key] = (score, source)

        sources = [item[1] for item in sorted(candidates.values(), key=lambda item: item[0], reverse=True)]
        return sources[:limit]

    @traceable
    async def get_documents_and_summary(self, query: str) -> dict:
        try:
            documents = await self.retrieve_document(query)
            sources = await self.build_sources(documents, query=query)
            document_contents = [doc.page_content for doc in documents]
            reordered_documents = await self.reorder_documents(query, document_contents)

            if not reordered_documents:
                return {"documents": [], "summary": "未找到相关信息。", "sources": []}

            max_documents = 3

            async def summarize_document(i, doc):
                single_context = f"[Reference {i}] {doc}\n"
                return await asyncio.wait_for(
                    self.chain.ainvoke({"input": query, "context": single_context}),
                    timeout=30.0,
                )

            try:
                tasks = [summarize_document(i, doc) for i, doc in enumerate(reordered_documents[:max_documents], 1)]
                individual_summaries = await asyncio.gather(*tasks)

                if len(individual_summaries) == 1:
                    return {"documents": reordered_documents, "summary": individual_summaries[0], "sources": sources}

                combined_context = "Combine these document summaries into one final answer:\n\n"
                for i, summary in enumerate(individual_summaries, 1):
                    combined_context += f"[Summary {i}] {summary}\n\n"

                final_summary = await asyncio.wait_for(
                    self.chain.ainvoke({"input": query, "context": combined_context}),
                    timeout=30.0,
                )
                return {"documents": reordered_documents, "summary": final_summary, "sources": sources}
            except asyncio.TimeoutError:
                return {"documents": reordered_documents, "summary": "生成摘要超时，请稍后再试。", "sources": sources}
        except Exception as e:
            logger.error(f"[RAG] summary failed: {e}", exc_info=True)
            return {"documents": [], "summary": "处理请求时出现错误。", "sources": []}

    @traceable
    async def rag_summary(self, query: str) -> str:
        result = await self.get_documents_and_summary(query)
        return result.get("summary", "处理请求时出现错误。")

    async def rag_summary_with_sources(self, query: str) -> dict:
        result = await self.get_documents_and_summary(query)
        answer = result.get("summary", "处理请求时出现错误。")
        return {
            "answer": answer,
            "response": answer,
            "sources": result.get("sources", []),
        }
