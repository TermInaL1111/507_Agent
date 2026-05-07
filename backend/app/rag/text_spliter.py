import math
import asyncio
import re
from typing import List, Optional, Any
from langchain.embeddings.base import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.utils.config import chroma_config


class AsyncTextSplitter:
    """
    异步文本分割器类
    
    核心功能：
    - 将文本分割成多个片段
    - 保留标题、段落、列表层级等结构
    - 保证片段语义完整，避免把一个观点拆成多段
    - 使用嵌入模型结合余弦相似度判断语义完整性
    """
    
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200, 
                 separators: Optional[List[str]] = None, 
                 embedding_model: Optional[Embeddings] = None):
        """
        初始化文本分割器
        
        Args:
            chunk_size: 每个文本片段的最大长度
            chunk_overlap: 片段之间的重叠长度
            separators: 分割符列表，用于分割文本
            embedding_model: 嵌入模型，用于计算语义相似度
        """
        # 默认分割符，按优先级排序
        default_separators = chroma_config['separators']
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or default_separators
        self.embedding_model = embedding_model
        
        # 初始化递归字符分割器
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators
        )
    
    async def split_text(self, text: str) -> List[str]:
        """
        分割文本成多个片段
        
        Args:
            text: 要分割的文本
            
        Returns:
            List[str]: 分割后的文本片段列表
        """
        # 使用递归字符分割器分割文本（同步操作，用to_thread包装）
        chunks = await asyncio.to_thread(self.splitter.split_text, text)
        
        # 如果提供了嵌入模型，进一步优化分割结果
        if self.embedding_model:
            chunks = await self._optimize_chunks(chunks)
        
        return chunks
    
    async def split_documents(self, documents: List[Any]) -> List[Any]:
        """
        分割文档列表
        
        Args:
            documents: 文档对象列表
            
        Returns:
            List[Any]: 分割后的文档对象列表
        """
        if chroma_config.get("split_by_article"):
            article_docs = await asyncio.to_thread(self._split_documents_by_article, documents)
            if article_docs:
                return article_docs

        # 使用递归字符分割器分割文档（同步操作，用to_thread包装）
        split_docs = await asyncio.to_thread(self.splitter.split_documents, documents)
        return split_docs

    def _split_documents_by_article(self, documents: List[Any]) -> List[Any]:
        article_pattern = re.compile(r"(第[一二三四五六七八九十百千万\d]+条)")
        split_docs = []

        for source_doc in documents:
            text = getattr(source_doc, "page_content", "") or ""
            metadata = dict(getattr(source_doc, "metadata", {}) or {})
            matches = list(article_pattern.finditer(text))

            if len(matches) < 2:
                split_docs.extend(self.splitter.split_documents([source_doc]))
                continue

            heading = text[:matches[0].start()].strip()
            if len(heading) > 300:
                heading = heading[-300:].strip()

            for index, match in enumerate(matches):
                start = match.start()
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                chunk = text[start:end].strip()
                if not chunk:
                    continue

                next_match = matches[index + 1] if index + 1 < len(matches) else None
                if next_match and len(chunk) < self.chunk_size // 2:
                    next_end = matches[index + 2].start() if index + 2 < len(matches) else len(text)
                    chunk = text[start:next_end].strip()

                if heading:
                    chunk = f"{heading}\n{chunk}"

                chunk_metadata = dict(metadata)
                chunk_metadata["article"] = match.group(1)
                doc_type = source_doc.__class__

                if len(chunk) > self.chunk_size * 1.5:
                    split_docs.extend(self.splitter.split_documents([doc_type(page_content=chunk, metadata=chunk_metadata)]))
                else:
                    split_docs.append(doc_type(page_content=chunk, metadata=chunk_metadata))

        return split_docs
    
    async def _optimize_chunks(self, chunks: List[str]) -> List[str]:
        """
        使用嵌入模型优化分割结果，确保语义完整性
        
        Args:
            chunks: 初步分割的文本片段列表
            
        Returns:
            List[str]: 优化后的文本片段列表
        """
        optimized_chunks = []
        current_chunk = chunks[0]
        
        for i in range(1, len(chunks)):
            # 计算当前片段与下一个片段的语义相似度
            similarity = await self._calculate_similarity(current_chunk, chunks[i])
            
            # 如果相似度高于阈值，合并两个片段
            if similarity > 0.7:  # 相似度阈值
                current_chunk += " " + chunks[i]
            else:
                optimized_chunks.append(current_chunk)
                current_chunk = chunks[i]
        
        # 添加最后一个片段
        optimized_chunks.append(current_chunk)
        
        return optimized_chunks
    
    async def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本片段的语义相似度
        
        Args:
            text1: 第一个文本片段
            text2: 第二个文本片段
            
        Returns:
            float: 两个文本片段的相似度，范围0-1
        """
        if not self.embedding_model:
            return 0.0
        
        embedding1 = self.embedding_model.embed_query(text1)
        embedding2 = self.embedding_model.embed_query(text2)
        
        # 计算余弦相似度
        similarity = self._cosine_similarity(embedding1, embedding2)
        
        return similarity
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
            
        Returns:
            float: 两个向量的余弦相似度，范围0-1
        """
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
