"""
薪资管家工具 - 工时记录、工资核算、欠薪预警
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from langchain.tools import tool
from postgrest.exceptions import APIError
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client


@tool
def record_work(
    worker_name: str,
    work_date: str,
    daily_wage: float,
    hours_worked: float = 8.0,
    is_overtime: bool = False,
    overtime_type: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    记录一天的工时。
    
    Args:
        worker_name: 工友姓名
        work_date: 工作日期，格式 YYYY-MM-DD
        daily_wage: 日工资（元）
        hours_worked: 工作时长（小时），默认8小时
        is_overtime: 是否加班
        overtime_type: 加班类型：weekday/weekend/holiday
        notes: 备注
    """
    ctx = request_context.get() or new_context(method="record_work")
    client = get_supabase_client(ctx)
    
    try:
        # 检查是否已存在记录
        existing = client.table('work_records').select('id').eq(
            'worker_name', worker_name
        ).eq('work_date', work_date).maybe_single().execute()
        
        if existing and existing.data and isinstance(existing.data, dict):
            # 更新记录
            record_id = existing.data.get('id')
            update_data = {
                'daily_wage': daily_wage,
                'work_hours': hours_worked,
                'is_overtime': is_overtime,
                'overtime_type': overtime_type,
                'notes': notes,
                'updated_at': datetime.utcnow().isoformat()
            }
            response = client.table('work_records').update(update_data).eq(
                'id', record_id
            ).execute()
            return f"已更新 {work_date} 的工时记录：日薪{daily_wage}元，工时{hours_worked}小时"
        else:
            # 插入新记录
            insert_data = {
                'worker_name': worker_name,
                'work_date': work_date,
                'daily_wage': daily_wage,
                'work_hours': hours_worked,
                'is_overtime': is_overtime,
                'overtime_type': overtime_type,
                'notes': notes
            }
            response = client.table('work_records').insert(insert_data).execute()
            return f"已记录 {work_date} 的工时：日薪{daily_wage}元，工时{hours_worked}小时"
    except APIError as e:
        return f"记录工时失败：{e.message}"


@tool
def calculate_salary(worker_name: str, start_date: str, end_date: str) -> str:
    """
    计算指定时间段内的应发工资。
    
    Args:
        worker_name: 工友姓名
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD
    """
    ctx = request_context.get() or new_context(method="calculate_salary")
    client = get_supabase_client(ctx)
    
    try:
        response = client.table('work_records').select(
            'work_date,daily_wage,work_hours,is_overtime,overtime_type'
        ).eq('worker_name', worker_name).gte(
            'work_date', start_date
        ).lte('work_date', end_date).order('work_date').execute()
        
        records = response.data
        if not records or not isinstance(records, list):
            return f"未找到 {worker_name} 在 {start_date} 至 {end_date} 期间的工时记录"
        
        total = Decimal('0')
        details = []
        
        for r in records:
            if not isinstance(r, dict):
                continue
            daily_wage = Decimal(str(r.get('daily_wage', 0)))
            hours = Decimal(str(r.get('work_hours', 8)))
            base_hours = Decimal('8')
            
            is_overtime = r.get('is_overtime', False)
            overtime_type = r.get('overtime_type')
            
            if is_overtime and overtime_type:
                if overtime_type == 'weekend':
                    # 周末加班 2倍
                    overtime_pay = daily_wage * Decimal('2')
                    day_total = overtime_pay
                    detail = f"{r.get('work_date')}: 周末加班 2倍工资 = {day_total}元"
                elif overtime_type == 'holiday':
                    # 法定节假日 3倍
                    overtime_pay = daily_wage * Decimal('3')
                    day_total = overtime_pay
                    detail = f"{r.get('work_date')}: 节假日加班 3倍工资 = {day_total}元"
                else:
                    # 工作日加班 1.5倍（按小时计算）
                    hourly_rate = daily_wage / base_hours
                    overtime_hours = hours - base_hours
                    if overtime_hours > 0:
                        overtime_pay = hourly_rate * overtime_hours * Decimal('1.5')
                        day_total = daily_wage + overtime_pay
                        detail = f"{r.get('work_date')}: 正常{daily_wage}元 + 加班{overtime_hours}小时×1.5倍 = {day_total}元"
                    else:
                        day_total = daily_wage
                        detail = f"{r.get('work_date')}: 正常工资 = {day_total}元"
            else:
                day_total = daily_wage
                detail = f"{r.get('work_date')}: 正常工资 = {day_total}元"
            
            total += day_total
            details.append(detail)
        
        result = f"【{worker_name} 工资核算】\n"
        result += f"统计期间：{start_date} 至 {end_date}\n"
        result += f"工作天数：{len(records)} 天\n\n"
        result += "明细：\n" + "\n".join(details) + "\n\n"
        result += f"应发工资合计：{total} 元"
        
        return result
    except APIError as e:
        return f"计算工资失败：{e.message}"


