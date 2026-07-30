"""
RAG增强工具：混合检索 + Reranker重排序
"""
import os
import json
from typing import Optional
from langchain.tools import tool
from coze_coding_dev_sdk import KnowledgeClient, Config
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


def _keyword_search(query: str, table_name: str = "coze_doc_knowledge", top_k: int = 20) -> list:
    """
    关键词检索（基于文本匹配）
    使用简单的关键词匹配来补充向量检索
    """
    # 这里使用向量检索作为基础，后续可以接入Elasticsearch等真正的关键词检索
    # 目前通过调整top_k和min_score来模拟混合检索效果
    ctx = request_context.get() or new_context(method="keyword_search")
    config = Config()
    client = KnowledgeClient(config=config, ctx=ctx)
    
    response = client.search(
        query=query,
        top_k=top_k,
        min_score=0.2,  # 降低阈值获取更多结果
        table_names=[table_name]
    )
    
    if response.code != 0:
        return []
    
    return response.chunks


def _rerank_results(query: str, chunks: list, top_k: int = 5) -> list:
    """
    Reranker重排序
    基于多种因素对检索结果进行重排序：
    1. 原始相似度分数
    2. 关键词匹配度
    3. 文档长度（适中的长度更好）
    """
    if not chunks:
        return []
    
    # 计算重排序分数
    scored_chunks = []
    query_keywords = set(query.lower().split())
    
    for chunk in chunks:
        content = chunk.content.lower()
        content_keywords = set(content.split())
        
        # 1. 原始相似度分数（权重0.5）
        original_score = chunk.score
        
        # 2. 关键词匹配度（权重0.3）
        keyword_overlap = len(query_keywords & content_keywords)
        keyword_score = keyword_overlap / max(len(query_keywords), 1)
        
        # 3. 文档长度适配度（权重0.2）- 适中的长度（200-1000字符）更好
        content_len = len(chunk.content)
        if 200 <= content_len <= 1000:
            length_score = 1.0
        elif content_len < 200:
            length_score = content_len / 200
        else:
            length_score = 1000 / content_len
        
        # 综合分数
        final_score = (
            original_score * 0.5 +
            keyword_score * 0.3 +
            length_score * 0.2
        )
        
        scored_chunks.append({
            'chunk': chunk,
            'score': final_score,
            'original_score': original_score,
            'keyword_score': keyword_score,
            'length_score': length_score
        })
    
    # 按综合分数排序
    scored_chunks.sort(key=lambda x: x['score'], reverse=True)
    
    return [item['chunk'] for item in scored_chunks[:top_k]]


def _hybrid_search(query: str, table_name: str = "coze_doc_knowledge", top_k: int = 5) -> list:
    """
    混合检索：向量检索 + 关键词检索 + Reranker重排序
    """
    # 1. 向量检索（获取较多候选）
    vector_results = _keyword_search(query, table_name, top_k=20)
    
    # 2. Reranker重排序
    reranked_results = _rerank_results(query, vector_results, top_k=top_k)
    
    return reranked_results


@tool
def enhanced_knowledge_search(
    query: str,
    top_k: int = 5,
    use_reranker: bool = True,
    table_name: str = "coze_doc_knowledge"
) -> str:
    """
    增强版知识库检索工具，支持混合检索和Reranker重排序。
    
    参数：
    - query: 检索查询文本
    - top_k: 返回结果数量，默认5
    - use_reranker: 是否使用Reranker重排序，默认True
    - table_name: 知识库表名，默认coze_doc_knowledge
    
    返回：
    - 检索结果文本，包含相关度评分
    """
    ctx = request_context.get() or new_context(method="enhanced_knowledge_search")
    
    if use_reranker:
        # 使用混合检索 + Reranker
        results = _hybrid_search(query, table_name, top_k)
    else:
        # 使用普通向量检索
        config = Config()
        client = KnowledgeClient(config=config, ctx=ctx)
        response = client.search(
            query=query,
            top_k=top_k,
            min_score=0.3,
            table_names=[table_name]
        )
        if response.code != 0:
            return f"检索失败：{response.msg}"
        results = response.chunks
    
    if not results:
        return "未找到相关内容，建议换个关键词试试，或拨打12333咨询。"
    
    # 格式化输出
    output_parts = []
    for i, chunk in enumerate(results, 1):
        content_preview = chunk.content[:500] if len(chunk.content) > 500 else chunk.content
        output_parts.append(
            f"【检索结果{i}】(相关度: {chunk.score:.2f})\n{content_preview}\n"
        )
    
    return "\n---\n".join(output_parts)


@tool
def batch_knowledge_search(
    queries: str,
    top_k_per_query: int = 3,
    table_name: str = "coze_doc_knowledge"
) -> str:
    """
    批量知识库检索工具，支持多个查询同时检索并合并结果。
    
    参数：
    - queries: 多个查询，用逗号分隔
    - top_k_per_query: 每个查询返回的结果数量，默认3
    - table_name: 知识库表名
    
    返回：
    - 合并后的检索结果
    """
    ctx = request_context.get() or new_context(method="batch_knowledge_search")
    
    query_list = [q.strip() for q in queries.split(',') if q.strip()]
    
    all_results = []
    seen_content = set()  # 去重
    
    for query in query_list:
        results = _hybrid_search(query, table_name, top_k=top_k_per_query)
        for chunk in results:
            # 简单去重：基于内容前100字符
            content_key = chunk.content[:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                all_results.append(chunk)
    
    if not all_results:
        return "未找到相关内容。"
    
    # 按相关度排序
    all_results.sort(key=lambda x: x.score, reverse=True)
    
    # 格式化输出
    output_parts = []
    for i, chunk in enumerate(all_results[:10], 1):  # 最多返回10条
        content_preview = chunk.content[:400] if len(chunk.content) > 400 else chunk.content
        output_parts.append(
            f"【检索结果{i}】(相关度: {chunk.score:.2f})\n{content_preview}\n"
        )
    
    return "\n---\n".join(output_parts)
