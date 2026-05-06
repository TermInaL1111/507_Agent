from typing import List, Dict, Any

import asyncio
import os
import requests
from dotenv import load_dotenv

try:
    import torch
except ImportError:
    torch = None

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

from app.core.logger_handler import logger


# 加载环境变量
load_dotenv()


def check_and_download_reranker_model() -> None:
    """检查并重排序模型，在FastAPI启动时执行"""
    api_url = os.getenv("RERANKER_API_URL", "").strip()
    if api_url:
        logger.info(f"✅ 检测到远程重排序API配置：{api_url}，跳过本地模型检查")
        return

    LOCAL_MODEL_PATH = os.getenv("RERANKER_MODEL_PATH", r"D:\Hugging_Face\models\Qwen3-Reranker-0.6B")
    HF_MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"

    if torch is None or CrossEncoder is None:
        raise RuntimeError("未检测到本地重排序依赖，请安装 torch 和 sentence-transformers，或配置 RERANKER_API_URL 使用远程API")


    try:
        # 检查本地模型是否存在
        if os.path.exists(LOCAL_MODEL_PATH) and os.path.isdir(LOCAL_MODEL_PATH):
            logger.info(f"✅ 检测到本地重排序模型：{LOCAL_MODEL_PATH}")
        else:
            logger.warning(f"⚠️  本地模型未找到：{LOCAL_MODEL_PATH}")
            logger.info(f"🔄 开始自动下载模型：{HF_MODEL_NAME}")

            # 创建模型目录
            os.makedirs(LOCAL_MODEL_PATH, exist_ok=True)

            # 自动下载模型
            device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
            model = CrossEncoder(
                HF_MODEL_NAME,
                max_length=512,
                device=device,
                cache_folder=LOCAL_MODEL_PATH

            )
            logger.info(f"✅ 模型下载完成，使用设备：{device}")

    except Exception as e:
        logger.error(f"❌ 模型检查失败: {str(e)}")
        raise RuntimeError(f"重排序模型检查失败: {str(e)}")


