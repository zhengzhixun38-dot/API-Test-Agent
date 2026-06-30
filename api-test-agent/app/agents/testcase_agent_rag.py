"""
RAG 增强版 (V2 - 轻量模式注入)
不改变 prompt 结构，只在生成前用知识库判断接口类型，附加针对性规则
"""
import json
import logging
from openai import OpenAI
from app.config import Settings
from app.rag.knowledge_base import get_kb

logger = logging.getLogger(__name__)

# ── 原始 Prompt（复用 baseline，只加 RAG 注入的规则）───

from app.agents.testcase_agent import TESTCASE_GENERATION_PROMPT as BASE_PROMPT


def _analyze_endpoint(api_info: dict) -> list[str]:
    """用知识库分析接口，返回应强调的规则"""
    kb = get_kb()
    hints = []

    # 判断是否需要鉴权
    need_auth = any(
        True for k, v in api_info.get("request_body", {}).items()
        if "token" in k.lower() or "auth" in k.lower()
    )
    has_header_param = "authorization" in json.dumps(api_info).lower()
    need_auth = need_auth or has_header_param

    if need_auth:
        hints.append("此接口需要鉴权。所有正常用例和鉴权异常用例都必须在 headers 中携带 Authorization: Bearer mock-token-2024")

    # 判断方法类型
    method = api_info.get("method", "").upper()
    if method == "GET":
        hints.append("GET 请求参数通过 params 传递（不是 json）")
    elif method in ("POST", "PUT", "PATCH"):
        hints.append(f"{method} 请求体通过 json 传递")

    # 检索相似模式
    patterns = kb.search_patterns(api_info, n_results=3)
    for p in patterns:
        if p not in hints:
            hints.append(p)

    return hints


def generate_with_rag(api_info: dict, settings: Settings) -> str:
    """
    RAG 轻量版：基础 prompt + 精准注入的接口规则
    """
    hints = _analyze_endpoint(api_info)
    api_json = json.dumps(api_info, ensure_ascii=False, indent=2)

    # 将 hints 注入到 prompt 中
    hint_text = "\n".join(f"### {h}" for h in hints) if hints else ""
    rag_block = f"\n\n## 特别注意（RAG 知识库匹配）\n{hint_text}" if hint_text else ""

    prompt = BASE_PROMPT.replace("{api_info}", api_json + rag_block)

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.BASE_URL,
    )
    response = client.chat.completions.create(
        model=settings.MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""
