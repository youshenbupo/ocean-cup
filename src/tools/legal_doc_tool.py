"""法律文书生成工具

生成劳动仲裁申请书、欠薪投诉书、工伤认定申请表等法律文书。
文件上传到对象存储，返回下载URL，方便工友获取和打印。
"""
import os
import tempfile
from datetime import datetime
from typing import Optional
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context

logger = __import__("logging").getLogger(__name__)


def _upload_to_storage(filename: str, content: str) -> str:
    """保存文书到临时文件并上传对象存储，返回下载URL"""
    try:
        from coze_coding_dev_sdk.s3 import S3SyncStorage

        storage = S3SyncStorage(
            endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
            access_key="",
            secret_key="",
            bucket_name=os.getenv("COZE_BUCKET_NAME"),
            region="cn-beijing",
        )

        # 上传文件内容（文本转字节）
        safe_name = filename.replace(" ", "_")
        file_key = storage.upload_file(
            file_content=content.encode("utf-8"),
            file_name=f"legal_docs/{safe_name}",
            content_type="text/plain; charset=utf-8",
        )

        # 生成签名URL（7天有效期）
        download_url = storage.generate_presigned_url(
            key=file_key,
            expire_time=604800,
        )

        return download_url
    except Exception as e:
        logger.warning(f"upload_to_storage failed: {e}, falling back to local save")
        # 降级：保存到本地assets目录
        output_dir = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "legal_docs")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath


@tool
def generate_arbitration_application(
    applicant_name: str,
    applicant_id: str,
    applicant_phone: str,
    applicant_address: str,
    employer_name: str,
    employer_address: str,
    employer_legal_rep: str,
    work_start_date: str,
    work_end_date: str,
    monthly_salary: float,
    claim_amount: float,
    claim_reason: str,
    evidence_list: str,
) -> str:
    """生成劳动仲裁申请书。

    Args:
        applicant_name: 申请人姓名
        applicant_id: 申请人身份证号
        applicant_phone: 申请人联系电话
        applicant_address: 申请人住址
        employer_name: 被申请人（用人单位）名称
        employer_address: 被申请人地址
        employer_legal_rep: 被申请人法定代表人
        work_start_date: 入职日期（YYYY-MM-DD）
        work_end_date: 离职日期或"至今"
        monthly_salary: 月工资金额
        claim_amount: 仲裁请求金额
        claim_reason: 仲裁请求事由（如"拖欠工资"、"违法解除劳动合同"等）
        evidence_list: 证据清单（用逗号分隔，如"劳动合同,工资条,考勤记录"）
    """
    ctx = request_context.get() or new_context(method="generate_arbitration_application")
    
    today = datetime.now().strftime("%Y年%m月%d日")
    evidence_items = [e.strip() for e in evidence_list.split(",") if e.strip()]
    evidence_text = "\n".join([f"    {i+1}. {e}" for i, e in enumerate(evidence_items)])
    
    doc = f"""
{'='*60}
              劳 动 仲 裁 申 请 书
{'='*60}

申请人：{applicant_name}
性别：    
身份证号：{applicant_id}
联系电话：{applicant_phone}
住址：{applicant_address}

被申请人：{employer_name}
地址：{employer_address}
法定代表人：{employer_legal_rep}

{'─'*60}
仲裁请求：
{'─'*60}

    1. 请求裁决被申请人支付申请人{claim_reason}，金额人民币
       {claim_amount:.2f}元（大写：{int(claim_amount)}元整）；
    2. 请求裁决被申请人承担本案仲裁费用。

{'─'*60}
事实与理由：
{'─'*60}

    申请人于{work_start_date}入职被申请人处，担任        岗位，
双方约定月工资为人民币{monthly_salary:.2f}元。

    {claim_reason}。被申请人的行为严重违反了《中华人民共和国劳动
法》第五十条"工资应当以货币形式按月支付给劳动者本人。不得
克扣或者无故拖欠劳动者的工资"及《劳动合同法》的相关规定，
损害了申请人的合法权益。

    综上所述，为维护申请人的合法权益，根据《中华人民共和国
劳动争议调解仲裁法》第二条、第五条之规定，特向贵委提出仲
裁申请，请依法裁决。

{'─'*60}
证据清单：
{'─'*60}
{evidence_text}

    以上证据均为原件/复印件，请贵委核实。

{'─'*60}

    此致
        劳动争议仲裁委员会

                                        申请人（签名）：
                                        日期：{today}

{'='*60}
                    注 意 事 项
{'='*60}
1. 本申请书需一式两份，仲裁委和被申请人各一份
2. 需携带身份证原件及复印件
3. 证据材料需准备复印件
4. 仲裁时效为知道或应当知道权利被侵害之日起一年内
5. 劳动仲裁不收费
"""
    
    filename = f"劳动仲裁申请书_{applicant_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    filepath = _upload_to_storage(filename, doc)
    
    return f"""✅ 劳动仲裁申请书已生成！

📄 文件：{filename}
🔗 下载：{filepath}

📋 申请信息摘要：
  • 申请人：{applicant_name}
  • 被申请人：{employer_name}
  • 仲裁请求金额：¥{claim_amount:.2f}
  • 事由：{claim_reason}

⚠️ 温馨提示：
  1. 打印后需在"申请人"处手写签名
  2. 携带身份证原件和复印件
  3. 证据材料准备复印件
  4. 去当地劳动仲裁委员会提交
"""


