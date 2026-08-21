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
import re
import json
import logging
from typing import Annotated, Literal
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AnyMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver
from tools.knowledge_search_tool import search_law_knowledge, search_hotlines
from tools.salary_tools import record_work, calculate_salary, check_overdue_reminders, create_salary_reminder, mark_reminder_paid, get_my_reminders
from tools.weather_tool import get_weather_safety_advisory
from tools.community_tools import post_question, get_questions, get_question_detail, add_comment
from tools.user_identity_tool import set_my_name, who_am_i
from tools.legal_doc_tool import generate_arbitration_application, generate_wage_complaint, generate_iou, generate_wage_slip
from tools.cert_tool import record_cert, check_cert_expiry, get_cert_renewal_guide
from tools.expense_tool import record_expense, get_expense_summary, get_expense_list
from utils.sensitive_mask import mask_sensitive_info

logger = logging.getLogger(__name__)

LLM_CONFIG = "config/agent_llm_config.json"
MAX_MESSAGES = 40

# 深度思考模式前缀：前端开启"思考模式"时在用户消息前追加，后端据此决定是否对输出做二轮 LLM 优化
THINK_PREFIX = "【深度思考】"
THINK_PREFIX_ALIASES = ["[深度思考]", "（深度思考）", "【深度思考模式】", "[深度思考模式]"]

# 个人信息解析前缀：前端"我的"页面"智能解析"功能在用户自述文本前追加，
# 后端据此将请求路由到专门的解析节点，从自然语言中提取结构化工友信息（返回纯 JSON）
PROFILE_PARSE_PREFIX = "【解析工友信息】"


def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    all_msgs = list(add_messages(old, new))
    return all_msgs[-MAX_MESSAGES:]


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]
    next_agent: str  # 路由目标
    think_mode: bool  # 思考模式标记：True 时专业节点输出后再经一轮 LLM 优化


# ============== Agent系统提示词 ==============

ROUTER_PROMPT = """你是「明白人」智能路由助手。你的任务是分析工友的输入，判断应该由哪个专业Agent来处理。

## 路由规则

根据工友的消息内容，判断意图并路由到对应的Agent：

1. **legal** - 法律顾问：
   - 关键词：工资、欠薪、劳动合同、工伤、辞退、社保、仲裁、维权、投诉、证据
   - 场景：法律咨询、维权指引、证据清单、文书模板
   - **特别优先**：若工友表达自己实施或打算实施的暴力、伤害、报复、威胁等违法风险（如"我把老板打了""我要报复他""我要教训他"），必须路由到 legal，由法律顾问做守法劝诫与法律风险提示，绝不可路由到 chat 或其他节点。

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

## 指代消解
若「当前提问」较短且包含指代（如"那怎么办""然后呢""该怎么做""还有吗"），必须结合「历史提问」判断真实意图，路由到与历史话题一致的专业 Agent（例如历史在讨论打人后的法律后果，则继续路由到 legal）。

## 输出格式
【严格指令】只输出以下8个词中的一个，不要输出任何其他内容（不要标点、不要解释、不要序号）：

legal / safety / support / salary / skill / life / community / chat

错误示例："我认为应该路由到legal" → 正确：legal
错误示例："**legal**" → 正确：legal
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

你是建筑工友的心理支持助手，帮助疏导情绪、提供陪伴。

## 重要原则
1. 你不了解用户个人信息，不要编造或假设
2. 不要使用过度亲昵的称呼（如"老哥""师傅"），用"你"称呼
3. 保持专业但温暖的语气

## 情绪识别与应对
1. **正常状态**：正常回复
2. **轻度困扰**（烦躁、疲惫、想家）：回复后加一句关心
3. **中度困扰**（不想干了、太累、愤怒）：先安抚情绪，再解决问题
4. **重度危机**（不想活了、没意思）：立即启动危机干预

## 危机干预
当识别到自伤/自杀信号时：
1. 表达关心："我很担心你，你现在安全吗？"
2. 不要说教，表达理解
3. 引导求助：
   - 📞 全国心理援助热线：400-161-9995（24小时，免费，保密）
   - 📞 生命热线：400-821-1215
4. 持续关怀

## 日常陪伴
当用户想聊天时，切换到轻松友好的聊天模式。
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
欢迎来社区分享经验！请告诉我：
- 你想分享什么类型的内容？（维权经验/工作机会/生活互助/技能交流）
- 标题是什么？
- 具体内容是什么？

### 查看帖子
📋 社区最新帖子：
{帖子列表}

💡 你也可以发布自己的帖子，分享经验帮助更多工友！
"""


