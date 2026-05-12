import os
import json
import asyncio
from langsmith import traceable
from typing import List, Optional, AsyncGenerator

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from app.agent.agent_middleware import get_middleware
from app.agent.agent_tools import (
    create_schedule_event,
    doc_preview,
    faq_recommend,
    get_campus_route,
    get_schedule_today,
    get_schedule_week,
    get_training_program,
    get_user_info_tools,
    get_weather_tools,
    rag_summary_tools,
    recommend_courses,
    reorder_documents_tools,
    search_campus_locations_tool,
    set_agent_user_context,
    what_time_is_now,
)
from app.core.logger_handler import logger
from app.db.db_config import AsyncSessionLocal
from app.rag.rag_service import RagService
from app.rag.vector_store import is_training_program_query
from app.services import session_manager as sm
from app.services.campus_ai_service import campus_result_to_history, handle_campus_ai_message
from app.services.schedule_ai_service import handle_schedule_ai_message
from app.utils.prompt_loader import load_prompt


class AgentFactory:
    """
    生产 Agent 工厂类
    支持：
    - 每次调用创建全新的 AgentExecutor 实例
    - 动态注入工具、提示词、模型配置
    - 支持异步流式调用
    """

    def __init__(
            self,
            model: str = "deepseek-chat",
            api_key: Optional[str] = None,
            default_tools: Optional[List[BaseTool]] = None,
            default_middleware: Optional[List] = None,
            default_system_prompt: Optional[str] = None,
    ):
        """
        初始化工厂配置（仅配置，不创建实例）
        :param model: 默认模型名称
        :param api_key: 默认 API Key（不传则从env读取）
        :param default_tools: 默认工具列表
        :param default_system_prompt: 默认系统提示词
        """
        self.model = model
        self.api_key = api_key or os.getenv("CHAT_API_KEY")
        self.default_tools = default_tools or self._get_default_tools()
        self.default_middleware = default_middleware or self._get_default_middleware()
        self.default_system_prompt = default_system_prompt or self._get_default_system_prompt()

    @staticmethod
    def _get_default_tools() -> List[BaseTool]:
        """获取默认工具列表"""
        return [
            rag_summary_tools,
            get_weather_tools,
            what_time_is_now,
            get_user_info_tools,
            reorder_documents_tools,
            get_schedule_week,
            get_schedule_today,
            create_schedule_event,
            search_campus_locations_tool,
            get_campus_route,
            get_training_program,
            recommend_courses,
            doc_preview,
            faq_recommend,
        ]

    def _get_default_middleware(self) -> List:
        """获取默认中间件列表"""
        return get_middleware()

    @staticmethod
    def _get_default_system_prompt() -> str:
        """获取默认系统提示词"""
        return load_prompt('main_prompt')

    def _create_chat_model(self, custom_model: Optional[str] = None):
        """内部方法：创建聊天模型实例"""
        return ChatOpenAI(
            model=custom_model or self.model,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
            streaming=True,
            temperature=0.7,
        )

    def _create_prompt(self, custom_system_prompt: Optional[str] = None) -> ChatPromptTemplate:
        """内部方法：创建提示词模板"""
        return ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

    def create_agent_executor(
            self,
            custom_tools: Optional[List[BaseTool]] = None,
            custom_model: Optional[str] = None,
            custom_system_prompt: Optional[str] = None,
            verbose: bool = True,
            return_intermediate_steps: bool = True,
            **kwargs
    ) -> AgentExecutor:
        """
        核心工厂方法：创建全新的 AgentExecutor 实例
        每次调用都会生成新的实例，彻底避免全局状态污染

        :param custom_tools: 自定义工具列表（覆盖默认）
        :param custom_model: 自定义模型（覆盖默认）
        :param custom_system_prompt: 自定义系统提示词（覆盖默认）
        :param verbose: 是否打印详细日志
        :param return_intermediate_steps: 是否返回中间步骤
        :param kwargs: 其他 AgentExecutor 参数
        :return: 全新的 AgentExecutor 实例
        """
        # 1. 创建组件（每次都重新创建，避免全局状态污染）
        chat_model = self._create_chat_model(custom_model)
        prompt = self._create_prompt()
        tools = custom_tools or self.default_tools
        system_prompt = custom_system_prompt or self.default_system_prompt

        # 2. 创建 Agent
        agent = create_tool_calling_agent(chat_model, tools, prompt)

        # 3. 创建 Executor
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=verbose,
            return_intermediate_steps=return_intermediate_steps,
            **kwargs
        )


# 初始化全局工厂配置
agent_factory = AgentFactory()


def get_agent_executor():
    """
    获取AgentExecutor实例，用于LangGraph
    :return: AgentExecutor实例
    """
    return agent_factory.create_agent_executor()


