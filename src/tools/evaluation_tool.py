"""
评估工具 - 用于评估Agent回复质量
"""
from typing import Optional
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def evaluate_response(
    query: str,
    response: str,
    expected_category: str = ""
) -> str:
    """
    评估Agent回复的质量（供开发者调试使用）。
    
    Args:
        query: 用户原始问题
        response: Agent的回复内容
        expected_category: 期望的路由分类（legal/safety/salary等）
    """
    ctx = request_context.get() or new_context(method="evaluate_response")
    
    # 基础检查
    issues = []
    scores = {}
    
    # 1. 回复长度检查
    response_len = len(response)
    if response_len < 50:
        issues.append("回复过短，可能不够详细")
        scores["length"] = 0.3
    elif response_len > 2000:
        issues.append("回复过长，建议精简")
        scores["length"] = 0.7
    else:
        scores["length"] = 1.0
    
    # 2. 格式检查
    has_structure = any(marker in response for marker in ["#", "【", "📋", "📞", "⚖️", "💡", "🔍"])
    if has_structure:
        scores["structure"] = 1.0
    else:
        scores["structure"] = 0.5
        issues.append("回复缺少结构化格式")
    
    # 3. 是否包含实用信息
    has_actionable = any(keyword in response for keyword in [
        "步骤", "建议", "可以", "应该", "拨打", "电话", "热线", "投诉", "仲裁"
    ])
    if has_actionable:
        scores["actionable"] = 1.0
    else:
        scores["actionable"] = 0.5
        issues.append("回复缺少可操作的建议")
    
    # 4. 是否包含法律/政策引用
    has_reference = any(keyword in response for keyword in [
        "条例", "法律", "规定", "第", "条", "《", "》"
    ])
    if has_reference:
        scores["reference"] = 1.0
    else:
        scores["reference"] = 0.6
    
    # 5. 是否包含联系方式/举报渠道
    has_contact = any(keyword in response for keyword in [
        "12333", "12348", "12350", "12345", "热线", "电话", "投诉"
    ])
    if has_contact:
        scores["contact"] = 1.0
    else:
        scores["contact"] = 0.7
        issues.append("回复缺少维权渠道信息")
    
    # 计算总分
    total_score = sum(scores.values()) / len(scores)
    
    # 生成评估报告
    report = f"【回复质量评估】\n"
    report += f"用户问题：{query[:50]}...\n"
    if expected_category:
        report += f"期望分类：{expected_category}\n"
    report += f"\n评分明细：\n"
    report += f"  - 回复长度：{scores['length']:.1f}\n"
    report += f"  - 结构化格式：{scores['structure']:.1f}\n"
    report += f"  - 可操作性：{scores['actionable']:.1f}\n"
    report += f"  - 法规引用：{scores['reference']:.1f}\n"
    report += f"  - 维权渠道：{scores['contact']:.1f}\n"
    report += f"\n总分：{total_score:.2f}/1.00\n"
    
    if issues:
        report += f"\n改进建议：\n"
        for issue in issues:
            report += f"  ⚠️ {issue}\n"
    
    if total_score >= 0.9:
        report += "\n✅ 优秀回复"
    elif total_score >= 0.7:
        report += "\n👍 良好回复"
    else:
        report += "\n⚠️ 需要改进"
    
    return report


@tool
def check_route_accuracy(test_cases: str) -> str:
    """
    批量检查路由准确性（供开发者调试使用）。
    
    Args:
        test_cases: JSON格式测试用例，如：
            [{"query": "老板欠薪", "expected": "legal"}, {"query": "工地安全隐患", "expected": "safety"}]
    """
    import json
    
    try:
        cases = json.loads(test_cases)
    except json.JSONDecodeError:
        return "测试用例格式错误，请提供合法的JSON"
    
    results = []
    correct = 0
    
    for case in cases:
        query = case.get("query", "")
        expected = case.get("expected", "")
        
        # 使用关键词路由进行快速检测
        from agents.agent import _keyword_route
        actual = _keyword_route(query) or "unknown"
        
        is_correct = (actual == expected)
        if is_correct:
            correct += 1
        
        results.append({
            "query": query,
            "expected": expected,
            "actual": actual,
            "correct": is_correct
        })
    
    accuracy = correct / len(cases) if cases else 0
    
    report = f"【路由准确性测试】\n"
    report += f"测试用例数：{len(cases)}\n"
    report += f"正确数：{correct}\n"
    report += f"准确率：{accuracy:.1%}\n\n"
    
    for r in results:
        status = "✅" if r["correct"] else "❌"
        report += f"{status} '{r['query']}' -> 期望:{r['expected']}, 实际:{r['actual']}\n"
    
    return report
