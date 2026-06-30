"""
RAG 对比验证脚本
A: 原始 LLM 生成  vs  B: RAG 增强生成
对比通过率，验证 RAG 效果
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))

from app.tools.openapi_parser import parse_openapi
from app.tools.test_file_writer import write_test_file
from app.tools.pytest_runner import run_pytest_all
from app.services.testcase_service import _parse_and_validate, get_case_type_stats
from app.agents.testcase_agent import generate_testcases as generate_baseline
from app.agents.testcase_agent_rag import generate_with_rag
from app.rag.knowledge_base import get_kb
from app.config import settings
from run_all_tests import TEST_CASES


def run_round(endpoints, mode="baseline"):
    """运行一轮测试，返回通过率"""
    all_cases = {}
    total_cases = 0
    label = "RAG Enhanced" if mode == "rag" else "Baseline (No RAG)"

    for ep in endpoints:
        key = f"{ep['method']} {ep['path']}"
        print(f"  [{label}] Generating for {key}...")

        if mode == "rag":
            raw = generate_with_rag(ep, settings)
        else:
            api_json = json.dumps(ep, ensure_ascii=False, indent=2)
            raw = generate_baseline(api_json, settings)

        cases = _parse_and_validate(raw)
        valid = [c for c in cases if "error" not in c]
        all_cases[key] = valid
        total_cases += len(valid)

    # 生成脚本
    for ep in endpoints:
        key = f"{ep['method']} {ep['path']}"
        cases = all_cases.get(key, [])
        if cases:
            write_test_file(ep, cases)

    # 执行
    result = run_pytest_all("generated_tests")
    s = result.get("summary", {})
    total = s.get("total", 0)
    passed = s.get("passed", 0)
    failed = s.get("failed", 0)
    rate = round(passed / total * 100, 1) if total > 0 else 0

    return {
        "total": total, "passed": passed, "failed": failed,
        "pass_rate": rate, "total_cases": total_cases,
    }


def main():
    print("=" * 60)
    print("  RAG A/B Comparison")
    print("  Baseline vs RAG-Enhanced Test Case Generation")
    print("=" * 60)

    print("\n[0] Loading knowledge base...")
    kb = get_kb()
    endpoints = parse_openapi("openapi.json")

    # 先用一份测试确保 kb 已构建
    test_retrieval = kb.search_similar_cases(endpoints[0], n_results=1)
    if not test_retrieval:
        print("    Knowledge base empty, building from hand-written cases...")
        from run_all_tests import TEST_CASES
        kb.build_from_handwritten(endpoints, TEST_CASES)
    print("    Ready!")

    # ═══ Round A: Baseline ═══
    print("\n[1] Round A: Baseline (no RAG)")
    print("-" * 40)
    r1 = run_round(endpoints, mode="baseline")

    # ═══ Round B: RAG Enhanced ═══
    print("\n[2] Round B: RAG Enhanced")
    print("-" * 40)
    r2 = run_round(endpoints, mode="rag")

    # ═══ Comparison ═══
    print()
    print("=" * 60)
    print("  COMPARISON")
    print("=" * 60)
    print(f"  {'Metric':30s} {'No RAG':>10s} {'RAG':>10s} {'Delta':>10s}")
    print(f"  {'-'*30} {'-'*10} {'-'*10} {'-'*10}")

    for metric in ["total", "passed", "failed"]:
        v1 = r1[metric]
        v2 = r2[metric]
        delta = v2 - v1
        arrow = "UP" if delta > 0 else "DOWN" if delta < 0 else "-"
        print(f"  {metric.capitalize():30s} {str(v1):>10s} {str(v2):>10s} {delta:+d} {arrow}")

    v1_rate = r1["pass_rate"]
    v2_rate = r2["pass_rate"]
    delta_rate = round(v2_rate - v1_rate, 1)
    print(f"  {'Pass Rate':30s} {str(v1_rate)+'%':>10s} {str(v2_rate)+'%':>10s} {delta_rate:+.1f}%")

    print()
    if delta_rate > 0:
        print(f"  [RESULT] RAG improved pass rate by {delta_rate:.1f}%!")
    elif delta_rate == 0:
        print(f"  [RESULT] Same pass rate. More runs needed.")
    else:
        print(f"  [RESULT] Baseline was better. Check RAG prompt tuning.")

    print("=" * 60)
    return v2_rate


if __name__ == "__main__":
    main()
