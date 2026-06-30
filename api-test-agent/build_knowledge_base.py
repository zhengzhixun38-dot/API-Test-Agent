"""
构建 RAG 知识库
从手写用例（100% 通过率）提取测试模式，索引到向量数据库
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.tools.openapi_parser import parse_openapi
from app.rag.knowledge_base import get_kb, KnowledgeBase
from run_all_tests import TEST_CASES

print("=" * 50)
print("  Building RAG Knowledge Base")
print("=" * 50)

# 1. 解析接口
print("\n[1] Parsing OpenAPI...")
endpoints = parse_openapi("openapi.json")
print(f"    {len(endpoints)} endpoints")

# 2. 构建知识库
print("\n[2] Indexing hand-written test cases...")
kb = KnowledgeBase()
kb.build_from_handwritten(endpoints, TEST_CASES)
print("    Done!")

# 3. 验证检索
print("\n[3] Testing retrieval...")
login_ep = endpoints[0]
similar = kb.search_similar_cases(login_ep, n_results=3)
patterns = kb.search_patterns(login_ep, n_results=3)
print(f"    Similar cases found: {len(similar)}")
print(f"    Patterns found: {len(patterns)}")
for p in patterns:
    print(f"      - {p[:80]}...")

print("\n[4] Knowledge base ready!")
print(f"    Path: chroma_db/")
print("=" * 50)
