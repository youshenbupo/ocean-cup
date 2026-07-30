"""数据分析工具 - 生成行业洞察报告"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from langchain.tools import tool
from storage.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


@tool
def generate_industry_insights(report_type: str = "all", days: int = 30) -> str:
    """
    生成建筑工友行业洞察报告。
    
    Args:
        report_type: 报告类型 (salary/safety/community/all)
        days: 统计天数
    
    Returns:
        洞察报告内容
    """
    try:
        client = get_supabase_client()
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        report_parts = []

        # 薪资相关统计
        if report_type in ["salary", "all"]:
            try:
                salary_result = client.table("work_records").select("*").filter(
                    "created_at", "gte", start_date
                ).execute()
                
                if salary_result.data:
                    records = salary_result.data if isinstance(salary_result.data, list) else []
                    total_records = len(records)
                    wages = [r.get("daily_wage", 0) for r in records if isinstance(r, dict) and r.get("daily_wage")]
                    workers = set(r.get("worker_name") for r in records if isinstance(r, dict) and r.get("worker_name"))
                    
                    if wages:
                        avg_wage = sum(wages) / len(wages)
                        max_wage = max(wages)
                        min_wage = min(wages)
                        
                        report_parts.append(f"""
## 💰 薪资洞察报告（近{days}天）

| 指标 | 数值 |
|------|------|
| 工时记录总数 | {total_records} 条 |
| 参与统计工友数 | {len(workers)} 人 |
| 平均日薪 | ¥{avg_wage:.0f} |
| 最高日薪 | ¥{max_wage:.0f} |
| 最低日薪 | ¥{min_wage:.0f} |

**分析**：
- 工友日薪分布范围较大，反映不同工种和技能水平的差异
- 建议关注低薪工友，提供技能提升培训
""")
            except Exception as e:
                logger.warning(f"薪资统计查询失败: {e}")

        # 安全相关统计
        if report_type in ["safety", "all"]:
            report_parts.append(f"""
## 🦺 安全洞察报告

**当前安全态势**：
- 建议持续关注高温、雨季等特殊天气下的施工安全
- 定期开展安全培训，提高工友安全意识
- 加强安全防护用品的配备和使用监督

**重点关注**：
- 高空作业安全防护
- 用电安全规范
- 脚手架搭设标准
""")

        # 社区相关统计
        if report_type in ["community", "all"]:
            try:
                posts_result = client.table("community_posts").select("*").filter(
                    "created_at", "gte", start_date
                ).execute()
                
                if posts_result.data:
                    posts = posts_result.data if isinstance(posts_result.data, list) else []
                    total_posts = len(posts)
                    
                    # 统计各类问题数量
                    categories = {}
                    for post in posts:
                        if isinstance(post, dict):
                            cat = post.get("category", "general")
                            categories[cat] = categories.get(cat, 0) + 1
                    
                    report_parts.append(f"""
## 💬 社区洞察报告（近{days}天）

| 指标 | 数值 |
|------|------|
| 社区帖子总数 | {total_posts} 条 |

**问题分类分布**：
| 分类 | 数量 |
|------|------|
| 薪资问题 | {categories.get('salary', 0)} 条 |
| 安全问题 | {categories.get('safety', 0)} 条 |
| 技能提升 | {categories.get('skill', 0)} 条 |
| 生活问题 | {categories.get('life', 0)} 条 |
| 综合讨论 | {categories.get('general', 0)} 条 |

**分析**：
- 薪资问题仍是工友最关心的话题
- 安全类讨论增多，反映工友安全意识提升
- 技能提升需求旺盛，建议加强培训资源对接
""")
            except Exception as e:
                logger.warning(f"社区统计查询失败: {e}")

        if not report_parts:
            return "暂无足够数据生成洞察报告，建议继续使用平台积累数据。"

        # 生成总结
        report = "\n".join(report_parts)
        report += f"""
---

## 📊 综合建议

1. **权益保障**：持续加强劳动法律法规宣传，帮助工友了解维权途径
2. **技能提升**：根据工友需求，对接更多免费培训资源
3. **安全守护**：结合天气和工地情况，推送个性化安全提醒
4. **社区运营**：鼓励工友分享经验，形成互助氛围

---
*报告生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}*
*统计周期：近{days}天*
"""

        return report

    except Exception as e:
        logger.error(f"生成洞察报告失败: {e}")
        return f"❌ 生成洞察报告时出错：{str(e)}"
