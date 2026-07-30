"""天气查询工具 - 用于获取天气信息并生成安全提醒"""

from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def get_weather_safety_advisory(location: str) -> str:
    """查询指定城市的天气情况并生成工地安全提醒。
    
    Args:
        location: 城市名称，如"北京"、"上海"、"广州"等
        
    Returns:
        天气情况和安全提醒信息
    """
    ctx = request_context.get() or new_context(method="get_weather_safety_advisory")
    client = SearchClient(ctx=ctx)
    
    # 搜索天气信息
    query = f"{location}今天天气预报 温度 风力 降雨"
    response = client.web_search(query=query, count=5)
    
    weather_info = ""
    if response.web_items:
        for item in response.web_items[:3]:
            weather_info += f"{item.snippet}\n"
    
    # 根据天气情况生成安全提醒
    advisory = _generate_safety_advisory(weather_info, location)
    
    return advisory


def _generate_safety_advisory(weather_info: str, location: str) -> str:
    """根据天气信息生成安全提醒"""
    
    advisory = f"🌤️ {location}今日工地安全提醒\n\n"
    advisory += "【天气概况】\n"
    
    # 分析天气关键词
    has_rain = any(kw in weather_info for kw in ["雨", "雷", "暴雨", "阵雨"])
    has_high_temp = any(kw in weather_info for kw in ["高温", "35", "36", "37", "38", "39", "40"])
    has_strong_wind = any(kw in weather_info for kw in ["大风", "7级", "8级", "9级", "10级", "台风"])
    has_cold = any(kw in weather_info for kw in ["降温", "低温", "0度", "零下", "冰冻", "雪"])
    
    if has_rain:
        advisory += "⚠️ 今日有降雨\n\n"
        advisory += "【雨天安全注意事项】\n"
        advisory += "1. 脚手架湿滑，高空作业必须系好安全带，穿防滑鞋\n"
        advisory += "2. 雷雨天气立即停止高空作业，远离金属架和树木\n"
        advisory += "3. 检查工地排水系统，防止基坑积水坍塌\n"
        advisory += "4. 电气设备做好防雨措施，防止漏电触电\n"
        advisory += "5. 雨后检查脚手架基础，确认稳固后再施工\n\n"
    elif has_high_temp:
        advisory += "⚠️ 今日高温预警\n\n"
        advisory += "【高温天气安全注意事项】\n"
        advisory += "1. 避开中午11点-下午3点高温时段作业\n"
        advisory += "2. 工地必须配备防暑降温药品（藿香正气水、十滴水等）\n"
        advisory += "3. 保证充足饮用水，建议喝淡盐水补充电解质\n"
        advisory += "4. 出现头晕、恶心、乏力等症状立即停工休息\n"
        advisory += "5. 发现有人中暑，立即转移到阴凉处，解开衣扣，喂水降温\n\n"
    elif has_strong_wind:
        advisory += "⚠️ 今日大风预警\n\n"
        advisory += "【大风天气安全注意事项】\n"
        advisory += "1. 6级以上大风停止塔吊作业和高空吊装\n"
        advisory += "2. 加固脚手架、模板、围挡等临时设施\n"
        advisory += "3. 停止外墙喷涂、屋面施工等高空作业\n"
        advisory += "4. 妥善堆放易被风吹落的材料，防止高空坠物\n"
        advisory += "5. 检查安全网是否牢固，防止被风吹开\n\n"
    elif has_cold:
        advisory += "⚠️ 今日低温/冰雪预警\n\n"
        advisory += "【低温天气安全注意事项】\n"
        advisory += "1. 清除脚手架、跳板上的冰雪，确认不滑后再作业\n"
        advisory += "2. 做好防滑措施，铺设草垫或撒沙\n"
        advisory += "3. 工人穿戴保暖防滑鞋，禁止穿硬底鞋作业\n"
        advisory += "4. 宿舍取暖注意通风，防止一氧化碳中毒\n"
        advisory += "5. 混凝土施工做好防冻措施\n\n"
    else:
        advisory += "✅ 今日天气良好\n\n"
        advisory += "【常规安全提醒】\n"
        advisory += "1. 进入工地必须戴好安全帽\n"
        advisory += "2. 高空作业（2米以上）必须系安全带\n"
        advisory += "3. 严禁酒后作业、疲劳作业\n"
        advisory += "4. 特种作业持证上岗，严禁违章操作\n"
        advisory += "5. 发现安全隐患立即报告，不要冒险作业\n\n"
    
    advisory += "📞 紧急求助电话：\n"
    advisory += "- 12350：安全生产举报投诉热线\n"
    advisory += "- 120：急救电话\n"
    advisory += "- 119：火警电话\n\n"
    
    advisory += "💡 记住：安全第一，平安回家！"
    
    return advisory