@tool
def generate_wage_complaint(
    worker_name: str,
    worker_id: str,
    worker_phone: str,
    employer_name: str,
    employer_address: str,
    work_period: str,
    owed_amount: float,
    owed_months: int,
    complaint_reason: str,
) -> str:
    """生成欠薪投诉书（用于向劳动监察大队投诉）。

    Args:
        worker_name: 投诉人姓名
        worker_id: 投诉人身份证号
        worker_phone: 投诉人联系电话
        employer_name: 被投诉单位名称
        employer_address: 被投诉单位地址
        work_period: 工作期间（如"2024年3月至2024年9月"）
        owed_amount: 拖欠工资金额
        owed_months: 拖欠月数
        complaint_reason: 投诉事由详细描述
    """
    ctx = request_context.get() or new_context(method="generate_wage_complaint")
    
    today = datetime.now().strftime("%Y年%m月%d日")
    
    doc = f"""
{'='*60}
              欠 薪 投 诉 书
{'='*60}

投诉人：{worker_name}
身份证号：{worker_id}
联系电话：{worker_phone}

被投诉单位：{employer_name}
单位地址：{employer_address}

{'─'*60}
投诉请求：
{'─'*60}

    请求劳动保障监察部门依法查处被投诉单位拖欠工资的违法
行为，责令被投诉单位立即支付拖欠投诉人工资人民币
{owed_amount:.2f}元。

{'─'*60}
事实与理由：
{'─'*60}

    投诉人于{work_period}在被投诉单位{employer_name}从事
        工作。工作期间，投诉人按照单位安排认真工作，
但被投诉单位已连续{owed_months}个月未支付投诉人工资，共计
拖欠人民币{owed_amount:.2f}元。

    {complaint_reason}

    被投诉单位的行为违反了《保障农民工工资支付条例》第三
条"农民工有按时足额获得工资的权利。任何单位和个人不得
拖欠农民工工资"之规定，也违反了《劳动法》第五十条的规
定。

    现投诉人特向贵部门投诉，恳请依法查处，维护投诉人的
合法权益。

{'─'*60}

    此致
        劳动保障监察大队

                                        投诉人（签名）：
                                        日期：{today}

{'='*60}
                    附 件
{'='*60}
1. 投诉人身份证复印件
2. 工作证明（劳动合同/工牌/考勤记录等）
3. 欠薪证明（工资条/欠条/银行流水等）
"""
    
    filename = f"欠薪投诉书_{worker_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    filepath = _upload_to_storage(filename, doc)
    
    return f"""✅ 欠薪投诉书已生成！

📄 文件：{filename}
🔗 下载：{filepath}

📋 投诉信息摘要：
  • 投诉人：{worker_name}
  • 被投诉单位：{employer_name}
  • 拖欠金额：¥{owed_amount:.2f}
  • 拖欠月数：{owed_months}个月

📍 下一步：
  携带本投诉书 + 身份证复印件 + 工作证明 + 欠薪证明
  前往项目所在地劳动保障监察大队提交投诉
"""


