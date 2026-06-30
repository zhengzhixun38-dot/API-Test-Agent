"""
RAG 知识库 (离线版)
用 sklearn TF-IDF 做向量检索，无需联网下载模型
"""
import os
import json
import logging
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base")


class KnowledgeBase:
    """轻量 RAG 知识库（TF-IDF + 本地存储）"""

    def __init__(self, persist_dir: str | None = None):
        self._dir = persist_dir or KB_PATH
        os.makedirs(self._dir, exist_ok=True)

        self._cases: list[dict] = []
        self._endpoints: list[dict] = []
        self._patterns: list[str] = []

        self._case_texts: list[str] = []
        self._ep_texts: list[str] = []
        self._ep_matrix = None

        # 尝试加载已有数据
        self._load()

    # ── 持久化 ───────────────────────────────────────

    def _save(self):
        with open(os.path.join(self._dir, "cases.json"), "w", encoding="utf-8") as f:
            json.dump(self._cases, f, ensure_ascii=False)
        with open(os.path.join(self._dir, "endpoints.json"), "w", encoding="utf-8") as f:
            json.dump(self._endpoints, f, ensure_ascii=False)
        with open(os.path.join(self._dir, "patterns.json"), "w", encoding="utf-8") as f:
            json.dump(self._patterns, f, ensure_ascii=False)

    def _load(self):
        for name, attr in [("cases.json", "_cases"), ("endpoints.json", "_endpoints"), ("patterns.json", "_patterns")]:
            path = os.path.join(self._dir, name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    setattr(self, attr, json.load(f))
        self._case_texts = [json.dumps(c, ensure_ascii=False) for c in self._cases]
        self._ep_texts = [json.dumps(e, ensure_ascii=False) for e in self._endpoints]

    # ── 构建索引 ──────────────────────────────────────

    def reset(self):
        self._cases = []
        self._endpoints = []
        self._patterns = []
        self._vectorizer = None
        self._case_matrix = None

    def build_from_handwritten(self, endpoints: list[dict], all_cases: dict[str, list[dict]]):
        """从手写用例构建初始知识库"""
        self.reset()

        self._endpoints = list(endpoints)
        self._ep_texts = [json.dumps(e, ensure_ascii=False) for e in endpoints]

        for key, cases in all_cases.items():
            for c in cases:
                if "error" not in c:
                    self._cases.append(c)
        self._case_texts = [json.dumps(c, ensure_ascii=False) for c in self._cases]

        self._patterns = [
            "鉴权接口必须在 headers 中携带 Authorization: Bearer mock-token-2024",
            "参数校验失败(Pydantic)返回 HTTP 422，业务规则错误返回 400，鉴权失败返回 401",
            "错误响应断言用 contains_fields: [code, message]，不要用 detail",
            "成功响应断言用 contains_fields: [code, message, data]",
            "GET 请求参数通过 params 传递",
            "POST/PUT 请求体通过 json 传递",
            "边界测试：最小值、最大值、刚好超出、刚好达标",
            "missing_param 测试时保持其他参数合法",
            "非鉴权接口不生成 auth_error 类型用例",
        ]

        self._save()
        logger.info("Knowledge base: %d cases, %d endpoints, %d patterns",
                     len(self._cases), len(self._endpoints), len(self._patterns))

    # ── 检索 ──────────────────────────────────────────

    def _search(self, query: str, pool_texts: list[str], pool_items: list, n_results: int) -> list:
        """通用检索：每查询时构建向量，简单但稳定"""
        if not pool_items or not pool_texts:
            return []

        try:
            # 每次查询时构建 TF-IDF（避免持久化矩阵的兼容问题）
            vec = TfidfVectorizer(max_features=500, analyzer="char_wb", ngram_range=(2, 4))
            all_texts = pool_texts + [query]
            matrix = vec.fit_transform(all_texts)
            query_vec = matrix[-1:]  # 最后一行为查询
            doc_matrix = matrix[:-1]  # 前面为文档

            scores = cosine_similarity(query_vec, doc_matrix)[0]
            indices = np.argsort(scores)[::-1]
            results = []
            for i in indices:
                if len(results) >= n_results:
                    break
                if scores[i] > 0.05:
                    results.append(pool_items[i])
            return results if results else pool_items[:n_results]
        except Exception as e:
            logger.warning("Search error: %s", e)
            return pool_items[:n_results]

    def search_similar_cases(self, api_info: dict, n_results: int = 5) -> list[dict]:
        query = json.dumps(api_info, ensure_ascii=False)
        return self._search(query, self._case_texts, self._cases, n_results)

    def search_patterns(self, api_info: dict, n_results: int = 4) -> list[str]:
        query = json.dumps(api_info, ensure_ascii=False)
        results = self._search(query, self._patterns, self._patterns, n_results)
        return results if results else self._patterns[:n_results]

    def search_similar_endpoints(self, api_info: dict, n_results: int = 2) -> list[dict]:
        query = json.dumps(api_info, ensure_ascii=False)
        return self._search(query, self._ep_texts, self._endpoints, n_results)


# ── 全局单例 ────────────────────────────────────────

_kb: Optional[KnowledgeBase] = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
