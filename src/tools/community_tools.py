"""工友社区工具 - 发帖、查看帖子、评论"""
import logging
from datetime import datetime, timezone
from typing import Optional

from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


@tool
def post_question(author_name: str, title: str, content: str, category: str = "general") -> str:
    """
    在工友社区发布帖子/提问。
    
    Args:
        author_name: 发帖人姓名
        title: 帖子标题
        content: 帖子内容
        category: 分类，可选值：salary(薪资)、safety(安全)、skill(技能)、life(生活)、general(综合)
    
    Returns:
        发布结果信息
    """
    ctx = request_context.get() or new_context(method="post_question")
    try:
        client = get_supabase_client(ctx)
        
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "author_name": author_name,
            "title": title,
            "content": content,
            "category": category,
            "created_at": now,
            "updated_at": now
        }
        
        result = client.table("community_posts").insert(data).execute()
        
        if result.data:
            return f"✅ 帖子发布成功！\n标题：{title}\n分类：{category}\n\n你的帖子已经发到工友社区了，其他工友可以看到并回复你。"
        else:
            return "❌ 帖子发布失败，请稍后重试。"
    except Exception as e:
        logger.error(f"发布帖子失败: {e}")
        return f"❌ 发布帖子时出错：{str(e)}"


@tool
def get_questions(category: Optional[str] = None, limit: int = 10) -> str:
    """
    查看工友社区的帖子列表。
    
    Args:
        category: 分类筛选，可选值：salary(薪资)、safety(安全)、skill(技能)、life(生活)、general(综合)，不填则查看全部
        limit: 返回数量，默认10条
    
    Returns:
        帖子列表
    """
    ctx = request_context.get() or new_context(method="get_questions")
    try:
        client = get_supabase_client(ctx)
        
        query = client.table("community_posts").select("*").order("created_at", desc=True).limit(limit)
        
        if category:
            query = query.eq("category", category)
        
        result = query.execute()
        
        if not result.data:
            return "📭 暂无帖子，你来发第一个吧！"
        
        category_names = {
            "salary": "💰薪资",
            "safety": "🦺安全",
            "skill": "📚技能",
            "life": "🏠生活",
            "general": "💬综合"
        }
        
        lines = ["📋 工友社区最新帖子：\n"]
        for i, post in enumerate(result.data, 1):
            post_dict = dict(post) if not isinstance(post, dict) else post
            cat = category_names.get(post_dict.get("category", "general"), "💬综合")
            title = post_dict.get("title", "无标题")
            author = post_dict.get("author_name", "匿名")
            post_id = post_dict.get("id", "")
            lines.append(f"{i}. {cat} | {title}")
            lines.append(f"   发帖人：{author} | ID: {post_id}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"获取帖子列表失败: {e}")
        return f"❌ 获取帖子列表时出错：{str(e)}"


@tool
def get_question_detail(post_id: int) -> str:
    """
    查看帖子的详细内容和评论。
    
    Args:
        post_id: 帖子ID
    
    Returns:
        帖子详情和评论
    """
    ctx = request_context.get() or new_context(method="get_question_detail")
    try:
        client = get_supabase_client(ctx)
        
        # 获取帖子详情
        post_result = client.table("community_posts").select("*").eq("id", post_id).execute()
        
        if not post_result.data:
            return f"❌ 找不到ID为{post_id}的帖子。"
        
        post = post_result.data[0]
        
        # 获取评论
        comments_result = client.table("community_comments").select("*").eq("post_id", post_id).order("created_at", desc=True).execute()
        comments = comments_result.data if comments_result.data else []
        
        category_names = {
            "salary": "💰薪资",
            "safety": "🦺安全",
            "skill": "📚技能",
            "life": "🏠生活",
            "general": "💬综合"
        }
        
        post_dict = dict(post) if not isinstance(post, dict) else post
        cat = category_names.get(post_dict.get("category", "general"), "💬综合")
        
        lines = [
            f"📝 帖子详情 (ID: {post_id})",
            f"分类：{cat}",
            f"标题：{post_dict.get('title', '无标题')}",
            f"发帖人：{post_dict.get('author_name', '匿名')}",
            f"内容：{post_dict.get('content', '无内容')}",
            "",
            f"💬 评论 ({len(comments)}条)："
        ]
        
        if comments:
            for i, comment in enumerate(comments, 1):
                comment_dict = dict(comment) if not isinstance(comment, dict) else comment
                commenter = comment_dict.get("commenter_name", "匿名")
                content = comment_dict.get("content", "")
                lines.append(f"  {i}. {commenter}：{content}")
        else:
            lines.append("  暂无评论，快来抢沙发！")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"获取帖子详情失败: {e}")
        return f"❌ 获取帖子详情时出错：{str(e)}"


@tool
def add_comment(post_id: int, commenter_name: str, content: str) -> str:
    """
    在帖子下添加评论。
    
    Args:
        post_id: 帖子ID
        commenter_name: 评论人姓名
        content: 评论内容
    
    Returns:
        评论结果
    """
    ctx = request_context.get() or new_context(method="add_comment")
    try:
        client = get_supabase_client(ctx)
        
        # 检查帖子是否存在
        post_result = client.table("community_posts").select("id").eq("id", post_id).execute()
        if not post_result.data:
            return f"❌ 找不到ID为{post_id}的帖子。"
        
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "post_id": post_id,
            "commenter_name": commenter_name,
            "content": content,
            "created_at": now
        }
        
        result = client.table("community_comments").insert(data).execute()
        
        if result.data:
            return f"✅ 评论成功！\n帖子ID：{post_id}\n你的评论：{content}\n\n感谢你的分享，其他工友会看到你的回复。"
        else:
            return "❌ 评论失败，请稍后重试。"
    except Exception as e:
        logger.error(f"添加评论失败: {e}")
        return f"❌ 添加评论时出错：{str(e)}"
