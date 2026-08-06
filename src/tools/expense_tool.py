"""记账本工具

帮助工友记录日常开支，统计收支情况。
"""
import os
from datetime import datetime, date, timedelta
from typing import Optional
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client


EXPENSE_CATEGORIES = [
    "餐饮", "交通", "住宿", "日用品", "通讯", "医疗", "娱乐", "其他"
]

# 分类别名映射：LLM 可能传入的各种说法 → 标准分类
_CATEGORY_ALIASES = {
    "吃饭": "餐饮", "早饭": "餐饮", "午饭": "餐饮", "晚饭": "餐饮",
    "外卖": "餐饮", "零食": "餐饮", "水果": "餐饮", "喝水": "餐饮",
    "打车": "交通", "地铁": "交通", "公交": "交通", "高铁": "交通",
    "火车": "交通", "飞机": "交通", "油费": "交通", "加油": "交通",
    "房租": "住宿", "租房": "住宿", "酒店": "住宿", "宾馆": "住宿",
    "洗衣": "日用品", "牙膏": "日用品", "毛巾": "日用品", "纸巾": "日用品",
    "话费": "通讯", "充值": "通讯", "流量": "通讯", "手机": "通讯",
    "看病": "医疗", "买药": "医疗", "体检": "医疗", "挂号": "医疗",
    "游戏": "娱乐", "电影": "娱乐", "唱歌": "娱乐", "烟": "娱乐", "酒": "娱乐",
}


def _normalize_category(category: str) -> str:
    """将 LLM 传入的分类名映射为标准分类。"""
    if category in EXPENSE_CATEGORIES:
        return category
    return _CATEGORY_ALIASES.get(category, "其他")


def _safe_get(item, key, default="") -> str:
    """安全获取字典值，兼容 LSP 类型检查。"""
    if isinstance(item, dict):
        val = item.get(key, default)
        return str(val) if val is not None else default
    return default


@tool
def record_expense(
    worker_name: str,
    amount: float,
    category: str,
    description: str = "",
    expense_date: str = "",
) -> str:
    """记录一笔开支。

    Args:
        worker_name: 工人姓名
        amount: 金额（元）
        category: 分类（餐饮/交通/住宿/日用品/通讯/医疗/娱乐/其他）
        description: 备注说明
        expense_date: 日期（YYYY-MM-DD格式，默认为今天）
    """
    ctx = request_context.get() or new_context(method="record_expense")
    client = get_supabase_client(ctx)
    
    normalized = _normalize_category(category)
    if normalized == "其他" and category not in EXPENSE_CATEGORIES and category not in _CATEGORY_ALIASES:
        pass  # 允许自定义分类归入"其他"
    category = normalized
    
    data = {
        "worker_name": worker_name,
        "amount": amount,
        "category": category,
        "description": description,
    }
    
    if expense_date:
        data["expense_date"] = expense_date
    
    client.table("expense_records").insert(data).execute()
    
    return f"""✅ 开支记录成功！

💰 开支明细：
  • 金额：¥{amount:.2f}
  • 分类：{category}
  • 备注：{description or '无'}
  • 日期：{expense_date or date.today().isoformat()}

💡 输入"查账"可以查看本月收支汇总
"""


@tool
def get_expense_summary(
    worker_name: str,
    month: str = "",
) -> str:
    """查询收支汇总。

    Args:
        worker_name: 工人姓名
        month: 查询月份（YYYY-MM格式，默认为本月）
    """
    ctx = request_context.get() or new_context(method="get_expense_summary")
    client = get_supabase_client(ctx)
    
    if not month:
        month = date.today().strftime("%Y-%m")
    
    start_date = f"{month}-01"
    year, m = int(month[:4]), int(month[5:7])
    if m == 12:
        end_date = f"{year}-12-31"
    else:
        end_date = f"{year}-{m+1:02d}-01"
    
    expenses = client.table("expense_records").select("*").eq(
        "worker_name", worker_name
    ).gte("expense_date", start_date).lt(
        "expense_date", end_date
    ).order("expense_date").execute()
    
    expense_list = expenses.data if expenses.data else []
    
    if not expense_list:
        return f"📊 {month} 暂无开支记录。"
    
    category_totals = {}
    total = 0
    for exp in expense_list:
        cat = _safe_get(exp, "category", "其他")
        amt = float(_safe_get(exp, "amount", 0))
        category_totals[cat] = category_totals.get(cat, 0) + amt
        total += amt
    
    lines = [f"📊 {month} 收支汇总\n"]
    lines.append(f"💸 总支出：¥{total:.2f}\n")
    
    lines.append("📋 分类明细：")
    for cat, amt in sorted(category_totals.items(), key=lambda x: -x[1]):
        pct = (amt / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5)
        lines.append(f"  {cat:6s} ¥{amt:>8.2f}  {pct:5.1f}% {bar}")
    
    lines.append(f"\n📝 共 {len(expense_list)} 笔记录")
    
    days_in_month = 30
    daily_avg = total / days_in_month
    lines.append(f"📅 日均开支：¥{daily_avg:.2f}")
    
    return "\n".join(lines)


@tool
def get_expense_list(
    worker_name: str,
    days: int = 7,
) -> str:
    """查询最近开支明细。

    Args:
        worker_name: 工人姓名
        days: 查询最近多少天的记录（默认7天）
    """
    ctx = request_context.get() or new_context(method="get_expense_list")
    client = get_supabase_client(ctx)
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    expenses = client.table("expense_records").select("*").eq(
        "worker_name", worker_name
    ).gte("expense_date", start_date).order("expense_date", desc=True).execute()
    
    expense_list = expenses.data if expenses.data else []
    
    if not expense_list:
        return f"📝 最近{days}天暂无开支记录。"
    
    lines = [f"📝 最近{days}天开支明细：\n"]
    
    total = 0
    icons = {"餐饮": "🍜", "交通": "🚌", "住宿": "🏠", "日用品": "🛒", 
             "通讯": "📱", "医疗": "💊", "娱乐": "🎮", "其他": "📦"}
    
    for exp in expense_list:
        exp_date = _safe_get(exp, "expense_date", "")[:10]
        cat = _safe_get(exp, "category", "")
        amt = float(_safe_get(exp, "amount", 0))
        desc = _safe_get(exp, "description", "")
        total += amt
        
        icon = icons.get(cat, "💰")
        line = f"  {icon} {exp_date}  {cat:4s}  ¥{amt:>7.2f}"
        if desc:
            line += f"  ({desc})"
        lines.append(line)
    
    lines.append(f"\n💸 合计：¥{total:.2f}")
    
    return "\n".join(lines)
