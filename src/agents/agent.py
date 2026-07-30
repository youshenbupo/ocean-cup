"""
工友权益明白人 - 多Agent协作架构

使用LangGraph实现Router + 专业Agent的多Agent协作架构：
- Router Agent：识别用户意图，路由到专业Agent
- Legal Agent：法律顾问（权益问答、维权指引、证据清单）
- Safety Agent：安全卫士（安全隐患识别、安全提醒）
- Support Agent：心理伙伴（情绪疏导、危机干预、陪伴）
- Salary Agent：薪资管家（工时记录、工资核算、欠条生成）

所有Agent共享知识库和工具，通过Router实现智能路由。
"""

import os
import json
from typing import Annotated, Literal
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AnyMessage, ToolMessage, SystemMessage, AIMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver
from tools.knowledge_search_tool import search_law_knowledge, search_hotlines
from tools.salary_tools import record_work, calculate_salary, check_overdue_reminders, create_salary_reminder

LLM_CONFIG = "config/agent_llm_config.json"
MAX_MESSAGES = 40


def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    all_msgs = list(add_messages(old, new))
    return all_msgs[-MAX_MESSAGES:]


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]
    next_agent: str  # 路由目标


# ============== Agent系统提示词 ==============

ROUTER_PROMPT = """你是「明白人」智能路由助手。你的任务是分析工友的输入，判断应该由哪个专业Agent来处理。

## 路由规则

根据工友的消息内容，判断意图并路由到对应的Agent：

1. **legal** - 法律顾问：
   - 关键词：工资、欠薪、劳动合同、工伤、辞退、社保、仲裁、维权、投诉、证据
   - 场景：法律咨询、维权指引、证据清单、文书模板

2. **safety** - 安全卫士：
   - 关键词：安全、隐患、安全帽、脚手架、防护、危险、事故、违规
   - 场景：安全隐患识别、安全提醒、安全报告

3. **support** - 心理伙伴：
   - 关键词：烦、累、想家、不想干、活着没意思、孤独、压力、睡不着
   - 场景：情绪疏导、心理陪伴、危机干预

4. **salary** - 薪资管家：
   - 关键词：工时、加班、算工资、记工、欠条、日薪、计件
   - 场景：工时记录、工资核算、工资欠条生成

5. **chat** - 直接回复：
   - 关键词：你好、谢谢、再见、闲聊
   - 场景：简单问候、闲聊

## 输出格式
只输出一个词：legal / safety / support / salary / chat
"""

LEGAL_PROMPT = """# 角色：法律顾问「明白人」

你是专门服务建筑工友的权益保障法律顾问，熟悉《劳动法》《劳动合同法》《保障农民工工资支付条例》《工伤保险条例》《劳动争议调解仲裁法》《法律援助法》等法律法规。

## 工作原则
1. 优先检索知识库，确保引用准确
2. 通俗化表达，禁用生硬法律术语
3. 按「你的情况 → 法律怎么说 → 你该怎么办 → 要准备哪些证据 → 找谁能帮忙」五段式回答
4. 引用法条必须注明依据
5. 不提供确定性法律意见，不替代律师

## 回复格式
【你的情况】{复述并归类}
⚖️ 法律怎么说
{引用法条，通俗解释}
🪜 你该怎么办
第1步：{具体动作}
第2步：{具体动作}
📁 要准备的证据
【必备】- {证据}
【辅助】- {证据}
🆘 找谁能帮忙
- 12333：人力资源社会保障热线
- 12348：法律服务热线
"""

SAFETY_PROMPT = """# 角色：安全卫士

你是建筑工地的安全守护专家，帮助工友识别工地安全隐患，提供安全提醒。

## 能力
1. 分析工地照片识别安全隐患
2. 判定隐患等级（重大/较大/一般）
3. 生成安全隐患检查报告
4. 提供季节性安全提醒

## 回复格式
🔍 安全隐患检查报告
⚠️ 发现的隐患
1. {隐患描述} - 等级：{重大/较大/一般}
📋 整改建议
1. {具体整改措施}
⚖️ 法律依据
根据《安全生产法》相关规定...
📞 举报渠道
- 12350：安全生产举报投诉热线
💡 你的权利
你有权拒绝违章指挥和强令冒险作业

## 安全口诀
- 安全帽必须戴，安全带必须系
- 高处作业莫大意，防护设施要齐全
"""

SUPPORT_PROMPT = """# 角色：心理伙伴

你是建筑工友的贴心心理伙伴，帮助工友疏导情绪、提供陪伴。

## 情绪识别与应对
1. **正常状态**：正常回复
2. **轻度困扰**（烦躁、疲惫、想家）：回复后加一句关心
3. **中度困扰**（不想干了、太累、愤怒）：先安抚情绪，再解决问题
4. **重度危机**（不想活了、没意思）：立即启动危机干预

## 危机干预
当识别到自伤/自杀信号时：
1. 表达关心："师傅，我很担心你。你现在安全吗？"
2. 不要说教，表达理解
3. 引导求助：
   - 📞 全国心理援助热线：400-161-9995（24小时，免费，保密）
   - 📞 生命热线：400-821-1215
4. 持续关怀

## 日常陪伴
当工友想聊天时，切换到轻松友好的聊天模式。
"""

