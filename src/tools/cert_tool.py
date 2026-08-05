"""证书到期提醒工具

帮助工友管理职业技能证书，到期前自动提醒。
"""
import os
from datetime import datetime, date, timedelta
from typing import Optional
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client


CERT_TYPES = [
    "电工证", "焊工证", "高空作业证", "架子工证", "塔吊操作证",
    "挖掘机操作证", "装载机操作证", "起重机操作证", "安全员证",
    "施工员证", "质量员证", "材料员证", "其他"
]


def _safe_get(item, key, default="") -> str:
    """安全获取字典值，兼容 LSP 类型检查。"""
    if isinstance(item, dict):
        val = item.get(key, default)
        return str(val) if val is not None else default
    return default


@tool
def record_cert(
    worker_name: str,
    cert_type: str,
    expiry_date: str,
    cert_no: str = "",
    issue_date: str = "",
    notes: str = "",
) -> str:
    """记录职业技能证书信息。

    Args:
        worker_name: 工人姓名
        cert_type: 证书类型（电工证/焊工证/高空作业证等）
        expiry_date: 到期日期（YYYY-MM-DD格式）
        cert_no: 证书编号
        issue_date: 发证日期（YYYY-MM-DD格式）
        notes: 备注
    """
    ctx = request_context.get() or new_context(method="record_cert")
    client = get_supabase_client(ctx)
    
    data = {
        "worker_name": worker_name,
        "cert_type": cert_type,
        "expiry_date": expiry_date,
        "cert_no": cert_no,
        "issue_date": issue_date or None,
        "notes": notes,
        "status": "active",
    }
    
    client.table("cert_records").insert(data).execute()
    
    # 计算距离到期的天数
    try:
        exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        days_left = (exp - date.today()).days
        if days_left < 0:
            urgency = "⚠️ 已过期！请尽快复审"
        elif days_left <= 30:
            urgency = "🔴 即将到期，请尽快安排复审"
        elif days_left <= 90:
            urgency = "🟡 3个月内到期，建议提前准备"
        else:
            urgency = "🟢 有效期充足"
    except ValueError:
        urgency = ""
    
    return f"""✅ 证书记录成功！

📋 证书信息：
  • 姓名：{worker_name}
  • 证书类型：{cert_type}
  • 证书编号：{cert_no or '未填写'}
  • 到期日期：{expiry_date}
  • {urgency}

💡 输入"查证书"可以查看所有证书到期情况
"""


@tool
def check_cert_expiry(worker_name: str) -> str:
    """检查证书到期情况。

    Args:
        worker_name: 工人姓名
    """
    ctx = request_context.get() or new_context(method="check_cert_expiry")
    client = get_supabase_client(ctx)
    
    today = date.today().isoformat()
    warning_date = (date.today() + timedelta(days=90)).isoformat()
    
    # 获取所有活跃证书
    certs = client.table("cert_records").select("*").eq(
        "worker_name", worker_name
    ).eq("status", "active").order("expiry_date").execute()
    
    cert_list = certs.data if certs.data else []
    
    if not cert_list:
        return "📋 暂无证书记录。输入【记证书】可以添加证书信息。"
    
    lines = [f"📋 {worker_name} 的证书到期情况：\n"]
    
    expired = []
    urgent = []
    warning = []
    ok = []
    
    for cert in cert_list:
        cert_type = _safe_get(cert, "cert_type", "")
        expiry = _safe_get(cert, "expiry_date", "")
        cert_no = _safe_get(cert, "cert_no", "")
        
        try:
            exp_date = datetime.strptime(expiry[:10], "%Y-%m-%d").date()
            days_left = (exp_date - date.today()).days
        except (ValueError, IndexError):
            days_left = 999
        
        info = f"  • {cert_type}（{cert_no or '无编号'}）到期：{expiry[:10]}，剩余 {days_left} 天"
        
        if days_left < 0:
            expired.append(f"🔴 {info} ⚠️ 已过期！")
        elif days_left <= 30:
            urgent.append(f"🔴 {info} 请尽快复审！")
        elif days_left <= 90:
            warning.append(f"🟡 {info}")
        else:
            ok.append(f"🟢 {info}")
    
    if expired:
        lines.append("⚠️ 已过期（需立即处理）：")
        lines.extend(expired)
        lines.append("")
    if urgent:
        lines.append("🔴 30天内到期（紧急）：")
        lines.extend(urgent)
        lines.append("")
    if warning:
        lines.append("🟡 90天内到期（注意）：")
        lines.extend(warning)
        lines.append("")
    if ok:
        lines.append("🟢 有效期充足：")
        lines.extend(ok)
    
    return "\n".join(lines)


@tool
def get_cert_renewal_guide(cert_type: str) -> str:
    """获取证书复审指南。

    Args:
        cert_type: 证书类型
    """
    guides = {
        "电工证": """📋 电工证复审指南：
1. 提前3个月到当地应急管理局（原安监局）报名
2. 准备材料：身份证原件、电工证原件、近期一寸照片2张、体检证明
3. 参加理论考试（满分100，80分及格）
4. 费用约200-500元
5. 审核通过后发放新证，有效期6年""",
        "焊工证": """📋 焊工证复审指南：
1. 提前3个月到当地应急管理局报名
2. 准备材料：身份证、焊工证原件、照片2张、体检证明
3. 参加理论+实操考试
4. 费用约300-600元
5. 有效期6年，每3年复审一次""",
        "高空作业证": """📋 高空作业证复审指南：
1. 提前3个月到应急管理局报名
2. 准备材料：身份证、证书原件、照片、体检证明（含血压、心电图）
3. 参加理论+实操考试
4. 费用约300-500元
5. 有效期6年，每3年复审一次""",
    }
    
    guide = guides.get(cert_type, f"""📋 {cert_type}复审通用指南：
1. 提前3个月到当地应急管理局或住建局报名
2. 准备材料：身份证、证书原件、照片、体检证明
3. 参加理论考试（部分证书需实操）
4. 费用因证书类型而异
5. 具体请咨询当地主管部门""")
    
    return f"{guide}\n\n💡 建议：提前3个月准备，避免证书过期影响上岗。"
