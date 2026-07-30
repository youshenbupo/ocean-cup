"""工友权益知识库检索工具

提供知识库语义搜索能力，用于检索法律法规、政策解读、典型案例、维权渠道等信息。
"""

from langchain.tools import tool
from coze_coding_dev_sdk import KnowledgeClient, Config
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


def _search_knowledge(query: str, top_k: int = 5) -> str:
    """内部知识库检索函数，供多个tool复用"""
    ctx = request_context.get() or new_context(method="knowledge_search")
    config = Config()
    client = KnowledgeClient(config=config, ctx=ctx)

    response = client.search(
        query=query,
        top_k=top_k,
        min_score=0.3,
    )

    if response.code == 0 and response.chunks:
        results = []
        for i, chunk in enumerate(response.chunks, 1):
            results.append(f"【检索结果{i}】(相关度: {chunk.score:.2f})\n{chunk.content}")
        return "\n\n---\n\n".join(results)
    else:
        return "未在知识库中检索到相关内容。建议告知工友拨打12333（人力资源社会保障热线）或12348（法律服务热线）获取帮助。"


@tool
def search_law_knowledge(query: str) -> str:
    """检索建筑工友权益保障相关的法律法规、政策解读、典型案例和维权渠道知识库。
    当工友咨询权益问题时，必须先调用此工具检索相关法条和案例，确保回答准确有据。
    输入参数为工友的问题描述或关键词，如"拖欠工资"、"工伤认定"、"未签合同"等。
    """
    return _search_knowledge(query, top_k=5)


@tool
def search_hotlines(query: str) -> str:
    """查询维权投诉热线和渠道信息。
    当工友询问"找谁帮忙"、"去哪投诉"、"电话号码"等问题时调用此工具。
    输入参数为地区名称或"全国"，如"河北"、"北京"、"全国"等。
    """
    full_query = f"维权渠道 热线 投诉 {query}"
    return _search_knowledge(full_query, top_k=3)