async def get_agent_response(
        query: str,
        history: Optional[List[tuple]] = None,
        custom_tools: Optional[List[BaseTool]] = None,
        **kwargs
):
    """
    获取 Agent 响应（使用工厂创建实例）
    :param query: 用户查询
    :param history: 会话历史 [(user_msg, assistant_msg), ...]
    :param custom_tools: 自定义工具（可选，用于动态切换工具）
    :param kwargs: 其他工厂参数
    :return: 响应结果
    """
    try:
        # 1. 从工厂获取全新的 Executor 实例
        agent_executor = agent_factory.create_agent_executor(custom_tools=custom_tools, **kwargs)

        # 注入用户上下文（供工具访问）
        set_agent_user_context(kwargs.get("user_id", ""))

        # 2. 构建聊天历史
        chat_history: List[BaseMessage] = []
        if history:
            from langchain_core.messages import HumanMessage, AIMessage
            for user_msg, assistant_msg in history:
                chat_history.append(HumanMessage(content=user_msg))
                chat_history.append(AIMessage(content=assistant_msg))

        # 3. 流式执行
        full_response = []
        steps = []
        async for chunk in agent_executor.astream({
            "input": query,
            "chat_history": chat_history,
            "system_prompt": agent_factory.default_system_prompt
        }):
            if "output" in chunk:
                full_response.append(chunk["output"])
            if "intermediate_steps" in chunk:
                for action, observation in chunk["intermediate_steps"]:
                    # 记录日志
                    logger.info(f"\n\n🧠 [Agent 思考] {action.log}")
                    logger.info(f"🛠️ [调用工具] {action.tool}")
                    logger.info(f"📥 [工具输入] {action.tool_input}")
                    logger.info(f"📤 [工具结果] {observation}\n")
                    # 收集步骤
                    steps.append({
                        "thought": action.log,
                        "tool": action.tool,
                        "tool_input": action.tool_input,
                        "tool_output": observation
                    })

        return {
            "response": "".join(full_response) if full_response else "抱歉，我无法理解您的请求。",
            "steps": steps
        }

    except Exception as e:
        logger.error(f"Agent 执行错误: {str(e)}", exc_info=True)
        return {
            "response": f"抱歉，处理您的请求时出现了错误: {str(e)}",
            "steps": []
        }

def _credibility(sources: list) -> dict:
    """Compute answer credibility based on source quality."""
    if not sources:
        return {"level": "low", "label": "仅供参考，请进一步核实",
                "icon": "💡", "detail": "当前知识库未找到充分依据"}
    has_high_score = any(s.get("score", 0) > 0.5 for s in sources)
    if has_high_score:
        return {"level": "high", "label": "依据学校正式文件生成",
                "icon": "📌", "detail": f"基于 {len(sources)} 个来源"}
    return {"level": "medium", "label": "部分依据，仅供参考",
            "icon": "⚠️", "detail": f"基于 {len(sources)} 个来源，建议核实"}