@tool
def check_overdue_reminders() -> str:
    """
    检查所有逾期未发的薪资提醒。
    """
    ctx = request_context.get() or new_context(method="check_overdue_reminders")
    client = get_supabase_client(ctx)
    
    try:
        today = date.today().isoformat()
        response = client.table('salary_reminders').select(
            'worker_name,employer_name,expected_amount,expected_pay_date,status,reminder_sent'
        ).eq('status', 'pending').lte('expected_pay_date', today).execute()
        
        reminders = response.data
        if not reminders or not isinstance(reminders, list):
            return "当前没有逾期未发的薪资提醒"
        
        result = f"【逾期未发提醒】共 {len(reminders)} 条：\n\n"
        for r in reminders:
            if not isinstance(r, dict):
                continue
            due_date_str = r.get('expected_pay_date', '')
            if due_date_str:
                days_overdue = (date.today() - date.fromisoformat(due_date_str)).days
            else:
                days_overdue = 0
            result += f"- {r.get('worker_name', '')} 被 {r.get('employer_name', '')} 欠薪 {r.get('expected_amount', 0)}元\n"
            result += f"  约定发薪日：{due_date_str}，已逾期 {days_overdue} 天\n\n"
        
        result += "💡 建议：超过约定发薪日7天未发，建议尽快与雇主沟通；超过15天，建议向劳动监察部门投诉。"
        
        return result
    except APIError as e:
        return f"查询逾期提醒失败：{e.message}"


@tool
def create_salary_reminder(
    worker_name: str,
    employer_name: str,
    expected_amount: float,
    expected_pay_date: str,
    notes: Optional[str] = None
) -> str:
    """
    创建薪资发放提醒。
    
    Args:
        worker_name: 工友姓名
        employer_name: 雇主/公司名称
        expected_amount: 应发金额（元）
        expected_pay_date: 约定发薪日期，格式 YYYY-MM-DD
        notes: 备注（如工作期间等补充信息）
    """
    ctx = request_context.get() or new_context(method="create_salary_reminder")
    client = get_supabase_client(ctx)
    
    try:
        insert_data = {
            'worker_name': worker_name,
            'employer_name': employer_name,
            'expected_amount': expected_amount,
            'expected_pay_date': expected_pay_date,
            'status': 'pending',
            'reminder_sent': False,
            'notes': notes
        }
        response = client.table('salary_reminders').insert(insert_data).execute()
        
        return f"已创建薪资提醒：{employer_name} 应于 {expected_pay_date} 前支付 {expected_amount}元 给 {worker_name}。到期未发我会提醒你。"
    except APIError as e:
        return f"创建提醒失败：{e.message}"


@tool
def mark_reminder_paid(reminder_id: int) -> str:
    """
    将薪资提醒标记为已支付。
    
    Args:
        reminder_id: 提醒记录的ID
    """
    ctx = request_context.get() or new_context(method="mark_reminder_paid")
    client = get_supabase_client(ctx)
    
    try:
        update_data = {
            'status': 'paid',
            'reminder_sent': True,
            'updated_at': datetime.utcnow().isoformat()
        }
        response = client.table('salary_reminders').update(update_data).eq(
            'id', reminder_id
        ).execute()
        
        if response.data:
            return f"已将提醒 #{reminder_id} 标记为已支付 ✅"
        else:
            return f"未找到ID为 {reminder_id} 的提醒记录"
    except APIError as e:
        return f"更新提醒状态失败：{e.message}"


@tool
def get_my_reminders(worker_name: str) -> str:
    """
    查询某位工友的所有薪资提醒记录。
    
    Args:
        worker_name: 工友姓名
    """
    ctx = request_context.get() or new_context(method="get_my_reminders")
    client = get_supabase_client(ctx)
    
    try:
        response = client.table('salary_reminders').select(
            'id,worker_name,employer_name,expected_amount,expected_pay_date,status,reminder_sent,created_at'
        ).eq('worker_name', worker_name).order('created_at', desc=True).execute()
        
        reminders = response.data
        if not reminders or not isinstance(reminders, list):
            return f"未找到 {worker_name} 的薪资提醒记录"
        
        result = f"【{worker_name} 的薪资提醒】共 {len(reminders)} 条：\n\n"
        for r in reminders:
            if not isinstance(r, dict):
                continue
            status_emoji = {'pending': '⏳', 'paid': '✅', 'overdue': '❗'}.get(r.get('status', ''), '❓')
            result += f"{status_emoji} #{r.get('id')} | {r.get('employer_name', '')} | "
            result += f"{r.get('expected_amount', 0)}元 | "
            result += f"约定发薪日：{r.get('expected_pay_date', '')} | "
            result += f"状态：{r.get('status', '')}\n"
        
        return result
    except APIError as e:
        return f"查询提醒失败：{e.message}"
