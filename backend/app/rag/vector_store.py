import asyncio
import sys
import os
import re
import tempfile

from langchain_classic.retrievers import EnsembleRetriever

# 将根目录添加到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import aiofiles
from aiofiles import os as aio_os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.rag.text_spliter import AsyncTextSplitter
from langchain_community.retrievers import BM25Retriever

from app.utils.config import chroma_config
from app.utils.factory import embed_model
from app.utils.file_handler import pdf_loader, txt_loader, listdir_allowed_type, get_file_md5_hex, markdown_loader, \
    ppt_loader, word_loader
from app.core.logger_handler import logger
from app.utils.path_tool import get_abstract_path

ARTICLE_PATTERN = re.compile(r"第[一二三四五六七八九十百千万\d]+条")
TRAINING_PROGRAM_KEYWORDS = (
    "培养方案", "培养计划", "专业", "学分", "毕业要求", "核心课程", "课程体系",
    "第几条", "第几章", "中国地质大学", "地大", "CUG"
)


def detect_article_query(query: str) -> str | None:
    match = ARTICLE_PATTERN.search(query or "")
    return match.group(0) if match else None


def is_training_program_query(query: str) -> bool:
    return any(keyword.lower() in (query or "").lower() for keyword in TRAINING_PROGRAM_KEYWORDS)


