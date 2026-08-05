"""
用户身份管理工具 - 通过session关联工友身份
避免每次调用工具都需要手动传入worker_name
"""
from typing import Optional
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client


# 简单的内存缓存（生产环境应使用Redis）
_session_user_cache: dict = {}


def register_user(session_id: str, worker_name: str, phone: Optional[str] = None) -> str:
    """注册或更新用户身份信息（内部函数，非tool）"""
    _session_user_cache[session_id] = {
        "worker_name": worker_name,
        "phone": phone
    }
    return f"已记住你的信息：{worker_name}"


def get_user_name(session_id: str) -> Optional[str]:
    """获取当前会话的用户姓名（内部函数）"""
    user_info = _session_user_cache.get(session_id)
    if user_info:
        return user_info.get("worker_name")
    return None


@tool
def set_my_name(worker_name: str, phone: str = "") -> str:
    """
    设置我的姓名和联系方式，后续操作会自动使用这个身份。
    
    Args:
        worker_name: 我的姓名
        phone: 联系电话（可选）
    """
    ctx = request_context.get() or new_context(method="set_my_name")
    # 从上下文中获取session_id（简化处理，使用默认值）
    session_id = "default"
    
    register_user(session_id, worker_name, phone if phone else None)
    
    # 同时保存到数据库（可选）
    try:
        client = get_supabase_client(ctx)
        client.table('user_profiles').upsert({
            'session_id': session_id,
            'worker_name': worker_name,
            'phone': phone if phone else None
        }, on_conflict='session_id').execute()
    except Exception:
        # 表不存在时忽略，仅使用内存缓存
        pass
    
    return f"好的，我记住你了！你是{worker_name}。后续记工时、查工资等操作都会自动用你的名字。"


@tool
def who_am_i() -> str:
    """
    查看当前已识别的身份信息。
    """
    ctx = request_context.get() or new_context(method="who_am_i")
    session_id = "default"
    
    name = get_user_name(session_id)
    if name:
        return f"当前身份：{name}"
    else:
        return "还没有记录你的身份信息。请告诉我你的名字，我会记住的。"
