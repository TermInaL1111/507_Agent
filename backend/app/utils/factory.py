from abc import ABC, abstractmethod
from typing import Optional
import os
from dotenv import load_dotenv

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.utils.config import rag_config

# 加载环境变量
load_dotenv()


class BaseModelFactory(ABC):
    """基础模型工厂"""

    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        """生成模型"""
        pass


class ChatModelFactory(BaseModelFactory):
    """聊天模型工厂"""
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        """生成模型"""
        return ChatTongyi(
            model=rag_config['chat_model_name'],
            api_key=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
            streaming=True,
            top_p=0.7,
        )


class EmbedModelFactory(BaseModelFactory):
    """嵌入模型工厂"""
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        """生成模型"""
        return DashScopeEmbeddings(
            model=rag_config['text_embedding_model_name'],
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
        )


class RerankerModelFactory(BaseModelFactory):
    """重排序模型工厂 - 已废弃，使用CrossEncoder模型"""
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        """生成模型"""
        # 注意：重排序服务已改为使用sentence_transformers的CrossEncoder模型
        # 这个工厂不再使用，保留仅为向后兼容
        return None


chat_model = ChatModelFactory().generator()
embed_model = EmbedModelFactory().generator()
# 重排序模型已改为使用CrossEncoder，不再使用Ollama模型
reranker_model = None
