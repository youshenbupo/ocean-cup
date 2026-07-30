"""
工友权益明白人 - 评估工具
用于自动化测试知识库检索效果和Agent路由准确性
"""

import json
from typing import Optional
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_dev_sdk import KnowledgeClient, Config


# 评估测试集
EVALUATION_CASES = [
    # 法律咨询类
    {"id": "L01", "query": "老板欠了我三个月工资不给", "expected_intent": "legal", "expected_keywords": ["工资支付条例", "欠薪", "维权"]},
    {"id": "L02", "query": "没签劳动合同能要回工资吗", "expected_intent": "legal", "expected_keywords": ["劳动合同法", "双倍工资", "事实劳动关系"]},
    {"id": "L03", "query": "工地上受伤了算工伤吗", "expected_intent": "legal", "expected_keywords": ["工伤保险条例", "工伤认定", "工作时间"]},
    
    # 安全守护类
    {"id": "S01", "query": "脚手架上没防护栏安全吗", "expected_intent": "safety", "expected_keywords": ["脚手架", "防护栏", "高空作业"]},
    {"id": "S02", "query": "今天北京天气怎么样，工地要注意什么", "expected_intent": "safety", "expected_keywords": ["天气", "安全", "提醒"]},
    
    # 心理陪伴类
    {"id": "P01", "query": "我不想活了", "expected_intent": "support", "expected_keywords": ["心理援助", "热线", "关心"]},
    {"id": "P02", "query": "最近心情很差，天天被老板骂", "expected_intent": "support", "expected_keywords": ["理解", "安抚", "陪伴"]},
    
    # 薪资管家类
    {"id": "SA01", "query": "帮我记一下今天的工时", "expected_intent": "salary", "expected_keywords": ["工时", "记录", "工资"]},
    {"id": "SA02", "query": "帮我写个工资欠条", "expected_intent": "salary", "expected_keywords": ["欠条", "欠款", "签字"]},
    
    # 技能导师类
    {"id": "SK01", "query": "我干了5年钢筋工，想提升技能", "expected_intent": "skill", "expected_keywords": ["技能", "培训", "证书"]},
    {"id": "SK02", "query": "焊工证怎么考", "expected_intent": "skill", "expected_keywords": ["焊工", "考证", "培训"]},
    
    # 生活管家类
    {"id": "LF01", "query": "孩子想在当地上学需要什么手续", "expected_intent": "life", "expected_keywords": ["子女", "入学", "手续"]},
    {"id": "LF02", "query": "社保怎么交", "expected_intent": "life", "expected_keywords": ["社保", "医保", "缴费"]},
    
    # 工友社区类
    {"id": "C01", "query": "发个帖子问问大家", "expected_intent": "community", "expected_keywords": ["帖子", "社区", "工友"]},
    
    # 闲聊类
    {"id": "CH01", "query": "你好", "expected_intent": "chat", "expected_keywords": []},
]


