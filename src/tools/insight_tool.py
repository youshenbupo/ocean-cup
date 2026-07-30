"""数据分析工具 - 生成行业洞察报告"""
import json
from datetime import datetime, timedelta
from typing import Optional
from langchain.tools import tool
from sqlalchemy import select, func, desc
from storage.database.supabase_client import get_supabase_client
from storage.database.shared.model import (
    WorkRecord, CommunityPost, CommunityComment
)
from coze_coding_utils.log.write_log import request_context


@tool
def generate_insight_report(
    report_type: str = "all",
    days: int = 30
) -> str:
    """生成行业洞察报告

    Args:
        report_type: 报告类型 (salary/safety/community/all)
        days: 统计天数

    Returns:
        洞察报告内容
    """
    try:
        client = get_supabase_client()
        with client.get_session() as session:
            start_date = datetime.now() - timedelta(days=days)
            report_parts = []

            # 薪资相关统计
            if report_type in ["salary", "all"]:
                salary_stats = session.query(
                    func.count(WorkRecord.id).label("total_records"),
                    func.avg(WorkRecord.daily_wage).label("avg_wage"),
                    func.max(WorkRecord.daily_wage).label("max_wage"),
                    func.min(WorkRecord.daily_wage).label("min_wage"),
                    func.count(func.distinct(WorkRecord.worker_name)).label("unique_workers")
                ).filter(WorkRecord.created_at >= start_date).first()

                if salary_stats and salary_stats.total_records > 0:
                    report_parts.append(f"""
## 💰 薪资洞察报告（近{days}天）

| 指标 | 数值 |
|------|------|
| 工时记录总数 | {salary_stats.total_records} 条 |
| 参与统计工友数 | {salary_stats.unique_workers} 人 |
| 平均日薪 | ¥{salary_stats.avg_wage:.0f} |
| 最高日薪 | ¥{salary_stats.max_wage:.0f} |
| 最低日薪 | ¥{salary_stats.min_wage:.0f} |

**分析**：
- 工友日薪分布范围较大，反映不同工种和技能水平的差异
- 建议关注低薪工友，提供技能提升培训
""")

            # 社区活跃度统计
            if report_type in ["community", "all"]:
                post_stats = session.query(
                    func.count(CommunityPost.id).label("total_posts"),
                    func.count(func.distinct(CommunityPost.author_name)).label("unique_authors"),
                    func.avg(CommunityPost.view_count).label("avg_views"),
                    func.avg(CommunityPost.like_count).label("avg_likes")
                ).filter(CommunityPost.created_at >= start_date).first()

                comment_stats = session.query(
                    func.count(CommunityComment.id).label("total_comments"),
                    func.count(func.distinct(CommunityComment.author_name)).label("unique_commenters")
                ).filter(CommunityComment.created_at >= start_date).first()

                # 热门帖子
                hot_posts = session.query(
                    CommunityPost.title,
                    CommunityPost.author_name,
                    CommunityPost.view_count,
                    CommunityPost.like_count
                ).filter(
                    CommunityPost.created_at >= start_date
                ).order_by(desc(CommunityPost.view_count)).limit(5).all()

                if post_stats and post_stats.total_posts > 0:
                    report_parts.append(f"""
## 🏘️ 社区活跃度报告（近{days}天）

| 指标 | 数值 |
|------|------|
| 发帖总数 | {post_stats.total_posts} 条 |
| 发帖人数 | {post_stats.unique_authors} 人 |
| 评论总数 | {comment_stats.total_comments if comment_stats else 0} 条 |
| 评论人数 | {comment_stats.unique_commenters if comment_stats else 0} 人 |
| 平均浏览 | {post_stats.avg_views:.0f} 次/帖 |
| 平均点赞 | {post_stats.avg_likes:.0f} 次/帖 |

### 🔥 热门帖子 TOP5
""")
                    for i, post in enumerate(hot_posts, 1):
                        report_parts.append(f"{i}. **{post.title}** - {post.author_name}（浏览{post.view_count}，点赞{post.like_count}）")

                    report_parts.append(f"""
**分析**：
- 社区活跃度反映工友关注热点
- 高浏览量帖子通常是维权、薪资相关话题
- 建议加强热门话题的知识库建设
""")

            # 生成总结
            if report_parts:
                report = f"""
# 📊 工友权益明白人 - 行业洞察报告

**报告周期**：近{days}天
**生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M")}

{''.join(report_parts)}

---

## 💡 建议

1. **知识库优化**：根据工友提问热点，补充相关知识库内容
2. **服务改进**：关注工友反馈，优化Agent回复质量
3. **功能扩展**：根据社区讨论热点，开发新功能
4. **政策跟踪**：及时更新法律法规变化，确保信息准确

---
*报告由「工友权益明白人」自动生成*
"""
                return report
            else:
                return "暂无数据可分析，请确保有工时记录或社区帖子数据。"

    except Exception as e:
        return f"生成报告失败：{str(e)}"
