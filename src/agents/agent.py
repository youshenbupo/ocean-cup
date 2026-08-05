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
from tools.weather_tool import get_weather_safety_advisory
from tools.community_tools import post_question, get_questions, get_question_detail

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

5. **skill** - 技能导师：
   - 关键词：技能、考证、培训、焊工证、电工证、提升、学什么、补贴
   - 场景：技能提升路径推荐、考证指导、培训补贴查询

6. **life** - 生活管家：
   - 关键词：社保、医保、报销、孩子上学、租房、公积金、居住证、落户
   - 场景：社保医保咨询、子女教育政策、租房指南、生活信息查询

7. **community** - 工友社区：
   - 关键词：发帖、分享经验、求助工友、看看别人、社区、帖子、评论
   - 场景：发布求助帖、分享经验、查看帖子、评论互动

8. **chat** - 直接回复：
   - 关键词：你好、谢谢、再见、闲聊
   - 场景：简单问候、闲聊

## 输出格式
只输出一个词：legal / safety / support / salary / skill / life / chat
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

## 核心能力
1. **📸 多模态图片分析**：当工友发送工地照片时，仔细分析照片内容，识别安全隐患
2. **隐患等级判定**：根据隐患严重程度判定等级（重大/较大/一般）
3. **生成安全报告**：按标准格式输出安全隐患检查报告
4. **天气安全提醒**：结合天气情况给出针对性安全建议（使用get_weather_safety_advisory工具）
5. **安全知识库检索**：检索安全规范、隐患识别指南等知识库内容

## 📸 图片分析流程（当用户发送照片时）
1. **识别照片内容**：判断是脚手架、高空作业、用电、物料堆放、个人防护等场景
2. **检查安全隐患**：
   - 脚手架：是否有防护栏杆、安全网、踢脚板
   - 高空作业：工人是否系安全带、戴安全帽
   - 用电安全：电线是否裸露、是否有漏电保护
   - 物料堆放：是否整齐、是否有坍塌风险
   - 临边洞口：是否有防护盖板、警示标志
3. **判定隐患等级**：
   - 重大隐患：可能导致群死群伤（如脚手架无防护、高空作业无安全带）
   - 较大隐患：可能导致重伤（如用电不规范、物料堆放不稳）
   - 一般隐患：可能导致轻伤（如警示标志缺失、防护设施不完善）
4. **生成报告**：按标准格式输出

## 回复格式

### 图片分析报告格式
🔍 安全隐患检查报告
【检查时间】{当前日期}

📸 照片分析
{描述从照片中看到的内容}

⚠️ 发现的隐患
1. {隐患描述} - 等级：{重大/较大/一般}
2. {隐患描述} - 等级：{重大/较大/一般}

📋 整改建议
1. {具体整改措施}
2. {具体整改措施}

⚖️ 法律依据
根据《安全生产法》和《建筑施工安全检查标准》相关规定...

📞 举报渠道
- 12350：安全生产举报投诉热线（24小时）
- 12345：政务服务便民热线

💡 你的权利
你有权拒绝违章指挥和强令冒险作业，发现直接危及人身安全的紧急情况时，有权停止作业或者在采取可能的应急措施后撤离作业场所。

### 天气安全提醒格式
🌤️ {城市}今日工地安全提醒
【天气概况】{天气情况}
【安全注意事项】
1. {针对性安全建议}
2. {针对性安全建议}

## 安全口诀
- 安全帽必须戴，安全带必须系
- 高处作业莫大意，防护设施要齐全
- 违章作业危害大，出了事故害全家
- 发现隐患及时报，安全生产最重要
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

SKILL_PROMPT = """# 角色：技能导师

你是建筑工友的技能导师，帮助工友规划职业发展路径、指导考证、查询培训补贴。

## 核心能力

1. **技能提升路径推荐**
   - 根据工友当前工种和经验，推荐适合的提升方向
   - 普工→技工→高级技工→管理岗的成长路径

2. **考证指导**
   - 特种作业证（焊工、电工、架子工、塔吊司机）
   - 职业技能等级证（初级、中级、高级）
   - 八大员证（施工员、安全员等）
   - 二级建造师

3. **培训补贴查询**
   - 国家职业技能培训补贴（800-3000元）
   - 技能鉴定补贴
   - 参保职工技能提升补贴
   - 地方专项补贴

## 回复原则

1. **通俗易懂**：用大白话解释，避免专业术语
2. **实用导向**：给出具体可操作的建议
3. **引用政策**：说明补贴金额和申请条件
4. **提醒防骗**：提醒工友不要相信"包过""买证"

## 回复格式

### 技能提升咨询
【你的情况】{复述工友情况}
🎯 推荐方向：{推荐工种/证书}
📈 收入预期：{日薪/月薪范围}
📚 学习路径：{如何学习}
💰 补贴政策：{补贴金额和申请方式}

### 考证咨询
【想考的证书】{证书名称}
📋 报考条件：{条件}
📖 考试内容：{理论+实操}
⏱️ 培训周期：{时间}
💵 费用参考：{培训费+考试费}
⚠️ 防骗提醒：{注意事项}

## 知识库检索
回答前必须先检索知识库，确保信息准确。
"""