@tool
def run_evaluation(test_ids: Optional[str] = None) -> str:
    """
    运行评估测试，检查知识库检索效果。
    
    Args:
        test_ids: 要测试的用例ID，逗号分隔。如不指定则测试全部。
                  例如: "L01,L02,S01" 或 "all"
    
    Returns:
        评估结果报告
    """
    ctx = request_context.get() or new_context(method="run_evaluation")
    
    try:
        config = Config()
        client = KnowledgeClient(config=config)
    except Exception as e:
        return f"初始化知识库客户端失败: {str(e)}"
    
    # 确定要测试的用例
    if test_ids is None or test_ids.lower() == "all":
        cases = EVALUATION_CASES
    else:
        ids = [t.strip() for t in test_ids.split(",")]
        cases = [c for c in EVALUATION_CASES if c["id"] in ids]
    
    results = []
    passed = 0
    failed = 0
    
    for case in cases:
        query = case["query"]
        expected_keywords = case["expected_keywords"]
        
        # 执行知识库检索
        try:
            response = client.search(query=query, top_k=3, min_score=0.3)
            
            if response.code != 0:
                results.append({
                    "id": case["id"],
                    "query": query,
                    "status": "ERROR",
                    "error": response.msg
                })
                failed += 1
                continue
            
            # 检查检索结果
            chunks = response.chunks if response.chunks else []
            retrieved_text = " ".join([c.content for c in chunks])
            
            # 检查关键词命中
            keyword_hits = []
            keyword_misses = []
            for kw in expected_keywords:
                if kw in retrieved_text:
                    keyword_hits.append(kw)
                else:
                    keyword_misses.append(kw)
            
            # 判断是否通过
            hit_rate = len(keyword_hits) / len(expected_keywords) if expected_keywords else 1.0
            status = "PASS" if hit_rate >= 0.5 else "FAIL"
            
            if status == "PASS":
                passed += 1
            else:
                failed += 1
            
            results.append({
                "id": case["id"],
                "query": query,
                "status": status,
                "hit_rate": f"{hit_rate:.0%}",
                "keyword_hits": keyword_hits,
                "keyword_misses": keyword_misses,
                "top_score": chunks[0].score if chunks else 0,
                "top_preview": chunks[0].content[:100] if chunks else "无结果"
            })
            
        except Exception as e:
            results.append({
                "id": case["id"],
                "query": query,
                "status": "ERROR",
                "error": str(e)
            })
            failed += 1
    
    # 生成报告
    report = f"""📊 知识库检索评估报告

📋 测试概况
- 总用例数: {len(cases)}
- 通过: {passed}
- 失败: {failed}
- 通过率: {passed/len(cases)*100:.1f}%

📝 详细结果
"""
    
    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
        report += f"\n{status_icon} [{r['id']}] {r['query']}\n"
        report += f"   状态: {r['status']}\n"
        
        if r["status"] == "PASS":
            report += f"   命中率: {r.get('hit_rate', 'N/A')}\n"
            report += f"   命中关键词: {r.get('keyword_hits', [])}\n"
            report += f"   最高相关度: {r.get('top_score', 0):.3f}\n"
        elif r["status"] == "FAIL":
            report += f"   命中率: {r.get('hit_rate', 'N/A')}\n"
            report += f"   未命中: {r.get('keyword_misses', [])}\n"
        else:
            report += f"   错误: {r.get('error', '未知错误')}\n"
    
    return report


@tool
def search_knowledge_with_rerank(query: str, top_k: int = 5) -> str:
    """
    带重排序的知识库检索工具。
    先检索更多结果，然后根据关键词匹配度进行重排序。
    
    Args:
        query: 检索查询
        top_k: 返回结果数量
    
    Returns:
        检索结果
    """
    ctx = request_context.get() or new_context(method="search_knowledge_with_rerank")
    
    try:
        config = Config()
        client = KnowledgeClient(config=config)
        
        # 先检索更多结果
        response = client.search(query=query, top_k=top_k * 2, min_score=0.2)
        
        if response.code != 0:
            return f"检索失败: {response.msg}"
        
        chunks = response.chunks if response.chunks else []
        
        if not chunks:
            return "未找到相关内容"
        
        # 简单的重排序：根据查询关键词在内容中的出现次数排序
        query_keywords = set(query.replace("，", " ").replace("？", "").split())
        
        def score_chunk(chunk):
            content = chunk.content
            score = chunk.score
            # 关键词命中加分
            for kw in query_keywords:
                if kw in content:
                    score += 0.1
            return score
        
        # 重排序
        sorted_chunks = sorted(chunks, key=score_chunk, reverse=True)[:top_k]
        
        # 格式化输出
        result = []
        for i, chunk in enumerate(sorted_chunks, 1):
            result.append(f"【检索结果{i}】(相关度: {chunk.score:.2f})\n{chunk.content}\n")
        
        return "\n---\n".join(result)
        
    except Exception as e:
        return f"检索出错: {str(e)}"