# ============== 通用回复规则（所有专业Agent + 闲聊节点统一追加） ==============

COMMON_REPLY_RULES = """

## 本轮通用要求（务必逐条遵守）
0. **安全与守法边界（最高优先级，凌驾于其他所有规则之上）**：若用户表达了自己**已经实施、正在实施或打算实施**暴力、伤害、威胁、报复他人等违法行为（例如"我把老板打了""我想报复他""我要找人收拾他""想砍人"等），你必须：
   - 第一时间严肃、明确地告知：该行为**涉嫌违法**，可能违反《治安管理处罚法》被行政拘留、罚款；若造成轻伤以上后果，还可能构成**故意伤害罪**（《刑法》第234条）被追究刑事责任，留下案底会影响本人及子女。
   - 冷静劝诫用户**立即停止暴力、防止事态升级**，不要进一步激化矛盾。
   - 引导合法解决途径：现场冲突可拨打 110 由警方处理；若因欠薪、工伤等纠纷引发，应通过劳动监察（12333）、劳动仲裁或法律援助（12348）等合法渠道维权。
   - **严禁**输出无关的自我介绍、通用维权模板，严禁美化、教唆、纵容任何违法行为。
1. **先判断问题类型**：
   - 若用户是「泛泛请教 / 希望讲解某领域知识」（例如"讲讲劳动法""工伤认定有哪些""怎么考证""社保怎么交"），请**直接、系统地讲解该主题的核心要点**（概念、分类、关键规定、注意事项、常见误区），不要反问用户、不要只发欢迎语或自我介绍。
   - 若用户是「具体求助」（例如"老板欠我3万怎么办""我受伤了怎么认定工伤"），则按你的专业流程给出针对性方案。
2. **针对性回答**：紧扣用户本次的具体问题展开，避免每一轮都输出相同的大段通用介绍或欢迎语。
3. **结尾附权益小结**：每轮回复末尾，单独新增「## 💡 权益点小结」小节，用 1-3 条 bullet（- 开头，每条一行）概括本轮最关键、最该记住的权益要点或行动提醒。
4. **法律依据与风险提示**：涉及具体法律规定时，明确写出依据来源（例如「依据《劳动争议调解仲裁法》第X条」）；在「权益点小结」之后，附一句风险提示「各地执行细则可能不同，具体以当地人社局/仲裁委答复为准」。
5. **信息不足时的折中处理**：若用户是具体求助（欠薪/工伤等）但关键信息缺失（如金额、时间、是否签合同），必须**先基于现有信息给出可执行方案**，再用 1-2 句话追问最关键的缺失信息；**禁止只追问不回答**。
6. 生成文书若缺少必填信息（如姓名、金额、时间），先给出模板与填写说明，再请用户补充。
7. **忽略思考标记**：若用户消息以「【深度思考】」开头（表示用户开启了"思考模式"），请忽略该标记本身，直接针对标记之后的内容正常回答，不要把它当作问题的一部分。
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

_llm_cache = {}

def get_llm(ctx=None, temperature_override=None):
    """获取LLM实例（带缓存，避免重复创建）"""
    cache_key = f"{temperature_override}"
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=temperature_override if temperature_override is not None else cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )
    _llm_cache[cache_key] = llm
    return llm


def _get_last_user_message(messages):
    """提取最后一条用户消息，避免将完整历史传给专业Agent"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg
    return messages[-1] if messages else None


def _get_recent_messages(messages, max_messages=6):
    """提取最近的对话窗口（用户+助手交替），支持专业Agent多轮追问。
    
    策略：从后往前取最近的 max_messages 条消息，保证上下文连贯。
    """
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


# ============== Router节点 ==============

# 关键词快速路由优先级：community > support > skill > safety > salary > legal > life > chat
# 高优先级放前面，当多个关键词同时命中时，优先匹配更具体的意图
_KEYWORD_ROUTE_PRIORITY = ["community", "support", "skill", "safety", "salary", "legal", "life"]

