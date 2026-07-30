"""
工友权益明白人 - 智能体主逻辑

采用单Agent多功能架构，通过Prompt工程实现多角色切换：
- 法律顾问：权益问答、维权指引、证据清单
- 安全卫士：安全隐患识别、安全提醒
- 心理伙伴：情绪疏导、危机干预、陪伴
- 薪资管家：工时记录、工资核算、欠条生成
- 工伤取证：多模态图片分析、取证建议

所有功能共享知识库和工具，通过Prompt指导Agent根据场景切换角色。
"""

import os
import json
from typing import Annotated
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, ToolMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver
from tools.knowledge_search_tool import search_law_knowledge, search_hotlines

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40


def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]


@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution errors with custom messages."""
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"工具执行出错，请稍后重试或拨打12333咨询: ({str(e)})",
            tool_call_id=request.tool_call["id"]
        )


def build_agent(ctx=None):
    """
    构建「工友权益明白人」智能体
    
    功能模块：
    1. 法律顾问 - 权益问答、维权指引、证据清单、渠道查询、文书模板
    2. 安全卫士 - 安全隐患识别、安全报告生成、季节性安全提醒
    3. 心理伙伴 - 情绪识别、共情安抚、危机干预、日常陪伴
    4. 薪资管家 - 工时记录指导、工资核算、工资欠条生成、欠薪预警
    5. 工伤取证 - 多模态图片分析、取证建议、证据清单
    
    架构设计：
    - 单Agent多功能架构，通过Prompt工程实现角色切换
    - 共享知识库（20+文档：法律法规、政策解读、典型案例、维权渠道、
      工伤取证、心理援助、安全守护、薪资管家）
    - 工具：知识库检索（search_law_knowledge, search_hotlines）
    - 短期记忆：滑动窗口20轮对话
    """
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    llm = ChatOpenAI(
        model=cfg["config"].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg["config"].get("temperature", 0.7),
        streaming=True,
        timeout=cfg["config"].get("timeout", 600),
        extra_body={
            "thinking": {"type": cfg["config"].get("thinking", "disabled")}
        },
        default_headers=default_headers(ctx) if ctx else {},
    )

    tools = [search_law_knowledge, search_hotlines]

    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=tools,
        middleware=[handle_tool_errors],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