class VectorStoreService:
    """向量数据库服务"""
    def __init__(self):
        persist_dir = get_abstract_path(chroma_config['persist_directory'])
        # 使用同步 Chroma, 在调用时用 to_thread 包裹
        self.vectors_store = Chroma(
            collection_name=chroma_config['collection_name'],
            embedding_function=embed_model,
            persist_directory=persist_dir,
        )
        self.spliter = AsyncTextSplitter(
            chunk_size=chroma_config['chunk_size'],
            chunk_overlap=chroma_config['chunk_overlap'],
            separators=chroma_config['separators'],
            embedding_model=embed_model
        )

    async def hybrid_search(self, query: str) -> list[Document]:
        article = detect_article_query(query)
        prefer_training_program = is_training_program_query(query)
        fetch_k = int(chroma_config.get("fetch_k", chroma_config.get("k", 5)))
        final_k = int(chroma_config.get("k", 5))
        keyword_top_k = int(chroma_config.get("keyword_top_k", 10))

        vector_results = await asyncio.to_thread(
            self.vectors_store.similarity_search_with_score,
            query,
            fetch_k,
        )
        if prefer_training_program:
            training_vector_results = await asyncio.to_thread(
                self.vectors_store.similarity_search_with_score,
                query,
                max(fetch_k, 50),
                filter={"source": "training_program"},
            )
            vector_results = list(vector_results) + list(training_vector_results)

        scored_docs: dict[str, tuple[Document, float]] = {}
        major_candidates = await self._detect_training_program_majors(query) if prefer_training_program else []

        def doc_key(doc: Document) -> str:
            metadata = doc.metadata or {}
            return "|".join([
                str(metadata.get("file_id") or metadata.get("source") or ""),
                str(metadata.get("page") or ""),
                str(metadata.get("chunk_index") or metadata.get("article") or ""),
                doc.page_content[:120],
            ])

        for doc, distance in vector_results:
            metadata = doc.metadata or {}
            score = -float(distance or 0)
            if prefer_training_program and metadata.get("source") == "training_program":
                score += 8.0
            if metadata.get("major") and metadata.get("major") in major_candidates:
                score += 5.0
            if article and article in (doc.page_content or ""):
                score += 2.0
            key = doc_key(doc)
            if key not in scored_docs or score > scored_docs[key][1]:
                scored_docs[key] = (doc, score)

        if article or prefer_training_program:
            all_docs = await self._get_all_documents()
            query_for_terms = (query or "").replace(article, "") if article else (query or "")
            query_terms = [
                term for term in re.split(r"[\s，。；：、,.!?！？（）()《》【】]+", query_for_terms)
                if len(term) >= 2 and term not in {"是什么", "什么", "第几条", "内容"}
            ]
            keyword_candidates = []
            for doc in all_docs:
                metadata = doc.metadata or {}
                text = doc.page_content or ""
                if prefer_training_program and metadata.get("source") != "training_program":
                    continue
                if article and article not in text:
                    continue
                keyword_score = 2.0 if article else 1.0
                if prefer_training_program:
                    keyword_score += 8.0
                if metadata.get("major") and metadata.get("major") in major_candidates:
                    keyword_score += 5.0
                for term in query_terms:
                    if term in text or term in str(metadata.get("major", "")) or term in str(metadata.get("college", "")):
                        keyword_score += min(len(term) / 10, 1.5)
                keyword_candidates.append((doc, keyword_score))

            keyword_candidates.sort(key=lambda item: item[1], reverse=True)
            keyword_hits = keyword_candidates[:keyword_top_k]

            for rank, (doc, keyword_score) in enumerate(keyword_hits):
                score = keyword_score - rank * 0.01
                key = doc_key(doc)
                if key not in scored_docs or score > scored_docs[key][1]:
                    scored_docs[key] = (doc, score)

        sorted_docs = sorted(scored_docs.values(), key=lambda item: item[1], reverse=True)
        return [doc for doc, _ in sorted_docs[:final_k]]

    async def _detect_training_program_majors(self, query: str) -> list[str]:
        all_docs = await self._get_all_documents()
        majors = sorted({
            str((doc.metadata or {}).get("major") or "")
            for doc in all_docs
            if (doc.metadata or {}).get("source") == "training_program" and (doc.metadata or {}).get("major")
        }, key=len, reverse=True)
        return [major for major in majors if major and major in (query or "")]

    async def get_bm25_retriever(self):
        """
        获取BM25检索器
        :return: BM25Retriever实例
        """
        # 从文件直接加载文档，不依赖向量数据库
        allowed_file_path: tuple[str] = await listdir_allowed_type(
            chroma_config['data_path'],
            tuple(chroma_config['allow_knowledge_file_types'])
        )
        file_paths = list(allowed_file_path)
        
        all_docs = []
        for file_path in file_paths:
            documents = await self.get_file_document(file_path)
            if documents:
                split_docs = await self.spliter.split_documents(documents)
                all_docs.extend(split_docs)
        
        # 创建BM25检索器
        if all_docs:
            bm25_retriever = BM25Retriever.from_documents(
                documents=all_docs,
                k=chroma_config['k']
            )
            return bm25_retriever
        else:
            return None

    async def _get_all_documents(self) -> list[Document]:
        """
        获取向量库中的所有文档
        :return: 文档列表
        """
        # 使用同步操作获取所有文档
        all_docs = await asyncio.to_thread(
            self.vectors_store.get,
            include=['documents', 'metadatas']
        )
        # 构建Document对象列表
        documents = []
        for i, doc in enumerate(all_docs['documents']):
            metadata = all_docs['metadatas'][i] if i < len(all_docs['metadatas']) else {}
            documents.append(Document(page_content=doc, metadata=metadata))
        return documents

    async def get_retriever(self, query: str = None):
        """
        获取混合检索器（BM25 + 向量检索）
        :param query: 查询语句，用于动态调整权重
        :return: EnsembleRetriever实例或单独的向量检索器
        """
        # 创建向量检索器
        vector_retriever = self.vectors_store.as_retriever(
            search_type='similarity',
            search_kwargs={'k': chroma_config['k'], 'fetch_k': chroma_config.get('fetch_k', chroma_config['k'])},
        )
        # 创建BM25检索器
        bm25_retriever = await self.get_bm25_retriever()
        
        # 根据是否有BM25检索器决定返回哪种检索器
        if bm25_retriever:
            # 获取动态权重
            weights = await self.get_dynamic_weights(query)
            # 创建混合检索器
            ensemble_retriever = EnsembleRetriever(
                retrievers=[vector_retriever, bm25_retriever],
                weights=weights
            )
            return ensemble_retriever
        else:
            # 如果没有BM25检索器，只返回向量检索器
            return vector_retriever

    @staticmethod
    async def get_dynamic_weights(query: str = None):
        """
        根据查询动态调整权重
        :param query: 查询语句
        :return: 权重列表 [向量检索权重, BM25检索权重]
        """
        # 默认权重
        default_vector_weight = 0.5
        default_bm25_weight = 0.5
        
        if not query:
            return [default_vector_weight, default_bm25_weight]
        
        # 根据查询特征调整权重
        query_length = len(query)
        query_words = len(query.split())
        
        # 长查询（>50字符）更适合向量检索
        if query_length > 50:
            vector_weight = 0.7
            bm25_weight = 0.3
        # 短查询（<20字符）更适合BM25检索
        elif query_length < 20:
            vector_weight = 0.3
            bm25_weight = 0.7
        # 中等长度查询使用默认权重
        else:
            vector_weight = default_vector_weight
            bm25_weight = default_bm25_weight
        
        # 关键词密集的查询（词数/长度比例高）更适合BM25
        if query_words > 0:
            word_density = query_words / query_length
            if word_density > 0.1:
                bm25_weight = min(bm25_weight + 0.1, 0.7)
                vector_weight = max(vector_weight - 0.1, 0.3)
        
        return [vector_weight, bm25_weight]

    async def check_md5_hex(self, md5_for_check: str) -> bool:
        """异步检查md5"""
        md5_path = get_abstract_path(chroma_config['md5_hex_store'])
        # 确保目录存在
        md5_dir = os.path.dirname(md5_path)
        if not await aio_os.path.exists(md5_dir):
            await aio_os.makedirs(md5_dir, exist_ok=True)
        if not await aio_os.path.exists(md5_path):
            async with aiofiles.open(md5_path, 'w', encoding="utf-8"):
                pass
            return False

        async with aiofiles.open(md5_path, 'r', encoding="utf-8") as f:
            async for line in f:
                if line.strip() == md5_for_check:
                    return True
            return False

    async def save_md5_hex(self, md5_hex: str):
        """异步保存md5"""
        async with aiofiles.open(get_abstract_path(chroma_config['md5_hex_store']), 'a', encoding="utf-8") as f:
            await f.write(md5_hex + '\n')

    async def delete_user_documents(self, user_id: str):
        """
        删除指定用户的所有文档
        :param user_id: 用户ID
        """
        try:
            # 使用同步操作删除文档
            await asyncio.to_thread(
                self.vectors_store.delete, 
                where={"user_id": user_id}
            )
            logger.info(f"【向量数据库】已删除用户 {user_id} 的所有文档")
        except Exception as e:
            logger.error(f"【向量数据库】删除用户 {user_id} 的文档时出错: {e}")
            raise

    async def get_file_document(self, read_path: str) -> list[Document]:
        """异步加载文件"""
        if read_path.endswith('.txt'):
            return await txt_loader(read_path)
        elif read_path.lower().endswith(('.pdf', '.pd_')):
            return await pdf_loader(read_path)
        elif read_path.endswith('.md'):
            return await markdown_loader(read_path)
        elif read_path.endswith('.pptx'):
            return await ppt_loader(read_path)
        elif read_path.endswith('.docx'):
            return await word_loader(read_path)
        else:
            return []

    async def get_document(self, files: list = None, user_id: str = None, file_records: list[dict] = None):
        """
        处理文档并将其转为向量存入向量数据库
        :param files: 上传的文件列表，如果为None则从数据文件夹读取
        :param user_id: 用户ID，用于标记文档的所有者
        """
        # 确定要处理的文件列表
        file_items = []
        if files:
            # 处理上传的文件
            for file in files:
                # 创建临时文件，使用asyncio.to_thread 包裹
                temp_file_path = await asyncio.to_thread(
                    tempfile.NamedTemporaryFile,
                    delete=False,
                    suffix=os.path.splitext(file.filename)[1]
                )
                content = await file.read()
                await asyncio.to_thread(temp_file_path.write, content)
                file_items.append({
                    "path": temp_file_path.name,
                    "metadata": (file_records or [{}])[len(file_items)] if file_records and len(file_records) > len(file_items) else {}
                })
        else:
            # 从数据文件夹读取文件
            allowed_file_path: tuple[str] = await listdir_allowed_type(
                chroma_config['data_path'],
                tuple(chroma_config['allow_knowledge_file_types'])
            )
            file_items = [{"path": file_path, "metadata": {}} for file_path in allowed_file_path]

        for file_item in file_items:
            file_path = file_item["path"]
            source_metadata = file_item.get("metadata") or {}
            # 2. 计算MD5
            md5_hex = await get_file_md5_hex(file_path)
            if await self.check_md5_hex(md5_hex) and not source_metadata.get("file_id"):
                logger.info(f"【向量数据库】文件 {file_path} 的md5值 {md5_hex} 已存在，跳过")
                # 如果是临时文件，删除
                if files:
                    try:
                        os.unlink(file_path)
                    except:
                        pass
                continue

            try:
                # 3. 加载文档
                document: list[Document] = await self.get_file_document(file_path)
                if not document:
                    logger.error(f"【向量数据库】文件 {file_path} 加载内容为空，跳过")
                    # 如果是临时文件，删除
                    if files:
                        try:
                            os.unlink(file_path)
                        except Exception as e:
                            pass
                    continue

                # 4. 切分文档
                document: list[Document] = await self.spliter.split_documents(document)
                if not document:
                    logger.error(f"【向量数据库】文件 {file_path} 切分内容为空，跳过")
                    # 如果是临时文件，删除
                    if files:
                        try:
                            os.unlink(file_path)
                        except:
                            pass
                    continue

                # 5. 添加用户ID作为元数据
                if user_id:
                    for chunk_index, doc in enumerate(document):
                        doc.metadata['user_id'] = user_id
                        doc.metadata['chunk_index'] = chunk_index
                        for key, value in source_metadata.items():
                            if value is not None:
                                doc.metadata[key] = value
                        if "page" in doc.metadata and doc.metadata["page"] is not None:
                            try:
                                doc.metadata["page"] = int(doc.metadata["page"]) + 1
                            except (TypeError, ValueError):
                                pass

                # 6. 异步写入向量库
                await asyncio.to_thread(self.vectors_store.add_documents, document)

                # 6. 保存MD5
                await self.save_md5_hex(md5_hex)
                logger.info(f"【向量数据库】文件 {file_path} 的md5值 {md5_hex} 已保存")

                # 如果是临时文件，删除
                if files:
                    try:
                        os.unlink(file_path)
                    except:
                        pass

            except Exception as e:
                logger.error(f"【向量数据库】文件 {file_path} 处理时出错: {e}")
                # 如果是临时文件，删除
                if files:
                    try:
                        os.unlink(file_path)
                    except:
                        pass
                continue


if __name__ == '__main__':
    async def main():
        store = VectorStoreService()
        await store.get_document()

        # 等待get_retriever方法完成
        retriever = await store.get_retriever()
        # 直接使用ainvoke方法，因为EnsembleRetriever的invoke可能返回协程
        results = await retriever.ainvoke('扫地')
        print(f"检索结果数量: {len(results)}")
        for result in results:
            print(result)

    asyncio.run(main())


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
        persist_path = str(Path(chroma_dir) / "document_specs")
        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    @property
    def collection(self):
        return self._client.get_or_create_collection(self.COLLECTION_NAME)

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
        """Search for matching document specs."""
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
        chunks, current = [], ""
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


# Singleton instance — populated at startup
document_spec_store = DocumentSpecStore()