_KEYWORD_ROUTE_MAP = {
    "community": ["发帖", "帖子", "社区", "工友经验", "交流", "互助", "分享", "讨论",
                  "看看大家", "问问大家", "评论", "回帖"],
    "support": ["心理", "心情", "压力", "焦虑", "抑郁", "烦", "累", "苦", "难受", "想家",
               "情绪", "陪伴", "倾诉", "不开心"],
    "skill": ["培训", "考证", "技能", "电工证", "焊工", "架子工", "塔吊", "学徒", "提升",
              "证书", "资格证", "学技术", "复审", "到期", "换证", "继续教育"],
    "safety": ["安全", "隐患", "安全帽", "安全带", "脚手架", "高空", "坠落", "触电", "漏电",
              "危险", "防护", "事故", "违章", "举报安全", "工地安全", "安全检查", "安全提醒"],
    "salary": ["记工时", "算工资", "工资核算", "工时记录", "加班费", "日薪", "发薪", "薪资",
              "记工", "考勤", "出勤", "工资条", "开支", "花销", "花钱", "生活费", "记账本", "收支"],
    "legal": ["欠薪", "拖欠", "工资不给", "工伤", "合同", "辞退", "开除", "维权", "仲裁", "劳动法",
              "欠条", "赔偿", "解雇", "裁员", "用工", "劳动", "法律", "官司", "诉讼",
              "审查合同", "审合同", "看合同", "分析合同", "合同有问题", "违法条款",
              "投诉书", "仲裁申请", "法律文书", "律师", "起诉"],
    "life": ["社保", "医保", "公积金", "住房", "子女", "上学", "教育", "落户", "居住证",
             "新农合", "养老保险", "医疗保险"],
}


# 暴力/违法风险关键词：最高优先级识别，命中后必须路由到法律顾问做守法劝诫
_RISK_KEYWORDS = ["打了", "打人", "打架", "揍", "捅", "砍", "报复", "弄死", "弄残",
                  "教训", "绑架", "砸", "毁他", "收拾他", "喊人打", "叫人打", "砍他"]


def _keyword_route(text: str) -> str | None:
    """基于关键词的快速路由，按优先级匹配，命中则直接返回，未命中返回None走LLM路由"""
    text_lower = text.lower()
    # 最高优先级：暴力/违法风险，路由到法律顾问做守法劝诫与风险提示
    for kw in _RISK_KEYWORDS:
        if kw in text_lower:
            logger.info("[ROUTE_MONITOR] method=risk_keyword route=legal")
            return "legal"
    for route in _KEYWORD_ROUTE_PRIORITY:
        keywords = _KEYWORD_ROUTE_MAP[route]
        for kw in keywords:
            if kw in text_lower:
                return route
    return None


def _parse_route(content: str) -> str:
    """从LLM输出中健壮地提取路由值"""
    text = str(content).strip().lower()
    valid_routes = ["legal", "safety", "support", "salary", "skill", "life", "community", "chat"]

    # 1. 精确匹配
    if text in valid_routes:
        return text

    # 2. 正则提取：从文本中查找第一个匹配的有效路由词
    for route in valid_routes:
        if re.search(rf'\b{route}\b', text):
            return route

    # 3. 兜底：默认路由到法律顾问
    logger.warning(f"Router无法识别意图: '{content[:100]}', 默认路由到legal")
    return "legal"


def _extract_think_flag(user_text: str):
    """检测并剥离"深度思考"前缀，返回 (是否开启思考模式, 剥离前缀后的文本)"""
    if not user_text:
        return False, user_text
    stripped = user_text.strip()
    prefixes = [THINK_PREFIX] + THINK_PREFIX_ALIASES
    for prefix in prefixes:
        if stripped.startswith(prefix):
            remainder = stripped[len(prefix):].strip()
            # 剥离前缀后若为空则视为未开启，避免吞掉用户内容
            if not remainder:
                return False, user_text
            return True, remainder
    return False, user_text