@tool
def generate_wage_slip(
    worker_name: str,
    employer_name: str,
    work_month: str,
    base_days: int,
    base_daily_wage: float,
    overtime_weekdays: int = 0,
    overtime_weekends: int = 0,
    overtime_holidays: int = 0,
    deductions: float = 0,
    deductions_note: str = "",
) -> str:
    """生成工资条/工资结算单。

    Args:
        worker_name: 工人姓名
        employer_name: 用人单位/雇主名称
        work_month: 工作月份（如"2024年9月"）
        base_days: 正常出勤天数
        base_daily_wage: 日工资标准
        overtime_weekdays: 工作日加班天数
        overtime_weekends: 周末加班天数
        overtime_holidays: 节假日加班天数
        deductions: 扣款金额（如预支、罚款等）
        deductions_note: 扣款原因说明
    """
    ctx = request_context.get() or new_context(method="generate_wage_slip")
    
    today = datetime.now().strftime("%Y年%m月%d日")
    
    # 计算各项工资
    base_pay = base_days * base_daily_wage
    weekday_ot = overtime_weekdays * base_daily_wage * 1.5
    weekend_ot = overtime_weekends * base_daily_wage * 2.0
    holiday_ot = overtime_holidays * base_daily_wage * 3.0
    total_earnings = base_pay + weekday_ot + weekend_ot + holiday_ot
    net_pay = total_earnings - deductions
    
    doc = f"""
{'='*60}
              工 资 结 算 单
{'='*60}

单位名称：{employer_name}
工人姓名：{worker_name}
结算月份：{work_month}
制单日期：{today}

{'─'*60}
                    明 细 项 目
{'─'*60}

┌──────────────────────────────────────────────────┐
│  项目              天数    单价(元)    小计(元)   │
├──────────────────────────────────────────────────┤
│  正常工资          {base_days:>3}     {base_daily_wage:>8.2f}   {base_pay:>9.2f}   │
│  工作日加班(1.5x)  {overtime_weekdays:>3}     {base_daily_wage*1.5:>8.2f}   {weekday_ot:>9.2f}   │
│  周末加班(2x)      {overtime_weekends:>3}     {base_daily_wage*2.0:>8.2f}   {weekend_ot:>9.2f}   │
│  节假日加班(3x)    {overtime_holidays:>3}     {base_daily_wage*3.0:>8.2f}   {holiday_ot:>9.2f}   │
├──────────────────────────────────────────────────┤
│  应发合计                                    {total_earnings:>9.2f}   │
"""
    if deductions > 0:
        doc += f"│  扣款（{deductions_note}）                           -{deductions:>8.2f}   │\n"
    doc += f"""├──────────────────────────────────────────────────┤
│  实发合计                                    {net_pay:>9.2f}   │
└──────────────────────────────────────────────────┘

{'─'*60}
                    签 字 确 认
{'─'*60}

    工人签字：                    雇主/负责人签字：
    
    日期：      年    月    日     日期：      年    月    日

{'='*60}
注：本工资结算单一式两份，工人和雇主各执一份，具有同等效力。
"""
    
    filename = f"工资结算单_{worker_name}_{work_month.replace('年','').replace('月','')}.txt"
    filepath = _upload_to_storage(filename, doc)
    
    return f"""✅ 工资结算单已生成！

📄 文件：{filename}
🔗 下载：{filepath}

💰 工资明细：
  • 正常工资：{base_days}天 × ¥{base_daily_wage:.2f} = ¥{base_pay:.2f}
  • 工作日加班：{overtime_weekdays}天 × ¥{base_daily_wage*1.5:.2f} = ¥{weekday_ot:.2f}
  • 周末加班：{overtime_weekends}天 × ¥{base_daily_wage*2.0:.2f} = ¥{weekend_ot:.2f}
  • 节假日加班：{overtime_holidays}天 × ¥{base_daily_wage*3.0:.2f} = ¥{holiday_ot:.2f}
  • 应发合计：¥{total_earnings:.2f}
""" + (f"  • 扣款：¥{deductions:.2f}（{deductions_note}）\n" if deductions > 0 else "") + f"""  • 实发合计：¥{net_pay:.2f}

⚠️ 温馨提示：
  1. 打印后双方签字确认，各留一份
  2. 签字即表示双方对工资金额无异议
  3. 如有争议，可作为劳动仲裁证据
"""