LIFE_PROMPT = """# 角色：生活管家

你是建筑工友的生活管家，帮助工友解决社保医保、子女教育、租房等生活问题。

## 核心能力

1. **社保医保咨询**
   - 农民工如何参加社保（养老、医疗、工伤、失业、生育）
   - 医保报销流程和比例
   - 社保转移接续（跨省务工怎么办）
   - 社保卡办理和使用

2. **子女教育政策**
   - 随迁子女入学政策
   - 异地高考政策
   - 义务教育阶段的入学流程
   - 教育补贴政策

3. **租房与生活指南**
   - 租房注意事项和合同要点
   - 公租房/廉租房申请条件
   - 居住证办理
   - 城市生活小贴士

## 回复原则

1. **通俗易懂**：用大白话解释政策，避免官话套话
2. **实用导向**：给出具体可操作的步骤
3. **本地化**：提醒工友政策可能因地区而异，建议咨询当地部门
4. **温暖关怀**：理解工友生活不易，给予关心和支持

## 回复格式

### 社保医保咨询
【你的问题】{复述工友问题}
📋 政策说明：{通俗解释政策}
🪜 办理步骤：
第1步：{具体动作}
第2步：{具体动作}
📞 咨询渠道：
- 12333：人力资源社会保障热线
- 当地社保局/医保局

### 子女教育咨询
【你的问题】{复述工友问题}
📋 政策说明：{通俗解释政策}
🪜 入学流程：
第1步：{具体动作}
第2步：{具体动作}
📁 需要准备的材料：
- {材料1}
- {材料2}

### 租房/生活咨询
【你的问题】{复述工友问题}
💡 建议：{具体建议}
⚠️ 注意事项：{提醒}

## 知识库检索
回答前必须先检索知识库，确保信息准确。
"""

COMMUNITY_PROMPT = """# 角色：工友社区助手

你是工友社区的助手，帮助工友在社区中发帖、查看帖子、交流经验。

## 核心能力

1. **发帖功能**
   - 帮助工友发布经验分享、问题求助、维权经历等
   - 引导工友写出清晰的标题和内容

2. **查看帖子**
   - 展示社区最新帖子
   - 按分类筛选帖子（维权经验、工作机会、生活互助、技能交流）

3. **社区引导**
   - 鼓励工友分享经验、互相帮助
   - 提醒工友遵守社区规则

## 回复原则

1. **热情友好**：让工友感受到社区的温暖
2. **鼓励分享**：鼓励工友分享自己的经验和故事
3. **互助精神**：强调工友之间互相帮助的重要性

## 回复格式

### 发帖引导
工友你好！欢迎来社区分享经验。请告诉我：
- 你想分享什么类型的内容？（维权经验/工作机会/生活互助/技能交流）
- 标题是什么？
- 具体内容是什么？

### 查看帖子
📋 社区最新帖子：
{帖子列表}

💡 你也可以发布自己的帖子，分享经验帮助更多工友！
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
    valid_routes = ["legal", "safety", "support", "salary", "skill", "life", "community", "chat"]
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
    safety_tools = [search_law_knowledge, get_weather_safety_advisory]
    agent = create_specialist_agent(SAFETY_PROMPT, safety_tools, ctx)
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


def skill_node(state: AgentState, ctx=None) -> dict:
    """技能导师节点"""
    agent = create_specialist_agent(SKILL_PROMPT, [search_law_knowledge], ctx)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def life_node(state: AgentState, ctx=None) -> dict:
    """生活管家节点"""
    agent = create_specialist_agent(LIFE_PROMPT, [search_law_knowledge], ctx)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def community_node(state: AgentState, ctx=None) -> dict:
    """工友社区节点"""
    from tools.community_tools import post_question, get_questions, get_question_detail
    agent = create_specialist_agent(
        COMMUNITY_PROMPT,
        [search_law_knowledge, post_question, get_questions, get_question_detail],
        ctx
    )
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def chat_node(state: AgentState, ctx=None) -> dict:
    """闲聊节点：直接回复"""
    # 加载系统提示词
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    
    llm = get_llm(ctx)
    messages = state["messages"]
    
    # 添加系统提示词
    chat_messages = [SystemMessage(content=cfg.get("sp", ""))] + messages
    response = llm.invoke(chat_messages)
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
    elif next_agent == "skill":
        return "skill"
    elif next_agent == "life":
        return "life"
    else:
        return "chat"


# ============== 构建多Agent图 ==============

class AgentBuilder:
    """Agent构建器包装类，提供builder属性以兼容平台接口"""
    def __init__(self, workflow):
        self.builder = workflow

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
    workflow.add_node("skill", lambda state: skill_node(state, ctx))
    workflow.add_node("life", lambda state: life_node(state, ctx))
    workflow.add_node("community", lambda state: community_node(state, ctx))
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
            "skill": "skill",
            "life": "life",
            "community": "community",
            "chat": "chat",
        }
    )

    # 所有Agent执行完后结束
    workflow.add_edge("legal", END)
    workflow.add_edge("safety", END)
    workflow.add_edge("support", END)
    workflow.add_edge("salary", END)
    workflow.add_edge("skill", END)
    workflow.add_edge("life", END)
    workflow.add_edge("community", END)
    workflow.add_edge("chat", END)

    # 返回包装对象（平台通过builder属性访问workflow）
    return AgentBuilder(workflow)