class ReorderService:

    """文档重排序服务"""

    def __init__(self):
        # 远程API配置（配置后优先走远程API模式）
        self.api_url = os.getenv("RERANKER_API_URL", "").strip()
        self.api_key = os.getenv("RERANKER_API_KEY", os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")).strip()
        self.api_timeout = float(os.getenv("RERANKER_API_TIMEOUT", "20"))
        self.api_provider = os.getenv("RERANKER_API_PROVIDER", "generic").strip().lower()
        self.api_model = os.getenv("RERANKER_API_MODEL", "gte-rerank-v2").strip()
        self._use_remote_api = bool(self.api_url)


        # 从环境变量读取重排序模型路径
        self.LOCAL_MODEL_PATH = os.getenv("RERANKER_MODEL_PATH", r"D:\Hugging_Face\models\Qwen3-Reranker-0.6B")
        # Hugging Face模型名称
        self.HF_MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"
        # 自动选择设备（优先使用GPU）
        self.device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        # 模型实例（懒加载）
        self._model = None

    async def _get_model(self):
        """懒加载模型实例"""
        if self._use_remote_api:
            raise RuntimeError("当前已配置远程重排序API，不需要加载本地模型")

        if CrossEncoder is None:
            raise RuntimeError("本地重排序依赖缺失：sentence-transformers 未安装")

        if self._model is None:
            logger.info(f"✅ 加载重排序模型：{self.LOCAL_MODEL_PATH}")
            self._model = CrossEncoder(
                self.LOCAL_MODEL_PATH,
                max_length=512,

                device=self.device,
                local_files_only=True
            )
            # 强制使用评估模式，避免训练模式下的随机性
            self._model.eval()
            logger.info(f"✅ 模型加载成功，使用设备：{self.device}")
        return self._model

    @property
    async def model(self):
        """获取模型实例（懒加载）"""
        return await self._get_model()

    @staticmethod
    def _normalize_remote_documents(payload: Any, original_documents: List[str]) -> List[Dict[str, Any]]:
        """兼容多种远程API返回结构并标准化为 documents 列表"""
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("output"), dict)
            and isinstance(payload["output"].get("results"), list)
        ):
            normalized_dashscope = []
            for item in payload["output"]["results"]:
                if not isinstance(item, dict):
                    continue

                doc_index = item.get("index")
                if isinstance(doc_index, int) and 0 <= doc_index < len(original_documents):
                    document = original_documents[doc_index]
                else:
                    document = ""

                raw_similarity = item.get("relevance_score", 0.0)
                try:
                    similarity = float(raw_similarity)
                except (TypeError, ValueError):
                    similarity = 0.0

                normalized_dashscope.append({
                    "document": str(document),
                    "similarity": similarity,
                })

            return normalized_dashscope

        remote_documents = None

        if isinstance(payload, dict):
            if isinstance(payload.get("documents"), list):
                remote_documents = payload.get("documents")
            elif isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("documents"), list):
                remote_documents = payload["data"]["documents"]
            elif isinstance(payload.get("data"), list):
                remote_documents = payload.get("data")

        if remote_documents is None:
            raise ValueError("远程重排序API返回格式不支持，未找到 documents/data 字段")

        normalized = []
        for item in remote_documents:
            if isinstance(item, dict):
                document = item.get("document") or item.get("text") or item.get("content") or ""
                raw_similarity = item.get("similarity", item.get("score", 0.0))
            else:
                document = str(item)
                raw_similarity = 0.0

            try:
                similarity = float(raw_similarity)
            except (TypeError, ValueError):
                similarity = 0.0

            normalized.append({
                "document": str(document),
                "similarity": similarity,
            })

        return normalized

    def _build_remote_payload(self, query: str, documents: List[str]) -> Dict[str, Any]:
        """根据 provider 生成远程API请求体"""
        if self.api_provider in {"aliyun", "dashscope"} or "dashscope.aliyuncs.com" in self.api_url:
            return {
                "model": self.api_model,
                "input": {
                    "query": query,
                    "documents": documents,
                },
            }

        return {
            "query": query,
            "documents": documents,
        }

    def _call_remote_reorder_api(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """调用远程重排序API"""
        if not self.api_url:
            raise ValueError("RERANKER_API_URL 未配置")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(
            self.api_url,
            json=self._build_remote_payload(query, documents),
            headers=headers,
            timeout=self.api_timeout,
        )
        response.raise_for_status()

        normalized_docs = self._normalize_remote_documents(response.json(), documents)
        logger.info(f"【重排序服务】远程API调用成功，返回 {len(normalized_docs)} 个文档")
        return normalized_docs

    async def reorder_documents(self, query: str, documents: List[str]) -> Dict[str, Any]:

        """
        对文档进行重排序
        :param query: 查询语句
        :param documents: 文档列表
        :return: 包含重排序结果的字典，格式为：
                 {"success": bool, "documents": List[Dict], "error": str}
        """
        try:
            if not documents:
                return {
                    "success": True,
                    "documents": [],
                    "error": ""
                }

            if self._use_remote_api:
                sorted_docs = await asyncio.to_thread(self._call_remote_reorder_api, query, documents)
                sorted_docs = sorted(sorted_docs, key=lambda x: x.get("similarity", 0.0), reverse=True)
                return {
                    "success": True,
                    "documents": sorted_docs,
                    "error": ""
                }

            # 构造查询+文档对
            pairs = [(query, doc) for doc in documents]

            # 使用模型进行批量预测（batch_size=1避免padding令牌报错）
            model = await self.model
            # 禁用梯度计算，提高推理性能
            with torch.no_grad():
                scores = model.predict(pairs, batch_size=1)

            
            # 构建结果列表
            scored_documents = []
            for doc, score in zip(documents, scores):
                scored_documents.append({
                    "document": doc,
                    "similarity": float(score)
                })
                logger.info(f"【重排序服务】文档相似度分数: {score:.4f}")
            
            # 按相似度分数降序排序
            sorted_docs = sorted(scored_documents, key=lambda x: x["similarity"], reverse=True)
            logger.info(f"【重排序服务】文档重排序成功，返回 {len(sorted_docs)} 个文档")
            
            return {
                "success": True,
                "documents": sorted_docs,
                "error": ""
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"【重排序服务】重排序失败: {error_msg}")
            return {
                "success": False,
                "documents": [],
                "error": error_msg
            }

    @staticmethod
    async def format_reorder_result(sorted_docs: List[Dict]) -> str:
        """
        格式化重排序结果
        :param sorted_docs: 重排序后的文档列表
        :return: 格式化后的字符串
        """
        formatted_result = "重排序后的文档列表：\n"
        for i, doc in enumerate(sorted_docs, 1):
            formatted_result += f"{i}. 相似度: {doc.get('similarity', 0):.4f}\n"
            formatted_result += f"   内容: {doc.get('document', '')}\n\n"
        return formatted_result


# 全局重排序服务实例
reorder_service = ReorderService()