@tool
def generate_iou(
    debtor_name: str,
    debtor_id: str,
    creditor_name: str,
    amount: float,
    amount_in_words: str,
    reason: str,
    repayment_date: str,
    witness_name: str = "",
) -> str:
    """生成欠条/借条。

    Args:
        debtor_name: 欠款人姓名
        debtor_id: 欠款人身份证号
        creditor_name: 债权人姓名（被欠钱的工友）
        amount: 欠款金额
        amount_in_words: 金额大写（如"壹万贰仟叁佰元整"）
        reason: 欠款原因（如"2024年3月至8月工资"）
        repayment_date: 约定还款日期
        witness_name: 见证人姓名（可选）
    """
    ctx = request_context.get() or new_context(method="generate_iou")
    
    today = datetime.now().strftime("%Y年%m月%d日")
    
    witness_section = ""
    if witness_name:
        witness_section = f"""
见证人：{witness_name}
身份证号：
联系电话：
"""
    
    doc = f"""
{'='*60}
                    欠    条
{'='*60}

    今欠到 {creditor_name}（身份证号：                ）
人民币（大写）{amount_in_words}（¥{amount:.2f}元）。

    欠款原因：{reason}

    约定还款日期：{repayment_date}

    如逾期未还，欠款人自愿按照全国银行间同业拆借中心公布
的贷款市场报价利率（LPR）的4倍支付利息，并承担债权人
为实现债权所支出的合理费用（包括但不限于诉讼费、律师费、
交通费等）。

    特立此据为证。

{'─'*60}

    欠款人（签字按手印）：{debtor_name}
    身份证号：{debtor_id}
    联系电话：
    
    日期：{today}
{witness_section}
{'='*60}
                    注 意 事 项
{'='*60}
1. 欠款人必须亲笔签名并按手印
2. 身份证号必须填写完整
3. 金额大小写必须一致
4. 还款日期必须明确
5. 最好有见证人在场
6. 欠条原件妥善保管，拍照备份
"""
    
    filename = f"欠条_{debtor_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    filepath = _upload_to_storage(filename, doc)
    
    return f"""✅ 欠条已生成！

📄 文件：{filename}
🔗 下载：{filepath}

📋 欠条信息：
  • 欠款人：{debtor_name}（{debtor_id}）
  • 债权人：{creditor_name}
  • 欠款金额：¥{amount:.2f}（{amount_in_words}）
  • 欠款原因：{reason}
  • 还款日期：{repayment_date}

⚠️ 重要提醒：
  1. 欠款人必须当面签字按手印
  2. 核对身份证号是否正确
  3. 最好有第三方见证人在场
  4. 签完后立即拍照备份
  5. 原件妥善保管，不要给欠款人
"""