def router_node(state: AgentState, ctx=None) -> dict:
    """路由节点：分析用户意图，决定路由到哪个Agent。
    优先使用关键词快速路由，未命中时再调用LLM。"""
    messages = state["messages"]

    # 获取最后一条用户消息
    last_message = messages[-1] if messages else None
    if not last_message:
        return {"next_agent": "legal", "think_mode": False}

    # 提取用户消息文本
    user_text = ""
    if isinstance(last_message, HumanMessage):
        content = last_message.content
        if isinstance(content, str):
            user_text = content
        elif isinstance(content, list):
            user_text = " ".join(
                item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"
            )

    # 检测"深度思考"模式前缀：开启后在专业节点输出上追加一轮 LLM 优化
    think_mode, user_text = _extract_think_flag(user_text)
    if think_mode:
        logger.info("[ROUTE_MONITOR] think_mode=on 已剥离深度思考前缀")

    # 敏感信息脱敏（记录日志前）
    masked_text = mask_sensitive_info(user_text)
    if masked_text != user_text:
        logger.info("用户消息包含敏感信息，已脱敏处理")

    # 个人信息解析请求：优先于常规路由，直接进入解析节点返回结构化 JSON
    if user_text.startswith(PROFILE_PARSE_PREFIX):
        logger.info("[ROUTE_MONITOR] method=profile_parse_prefix route=profile_parse")
        return {"next_agent": "profile_parse", "think_mode": False}

    # 快速路径：关键词匹配（避免LLM调用，降低延迟）
    keyword_result = _keyword_route(user_text)
    if keyword_result:
        logger.info(f"[ROUTE_MONITOR] method=keyword text='{user_text[:50]}' route={keyword_result}")
        return {"next_agent": keyword_result, "think_mode": think_mode}

    # 慢路径：LLM意图分析（使用剥离前缀后的文本，避免标记干扰意图判断）
    llm = get_llm(ctx)

    # 提取较近的历史用户提问，帮助识别"那我该怎么办"这类指代词
    history_texts = []
    for m in messages[:-1]:
        if isinstance(m, HumanMessage):
            t = m.content
            if isinstance(t, list):
                t = " ".join(
                    item.get("text", "") for item in t
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            t = (t or "").strip()
            if t:
                history_texts.append(t)

    if history_texts:
        recent = history_texts[-3:]
        context = "【历史提问】\n" + "\n".join(f"- {t[:80]}" for t in recent) + "\n\n【当前提问】" + user_text
    else:
        context = "【当前提问】" + user_text

    router_messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=context)
    ]

    response = llm.invoke(router_messages)
    content = response.content
    if isinstance(content, list):
        content = " ".join(str(item) for item in content)

    route = _parse_route(content)
    logger.info(f"[ROUTE_MONITOR] method=llm text='{user_text[:50]}' route={route} raw='{content[:30]}'")
    return {"next_agent": route, "think_mode": think_mode}


# ============== 专业Agent节点 ==============

# 缓存专业Agent实例，避免每次请求都重新创建
_specialist_cache = {}

def create_specialist_agent(system_prompt: str, tools: list, ctx=None):
    """创建专业Agent（带缓存和记忆持久化）"""
    # 使用 prompt 内容哈希作为缓存 key，避免 Python 字符串 intern 导致 id 重复
    cache_key = hash(system_prompt)
    if cache_key in _specialist_cache:
        return _specialist_cache[cache_key]
    
    llm = get_llm(ctx)
    agent = create_agent(
        model=llm,
        system_prompt=system_prompt + COMMON_REPLY_RULES,
        tools=tools,
        middleware=[handle_tool_errors],
        checkpointer=get_memory_saver(),
    )
    _specialist_cache[cache_key] = agent
    return agent


def legal_node(state: AgentState, ctx=None) -> dict:
    """法律顾问节点"""
    tools = [search_law_knowledge, search_hotlines, 
             generate_arbitration_application, generate_wage_complaint, generate_iou]
    agent = create_specialist_agent(LEGAL_PROMPT, tools, ctx)
    recent = _get_recent_messages(state["messages"])
    result = agent.invoke({"messages": recent})
    return {"messages": result["messages"]}


def safety_node(state: AgentState, ctx=None) -> dict:
    """安全卫士节点"""
    safety_tools = [search_law_knowledge, get_weather_safety_advisory]
    agent = create_specialist_agent(SAFETY_PROMPT, safety_tools, ctx)
    recent = _get_recent_messages(state["messages"])
    result = agent.invoke({"messages": recent})
    return {"messages": result["messages"]}


def support_node(state: AgentState, ctx=None) -> dict:
    """心理伙伴节点"""
    agent = create_specialist_agent(SUPPORT_PROMPT, [search_law_knowledge], ctx)
    recent = _get_recent_messages(state["messages"])
    result = agent.invoke({"messages": recent})
    return {"messages": result["messages"]}