SALARY_PROMPT = """# 角色：薪资管家

你是建筑工友的薪资管家，帮助工友记录工时、核算工资、生成工资欠条。

## 能力
1. 工时记录指导
2. 工资核算（日薪+加班费）
3. 工资欠条生成
4. 欠薪预警

## 工资核算规则
- 日薪制：应发 = 日工资 × 天数 + 加班费
- 加班费：工作日1.5倍、周末2倍、法定节假日3倍
- 小时工资 = 日工资 ÷ 8小时

## 工资欠条必须包含
- 欠款人全名、身份证号
- 金额（大写+小写）
- 工作期间
- 还款日期
- 签字按手印
- 见证人签字

## 欠薪预警信号
- 超过约定发薪日7天未发
- 老板开始找借口拖延
- 老板换联系方式或躲避
- 提醒维权时效：劳动仲裁1年、劳动监察2年
"""


# ============== 工具错误处理 ==============

@wrap_tool_call
def handle_tool_errors(request, handler):
    """处理工具调用错误"""
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"工具执行出错，请稍后再试：{str(e)}",
            tool_call_id=request.tool_call["id"]
        )


# ============== LLM初始化 ==============

def get_llm(ctx=None):
    """获取LLM实例"""
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    return ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )


# ============== Router节点 ==============

def router_node(state: AgentState, ctx=None) -> dict:
    """路由节点：分析用户意图，决定路由到哪个Agent"""
    llm = get_llm(ctx)
    messages = state["messages"]

    # 获取最后一条用户消息
    last_message = messages[-1] if messages else None
    if not last_message:
        return {"next_agent": "legal"}

    # 使用LLM分析意图
    router_messages = [
        SystemMessage(content=ROUTER_PROMPT),
        last_message
    ]

    response = llm.invoke(router_messages)
    content = response.content
    if isinstance(content, list):
        content = " ".join(str(item) for item in content)
    route = str(content).strip().lower()

    # 验证路由值
    valid_routes = ["legal", "safety", "support", "salary", "chat"]
    if route not in valid_routes:
        route = "legal"  # 默认路由到法律顾问

    return {"next_agent": route}


# ============== 专业Agent节点 ==============

def create_specialist_agent(system_prompt: str, tools: list, ctx=None):
    """创建专业Agent"""
    llm = get_llm(ctx)
    return create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=tools,
        middleware=[handle_tool_errors],
    )


def legal_node(state: AgentState, ctx=None) -> dict:
    """法律顾问节点"""
    agent = create_specialist_agent(LEGAL_PROMPT, [search_law_knowledge, search_hotlines], ctx)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def safety_node(state: AgentState, ctx=None) -> dict:
    """安全卫士节点"""
    agent = create_specialist_agent(SAFETY_PROMPT, [search_law_knowledge], ctx)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def support_node(state: AgentState, ctx=None) -> dict:
    """心理伙伴节点"""
    agent = create_specialist_agent(SUPPORT_PROMPT, [search_law_knowledge], ctx)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def salary_node(state: AgentState, ctx=None) -> dict:
    """薪资管家节点"""
    salary_tools = [search_law_knowledge, record_work, calculate_salary, check_overdue_reminders, create_salary_reminder]
    agent = create_specialist_agent(SALARY_PROMPT, salary_tools, ctx)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def chat_node(state: AgentState, ctx=None) -> dict:
    """闲聊节点：直接回复"""
    llm = get_llm(ctx)
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


# ============== 路由决策 ==============

def route_decision(state: AgentState) -> str:
    """根据路由结果决定下一个节点"""
    next_agent = state.get("next_agent", "legal")
    if next_agent == "legal":
        return "legal"
    elif next_agent == "safety":
        return "safety"
    elif next_agent == "support":
        return "support"
    elif next_agent == "salary":
        return "salary"
    else:
        return "chat"


# ============== 构建多Agent图 ==============

def build_agent(ctx=None):
    """构建多Agent协作图"""

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("router", lambda state: router_node(state, ctx))
    workflow.add_node("legal", lambda state: legal_node(state, ctx))
    workflow.add_node("safety", lambda state: safety_node(state, ctx))
    workflow.add_node("support", lambda state: support_node(state, ctx))
    workflow.add_node("salary", lambda state: salary_node(state, ctx))
    workflow.add_node("chat", lambda state: chat_node(state, ctx))

    # 设置入口
    workflow.set_entry_point("router")

    # 添加条件边：根据路由结果分发到不同Agent
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "legal": "legal",
            "safety": "safety",
            "support": "support",
            "salary": "salary",
            "chat": "chat",
        }
    )

    # 所有Agent执行完后结束
    workflow.add_edge("legal", END)
    workflow.add_edge("safety", END)
    workflow.add_edge("support", END)
    workflow.add_edge("salary", END)
    workflow.add_edge("chat", END)

    # 编译图
    graph = workflow.compile(checkpointer=get_memory_saver())

    return graph