@traceable
async def get_agent_stream_response(
        query: str,
        session_id: str,
        user_id: str,
        custom_tools: Optional[List[BaseTool]] = None,
        **kwargs
) -> AsyncGenerator[str, None]:
    """
    获取 Agent 流式响应
    :param query: 用户查询
    :param session_id: 会话 ID
    :param user_id: 用户 ID
    :param custom_tools: 自定义工具（可选）
    :param kwargs: 其他参数
    :return: 流式响应生成器
    """
    try:
        logger.info(f"【Agent流式响应】开始处理请求，用户ID: {user_id}, 会话ID: {session_id}, 查询: {query}")

        set_agent_user_context(user_id)

        # 获取会话历史
        history = await sm.session_manager.get_history(session_id, user_id)
        logger.info(f"【Agent流式响应】获取会话历史成功，历史记录数: {len(history)}")

        # 构建聊天历史
        chat_history: List[BaseMessage] = []
        if history:
            from langchain_core.messages import HumanMessage, AIMessage
            for user_msg, assistant_msg in history:
                chat_history.append(HumanMessage(content=user_msg))
                chat_history.append(AIMessage(content=assistant_msg))

        # 从工厂获取全新的 Executor 实例

        async with AsyncSessionLocal() as db:
            schedule_result = await handle_schedule_ai_message(db, user_id, session_id, query, history)
            if schedule_result.handled:
                response = schedule_result.message
                yield f"data: {json.dumps({'type': 'response', 'content': response, 'session_id': session_id}, ensure_ascii=False)}\n\n"
                await sm.session_manager.add_message(session_id, user_id, query, response)
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': [], 'credibility': _credibility([])}, ensure_ascii=False)}\n\n"
                return

        campus_result = handle_campus_ai_message(query)
        if campus_result.handled:
            payload = campus_result.payload() if campus_result.result_card else campus_result.message
            yield f"data: {json.dumps({'type': 'response', 'content': payload, 'session_id': session_id}, ensure_ascii=False)}\n\n"
            await sm.session_manager.add_message(session_id, user_id, query, campus_result_to_history(campus_result))
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': [], 'credibility': _credibility([])}, ensure_ascii=False)}\n\n"
            return

        if is_training_program_query(query):
            try:
                rag_result = await RagService().rag_summary_with_sources(query)
                sources = rag_result.get("sources") or []
                if sources:
                    payload = {
                        "answer": rag_result.get("answer") or rag_result.get("response") or "",
                        "sources": sources,
                    }
                    yield f"data: {json.dumps({'type': 'response', 'content': payload, 'session_id': session_id}, ensure_ascii=False)}\n\n"
                    await sm.session_manager.add_message(session_id, user_id, query, payload["answer"])
                    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': sources, 'credibility': _credibility(sources)}, ensure_ascii=False)}\n\n"
                    return
            except Exception as rag_error:
                logger.warning(f"【Agent流式响应】培养方案RAG优先检索失败，回退Agent流程: {rag_error}")

        agent_executor = agent_factory.create_agent_executor(custom_tools=custom_tools, **kwargs)

        # 流式执行
        full_response = []
        steps = []

        # 先发送初始响应
        yield f"data: {json.dumps({'type': 'response', 'content': '', 'session_id': session_id}, ensure_ascii=False)}\n\n"

        # 使用agent_executor的astream方法获取流式响应
        async for chunk in agent_executor.astream({
            "input": query,
            "chat_history": chat_history,
            "system_prompt": agent_factory.default_system_prompt
        }):
            if "output" in chunk:
                chunk_content = chunk["output"]
                if chunk_content:
                    full_response.append(chunk_content)
                    yield f"data: {json.dumps({'type': 'response', 'content': chunk_content}, ensure_ascii=False)}\n\n"
                    logger.info(f"【debug】当前响应: {chunk_content}")
                    await asyncio.sleep(0.05)
            if "intermediate_steps" in chunk:
                for action, observation in chunk["intermediate_steps"]:
                    # 记录日志
                    logger.info(f"\n\n🧠 [Agent 思考] {action.log}")
                    logger.info(f"🛠️ [调用工具] {action.tool}")
                    logger.info(f"📥 [工具输入] {action.tool_input}")
                    logger.info(f"📤 [工具结果] {observation}\n")

                    tool_input_serializable = action.tool_input
                    try:
                        json.dumps(tool_input_serializable)
                    except (TypeError, ValueError):
                        tool_input_serializable = str(tool_input_serializable)

                    tool_output_serializable = observation
                    try:
                        json.dumps(tool_output_serializable)
                    except (TypeError, ValueError):
                        tool_output_serializable = str(tool_output_serializable)

                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': action.tool, 'args': tool_input_serializable}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': action.tool, 'result': tool_output_serializable}, ensure_ascii=False)}\n\n"

                    steps.append({
                        "thought": action.log,
                        "tool": action.tool,
                        "tool_input": tool_input_serializable,
                        "tool_output": tool_output_serializable,
                    })

        response = "".join(full_response) if full_response else "抱歉，我无法理解您的请求。"

        # Extract result card from doc_preview tool output (if any)
        result_card = None
        tool_call_names = []
        for step in steps:
            tool_call_names.append(step.get("tool", ""))
            if step.get("tool") == "doc_preview":
                try:
                    card_candidate = json.loads(step.get("tool_output", "{}"))
                    if card_candidate.get("type") in ("document_preview", "document_result"):
                        result_card = card_candidate
                except (json.JSONDecodeError, TypeError):
                    pass

        # Build storable response with metadata
        stored_response = {
            "content": response,
            "card": result_card,
            "tool_calls": tool_call_names,
        }
        stored_str = json.dumps(stored_response, ensure_ascii=False)

        sources = []
        try:
            rag_service = RagService()
            related_docs = await rag_service.retrieve_document(query)
            sources = await rag_service.build_sources(related_docs, query=query)
            if sources:
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources, 'session_id': session_id}, ensure_ascii=False)}\n\n"
        except Exception as source_error:
            logger.warning(f"【Agent流式响应】来源文件生成失败: {source_error}")

        # Store with metadata wrapper so frontend can reconstruct cards on replay
        await sm.session_manager.add_message(session_id, user_id, query, stored_str)
        logger.info(f"【Agent流式响应】添加到会话历史成功")

        # Send done — include card so frontend can render immediately
        done_payload = {'type': 'done', 'session_id': session_id, 'sources': sources, 'steps': steps, 'credibility': _credibility(sources)}
        if result_card:
            done_payload['result_card'] = result_card
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
        logger.info(f"【Agent流式响应】处理完成，会话ID: {session_id}")
    except Exception as e:
        logger.error(f"【Agent流式响应】处理请求失败: {e}", exc_info=True)
        # 发送错误信息
        error_message = f"错误: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'content': error_message, 'session_id': session_id}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