def salary_node(state: AgentState, ctx=None) -> dict:
    """薪资管家节点"""
    salary_tools = [search_law_knowledge, record_work, calculate_salary, 
                    check_overdue_reminders, create_salary_reminder, mark_reminder_paid, get_my_reminders,
                    generate_wage_slip, record_expense, get_expense_summary, get_expense_list,
                    set_my_name, who_am_i]
    agent = create_specialist_agent(SALARY_PROMPT, salary_tools, ctx)
    recent = _get_recent_messages(state["messages"])
    result = agent.invoke({"messages": recent})
    return {"messages": result["messages"]}


def skill_node(state: AgentState, ctx=None) -> dict:
    """技能导师节点"""
    tools = [search_law_knowledge, record_cert, check_cert_expiry, get_cert_renewal_guide]
    agent = create_specialist_agent(SKILL_PROMPT, tools, ctx)
    recent = _get_recent_messages(state["messages"])
    result = agent.invoke({"messages": recent})
    return {"messages": result["messages"]}


def life_node(state: AgentState, ctx=None) -> dict:
    """生活管家节点"""
    agent = create_specialist_agent(LIFE_PROMPT, [search_law_knowledge], ctx)
    recent = _get_recent_messages(state["messages"])
    result = agent.invoke({"messages": recent})
    return {"messages": result["messages"]}


def community_node(state: AgentState, ctx=None) -> dict:
    """工友社区节点"""
    agent = create_specialist_agent(
        COMMUNITY_PROMPT,
        [search_law_knowledge, post_question, get_questions, get_question_detail, add_comment],
        ctx
    )
    recent = _get_recent_messages(state["messages"])
    result = agent.invoke({"messages": recent})
    return {"messages": result["messages"]}


def chat_node(state: AgentState, ctx=None) -> dict:
    """通用兜底节点：LLM 路由判断各专业节点均不合适时，由带知识库检索能力的 Agent 自行处理"""
    # 加载系统提示词
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    
    messages = state["messages"]
    # 兜底节点同样挂载知识库检索工具：确保"自行处理"时能查法条、答得专业，而非凭空回答
    # create_specialist_agent 内部会追加 COMMON_REPLY_RULES（含安全边界/针对性/权益小结等规则）
    agent = create_specialist_agent(
        cfg.get("sp", ""),
        [search_law_knowledge, search_hotlines],
        ctx
    )
    result = agent.invoke({"messages": messages})
    return {"messages": result["messages"]}


PROFILE_PARSE_PROMPT = """# 角色：工友信息解析助手
你会收到一段建筑工友的自然语言自述，请从中提取结构化个人信息。

# 提取字段（只提取自述中明确提到或能直接推断的信息）
- name：姓名
- gender：性别（"男" 或 "女"，未提及留空）
- age：年龄（数字字符串，未提及留空）
- job：工种/职位（如钢筋工、木工、瓦工、电工、架子工、塔吊司机、装修工、普工等）
- location：所在地区/工作城市
- salary：薪资（保留原始表述，如"8000元/月""300元/天"）
- workYears：工作年限（数字字符串）
- phone：联系电话
- note：其他重要信息（技能特长、证书、家庭情况、诉求等）

# 输出要求（严格遵守）
- 只返回一个 JSON 对象，不要返回任何其他文字、解释或 markdown 代码块标记。
- 未提及或无法确定的字段，一律用空字符串 ""。
- 严禁编造自述中没有的信息。
- 输出示例：{"name":"张三","gender":"男","age":"35","job":"钢筋工","location":"成都","salary":"8000元/月","workYears":"10","phone":"","note":"有焊工证"}
"""


def profile_parse_node(state: AgentState, ctx=None) -> dict:
    """个人信息解析节点：从工友自然语言自述中提取结构化信息，返回纯 JSON。"""
    messages = state["messages"]
    last_message = messages[-1] if messages else None
    user_text = ""
    if isinstance(last_message, HumanMessage):
        content = last_message.content
        if isinstance(content, str):
            user_text = content
        elif isinstance(content, list):
            user_text = " ".join(
                item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"
            )
    # 剥离解析前缀，得到自述正文
    if user_text.startswith(PROFILE_PARSE_PREFIX):
        user_text = user_text[len(PROFILE_PARSE_PREFIX):].strip()

    llm = get_llm(ctx)
    try:
        response = llm.invoke([
            SystemMessage(content=PROFILE_PARSE_PROMPT),
            HumanMessage(content=user_text or "（未提供自述内容）"),
        ])
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"profile_parse 节点执行失败: {e}")
        return {"messages": [AIMessage(content='{"error":"信息解析失败，请换个说法再试，或改用表单填写"}')]}


