"""
多模态深化：工地安全隐患自动识别工具
支持图片分析，识别常见安全隐患
"""
import os
import json
from typing import Optional
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context, default_headers


# 安全隐患识别提示词
SAFETY_DETECTION_PROMPT = """你是一位专业的建筑工地安全 inspector（安全检查员）。请仔细分析这张工地照片，识别其中的安全隐患。

请按以下格式输出：

## 🔍 安全隐患检查报告

### 📸 场景识别
{描述你看到的工地场景}

### ⚠️ 发现的安全隐患
{列出发现的所有安全隐患，每个隐患包含：}
1. **隐患描述**：{具体描述}
   - **风险等级**：{重大/较大/一般}
   - **可能后果**：{可能导致的事故}
   - **整改建议**：{具体的整改措施}

### 📋 整改优先级
{按风险等级排序的整改建议}

### ⚖️ 法律依据
{相关的安全生产法规条款}

### 📞 举报渠道
- 12350：安全生产举报投诉热线
- 当地住建部门安全监管科

### 💡 安全提醒
{针对该场景的安全注意事项}

注意：
1. 如果没有发现明显隐患，也要说明场景安全状况
2. 重点关注：高空作业防护、用电安全、机械设备、个人防护用品
3. 给出的建议要具体可执行
"""


def _analyze_safety_image(image_url: str, ctx=None) -> str:
    """
    分析工地图片中的安全隐患
    使用多模态模型进行图片分析
    """
    # 获取模型配置
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, "config/agent_llm_config.json")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")
    
    # 使用多模态模型
    llm = ChatOpenAI(
        model="doubao-seed-2-0-pro-260215",  # 支持图片输入
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,  # 降低温度，提高准确性
        streaming=False,
        timeout=120,
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )
    
    # 构建多模态消息
    message = HumanMessage(
        content=[
            {"type": "text", "text": SAFETY_DETECTION_PROMPT},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    )
    
    response = llm.invoke([message])
    return response.content


@tool
def analyze_safety_image(image_url: str) -> str:
    """
    分析工地图片中的安全隐患。
    
    参数：
    - image_url: 图片URL地址
    
    返回：
    - 安全隐患检查报告，包含隐患描述、风险等级、整改建议等
    """
    ctx = request_context.get() or new_context(method="analyze_safety_image")
    
    try:
        result = _analyze_safety_image(image_url, ctx)
        return result
    except Exception as e:
        return f"图片分析失败：{str(e)}。请检查图片URL是否可访问。"


@tool
def batch_safety_analysis(image_urls: str) -> str:
    """
    批量分析多张工地图片的安全隐患。
    
    参数：
    - image_urls: 多个图片URL，用逗号分隔
    
    返回：
    - 每张图片的安全隐患分析报告
    """
    ctx = request_context.get() or new_context(method="batch_safety_analysis")
    
    urls = [url.strip() for url in image_urls.split(',') if url.strip()]
    
    results = []
    for i, url in enumerate(urls, 1):
        try:
            result = _analyze_safety_image(url, ctx)
            results.append(f"## 📷 图片 {i} 分析结果\n\n{result}\n")
        except Exception as e:
            results.append(f"## 📷 图片 {i} 分析失败\n\n错误：{str(e)}\n")
    
    return "\n---\n".join(results)


# 常见安全隐患类型（用于辅助识别）
COMMON_HAZARDS = {
    "高空作业": [
        "未系安全带",
        "未戴安全帽",
        "脚手架无防护栏",
        "安全网破损",
        "临边无防护"
    ],
    "用电安全": [
        "电线裸露",
        "配电箱无防护",
        "私拉乱接",
        "漏电保护器缺失",
        "电缆浸水"
    ],
    "机械设备": [
        "防护罩缺失",
        "操作规程缺失",
        "设备带病运转",
        "无证操作",
        "超负荷运行"
    ],
    "物料堆放": [
        "堆放过高",
        "倾斜不稳",
        "堵塞通道",
        "易燃易爆品混放",
        "无标识标牌"
    ],
    "个人防护": [
        "未戴安全帽",
        "未穿工作服",
        "未穿防护鞋",
        "未戴手套",
        "未戴护目镜"
    ]
}


@tool
def get_hazard_checklist(hazard_type: str = "全部") -> str:
    """
    获取特定类型的安全隐患检查清单。
    
    参数：
    - hazard_type: 隐患类型，可选值：高空作业、用电安全、机械设备、物料堆放、个人防护、全部
    
    返回：
    - 该类型的安全隐患检查清单
    """
    if hazard_type == "全部":
        output = "# 📋 建筑工地安全隐患检查清单\n\n"
        for category, hazards in COMMON_HAZARDS.items():
            output += f"## {category}\n"
            for hazard in hazards:
                output += f"- [ ] {hazard}\n"
            output += "\n"
        return output
    
    if hazard_type in COMMON_HAZARDS:
        output = f"# 📋 {hazard_type}安全隐患检查清单\n\n"
        for hazard in COMMON_HAZARDS[hazard_type]:
            output += f"- [ ] {hazard}\n"
        return output
    
    return f"未找到类型：{hazard_type}。可选类型：{', '.join(COMMON_HAZARDS.keys())}、全部"
