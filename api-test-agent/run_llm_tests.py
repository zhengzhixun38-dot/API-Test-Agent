"""
LLM 驱动的全链路测试脚本 (A+B)
解析 OpenAPI → LLM 生成用例 → 生成 pytest → 执行 → 失败分析
"""
import sys
import os
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format="  %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from app.tools.openapi_parser import parse_openapi
from app.tools.test_file_writer import write_test_file
from app.tools.pytest_runner import run_pytest_all
from app.services.testcase_service import generate_for_endpoint, get_case_type_stats
from app.agents.report_agent import analyze_all_failures
from app.config import settings
from openai import OpenAI


def main():
    print("=" * 60)
    print("  API Test Agent - LLM-Driven Full Pipeline (A+B)")
    print("=" * 60)

    # ═══ 1. 检查配置 ═══
    print("\n[Config]")
    print(f"  Model:  {settings.MODEL_NAME}")
    print(f"  Base:   {settings.BASE_URL}")
    print(f"  Target: {settings.TEST_BASE_URL}")
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-api-key-here":
        print("\n  [!] WARNING: API Key not set in .env")
        print("  Will use hand-written test cases as fallback.\n")
        use_llm = False
    else:
        print(f"  Key:    {settings.OPENAI_API_KEY[:8]}...****")
        use_llm = True

    # ═══ 2. 解析 OpenAPI ═══
    print("\n[1/5] Parsing openapi.json ...")
    endpoints = parse_openapi("openapi.json")
    print(f"       {len(endpoints)} endpoints found")

    # ═══ 3. 生成测试用例 ═══
    print("\n[2/5] Generating test cases ...")
    all_cases = {}
    total_cases = 0

    for ep in endpoints:
        key = f"{ep['method']} {ep['path']}"

        if use_llm:
            print(f"       Calling LLM for {key} ...")
            try:
                cases = generate_for_endpoint(ep)
            except Exception as e:
                print(f"       [!] LLM failed for {key}: {e}")
                print(f"       Using fallback: empty list")
                cases = []
        else:
            # 兜底：用 run_all_tests.py 的手写用例
            try:
                from run_all_tests import TEST_CASES
                cases = TEST_CASES.get(key, [])
                print(f"       Using hand-written cases for {key}")
            except ImportError:
                cases = []
                print(f"       No test cases for {key}")

        all_cases[key] = cases
        total_cases += len(cases)

        if cases and "error" not in cases[0]:
            stats = get_case_type_stats(cases)
            parts = []
            for ct, cnt in stats.items():
                if ct != "total" and cnt > 0:
                    parts.append(f"{ct}:{cnt}")
            print(f"         {len(cases)} cases ({', '.join(parts)})")
        else:
            print(f"         {len(cases)} cases (may have errors)")

    # ═══ 4. 生成 pytest 脚本 ═══
    print("\n[3/5] Generating pytest scripts ...")
    for ep in endpoints:
        key = f"{ep['method']} {ep['path']}"
        cases = all_cases.get(key, [])
        # 过滤掉错误用例
        valid_cases = [c for c in cases if "error" not in c]
        if valid_cases:
            fp = write_test_file(ep, valid_cases)
            print(f"       {fp}")

    # ═══ 5. 执行测试 ═══
    print("\n[4/5] Executing tests ...")
    start = time.time()
    exec_result = run_pytest_all("generated_tests")
    elapsed = time.time() - start

    summary = exec_result.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    pass_rate = round(passed / total * 100, 1) if total > 0 else 0

    print(f"       Total: {total}  Passed: {passed}  Failed: {failed}  Rate: {pass_rate}%  Time: {elapsed:.1f}s")

    # ═══ 6. 失败分析 (B) ═══
    print("\n[5/5] Failure analysis ...")
    if failed == 0:
        print("       All tests passed! No analysis needed.")
    elif not use_llm:
        print("       Skipped: API Key not configured.")
    else:
        # 提取失败信息
        failures = _extract_failures_from_report(exec_result, endpoints, all_cases)
        if failures:
            print(f"       Analyzing {len(failures)} failure(s) with LLM ...")
            failure_analysis_results = []
            try:
                analysis_results = analyze_all_failures(failures, settings)
                failure_analysis_results = analysis_results
                for ar in analysis_results:
                    a = ar.get("analysis", {})
                    print(f"\n       --- {ar.get('case_name', '?')} ---")
                    print(f"       Type:     {a.get('failure_type', '?')}")
                    print(f"       Root:     {a.get('root_cause', '?')}")
                    print(f"       Severity: {a.get('severity', '?')}")
                    for s in a.get("suggestions", []):
                        print(f"       Suggestion: {s}")
            except Exception as e:
                print(f"       Analysis failed: {e}")
        else:
            print("       Could not extract failure details.")

    # ═══ 6. 自修正（第二轮）═══
    round2_pass_rate = None
    if failed > 0 and use_llm and failure_analysis_results:
        print("\n[6/6] Self-correction round ...")
        corrected = _self_correct(endpoints, all_cases, failure_analysis_results, settings)

        # 重新生成脚本
        for ep in endpoints:
            key = f"{ep['method']} {ep['path']}"
            cases = corrected.get(key, all_cases.get(key, []))
            valid_cases = [c for c in cases if "error" not in c]
            if valid_cases:
                write_test_file(ep, valid_cases)

        # 重新执行
        exec2 = run_pytest_all("generated_tests")
        s2 = exec2.get("summary", {})
        t2 = s2.get("total", 0)
        p2 = s2.get("passed", 0)
        f2 = s2.get("failed", 0)
        round2_pass_rate = round(p2 / t2 * 100, 1) if t2 > 0 else 0
        print(f"       Round 2: {p2}/{t2} passed ({round2_pass_rate}%)")

        total = t2
        passed = p2
        failed = f2
        pass_rate = round2_pass_rate

    # ═══ Final Report ═══
    print()
    print("=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    print(f"  Endpoints:     {len(endpoints)}")
    print(f"  Total Cases:   {total}")
    print(f"  Passed:        {passed}")
    print(f"  Failed:        {failed}")
    print(f"  Pass Rate:     {pass_rate}%")
    print(f"  LLM Generated: {'Yes' if use_llm else 'No (hand-written)'}")
    if round2_pass_rate is not None:
        print(f"  Self-Correct:  Round 1 -> Round 2 ({round2_pass_rate}%)")
    print("=" * 60)

    return pass_rate


def _extract_failures_from_report(exec_result, endpoints, all_cases):
    """从执行报告中提取失败用例"""
    json_report = exec_result.get("json_report", {})
    failures = []

    for test in json_report.get("tests", []):
        if test.get("outcome") != "failed":
            continue
        nodeid = test.get("nodeid", "")
        call = test.get("call", {})
        longrepr = call.get("longrepr", "")

        # 尝试匹配端点和用例
        matched_ep = endpoints[0] if endpoints else {}
        matched_case = {"case_name": nodeid.split("::")[-1]}

        for ep in endpoints:
            ep_file = f"test_{ep['method'].lower()}_{ep['path'].strip('/').replace('/', '_').replace('-', '_')}"
            if ep_file in nodeid:
                matched_ep = ep
                break

        failures.append({
            "endpoint": matched_ep,
            "test_case": matched_case,
            "error": longrepr,
        })

    return failures


def _self_correct(endpoints, all_cases, analysis_results, settings):
    """将失败用例分析结果反馈给 LLM，让其修正用例"""
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.BASE_URL)

    # 汇总所有失败信息
    fail_summary = []
    for ar in analysis_results:
        a = ar.get("analysis", {})
        fail_summary.append({
            "endpoint": ar.get("endpoint_key", ""),
            "case_name": ar.get("case_name", ""),
            "root_cause": a.get("root_cause", ""),
            "suggestions": a.get("suggestions", []),
        })

    prompt = f"""你是测试工程师，请根据失败分析修正测试用例。

## 原始接口列表
{json.dumps([{ "path": ep["path"], "method": ep["method"] } for ep in endpoints], ensure_ascii=False, indent=2)}

## 失败分析
{json.dumps(fail_summary, ensure_ascii=False, indent=2)}

## 原始用例
{json.dumps({k: v for k, v in all_cases.items()}, ensure_ascii=False, indent=2)}

## 修正要求
1. 根据失败分析中的根因和建议，修正每个失败用例
2. 输出完整的新用例 JSON（只输出 JSON）
3. 输出格式: {{"POST /api/xxx": [修正后的用例数组], ...}}
4. 每个用例结构: {{"case_name":"...","case_type":"...","request_data":{{...}},"headers":{{...}},"expected_status":...,"assert_rules":{{...}}}}
"""

    response = client.chat.completions.create(
        model=settings.MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    raw = response.choices[0].message.content or ""

    # 解析修正后的用例
    from app.agents.testcase_agent import _extract_json_array
    json_str = _extract_json_array(raw) or raw
    try:
        corrected = json.loads(json_str)
        if isinstance(corrected, dict):
            return corrected
    except json.JSONDecodeError:
        pass

    # 兜底：返回原始用例
    return all_cases


if __name__ == "__main__":
    main()