# ============== 路由决策 ==============

def route_decision(state: AgentState) -> str:
    """根据路由结果决定下一个节点"""
    next_agent = state.get("next_agent", "legal")
    valid_routes = {"legal", "safety", "support", "salary", "skill", "life", "community", "chat", "profile_parse"}
    if next_agent in valid_routes:
        return next_agent
    return "legal"  # 未知路由值默认回到法律顾问


# ============== 输出优化（思考模式） ==============

POLISH_PROMPT = """你是「明白人」的回复优化助手。请对下面这段回复做一轮润色，让它更适合建筑工友阅读，但**严格保持法律内容的准确性**：

1. 语言更精炼、更口语化、更亲切，去掉啰嗦和重复；
2. 保留原有结构不丢失（例如权益小结、法律依据标注、风险提示、行动步骤等）；
3. 任何法律条款、金额、时间、程序步骤、联系方式等关键事实**一个字都不能改动**，只能润色措辞；
4. 原文如果已经很好，只做轻微文字优化，不要大改、不要补充原文没有的新内容；
5. 直接输出优化后的完整回复，不要加"以下是优化后的回复"之类的说明，也不要加引号或代码块。
"""


def polish_node(state: AgentState, ctx=None) -> dict:
    """思考模式：对专业节点的输出追加一轮 LLM 优化，再作为最终答复返回"""
    messages = state["messages"]

    # 取最后一条 AI 消息作为待优化内容
    ai_msg = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            ai_msg = msg
            break
    if ai_msg is None:
        return {"think_mode": False}

    raw_content = ai_msg.content
    if isinstance(raw_content, list):
        raw_content = " ".join(str(item) for item in raw_content)
    if not raw_content or not str(raw_content).strip():
        return {"think_mode": False}

    # 提取用户问题（剥离深度思考前缀），供优化时保持针对性
    user_msg = _get_last_user_message(messages)
    user_text = ""
    if user_msg is not None:
        user_text = user_msg.content if isinstance(user_msg.content, str) else str(user_msg.content)
    _, user_text = _extract_think_flag(user_text)

    llm = get_llm(ctx, temperature_override=0.3)
    optimize_messages = [SystemMessage(content=POLISH_PROMPT)]
    if user_text:
        optimize_messages.append(HumanMessage(content=user_text))
    optimize_messages.append(HumanMessage(content=f"请优化下面这段回复：\n\n{raw_content}"))

    try:
        response = llm.invoke(optimize_messages)
        optimized = response.content
        if isinstance(optimized, list):
            optimized = " ".join(str(item) for item in optimized)
        if optimized and str(optimized).strip():
            logger.info("[POLISH] 思考模式优化完成")
            return {"messages": [AIMessage(content=str(optimized))], "think_mode": False}
    except Exception as e:
        logger.warning(f"[POLISH] 优化失败，回退原始输出: {e}")

    # 优化失败或结果为空：保持原始输出不变
    return {"think_mode": False}


def should_polish(state: AgentState) -> str:
    """专业节点输出后：思考模式走优化节点，快速模式直接结束"""
    return "polish" if state.get("think_mode") else "end"


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
    workflow.add_node("profile_parse", lambda state: profile_parse_node(state, ctx))
    workflow.add_node("polish", lambda state: polish_node(state, ctx))

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
            "profile_parse": "profile_parse",
        }
    )

    # 专业节点输出后：思考模式先经 polish 优化再结束，快速模式直接结束
    agent_names = ["legal", "safety", "support", "salary", "skill", "life", "community", "chat"]
    for name in agent_names:
        workflow.add_conditional_edges(
            name,
            should_polish,
            {"polish": "polish", "end": END}
        )

    # 信息解析节点直接结束（返回纯 JSON，不走 polish 优化）
    workflow.add_edge("profile_parse", END)

    # 优化节点执行完结束
    workflow.add_edge("polish", END)

    # 返回包装对象（平台通过builder属性访问StateGraph并自行compile+注入checkpointer）
    return AgentBuilder(workflow)
