"""执行路由 — 生成脚本 + 执行 + 入库 + 分析"""
import time
import logging
from fastapi import APIRouter, Request, Query
from app.services.execute_service import generate_and_run
from app.agents.report_agent import analyze_all_failures
from app.db import save_execution
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["execute"])


@router.post("/execute")
def execute_tests(request: Request, analyze: bool = Query(default=True)):
    test_cases_map = getattr(request.app.state, "test_cases", None)
    endpoints = getattr(request.app.state, "current_endpoints", None)

    if not test_cases_map or not endpoints:
        return {"code": 400, "message": "请先生成测试用例"}

    start = time.time()
    results = []
    all_failures = []
    total_passed = 0
    total_failed = 0

    for ep in endpoints:
        key = f"{ep['method']} {ep['path']}"
        cases = test_cases_map.get(key, [])
        if not cases:
            continue

        result = generate_and_run(ep, cases)
        summary = result["execution"].get("summary", {})
        total_passed += summary.get("passed", 0)
        total_failed += summary.get("failed", 0)

        results.append({
            "key": key,
            "file_path": result["file_path"],
            "cases_count": result["test_cases_count"],
            "summary": summary,
            "stdout": result["execution"].get("stdout", ""),
            "stderr": result["execution"].get("stderr", ""),
            "failures": result.get("failures", []),
        })
        all_failures.extend(result.get("failures", []))

    total = total_passed + total_failed
    pass_rate = round(total_passed / total * 100, 1) if total > 0 else 0
    elapsed = time.time() - start

    # 失败分析
    failure_analysis = None
    if analyze and all_failures:
        try:
            failure_analysis = analyze_all_failures(all_failures, settings)
        except Exception as e:
            logger.error("Failure analysis failed: %s", e)
            failure_analysis = [{"error": str(e)}]

    # 入库
    project_id = getattr(request.app.state, "project_id", 1)
    save_execution(
        project_id=project_id,
        total=total, passed=total_passed, failed=total_failed,
        pass_rate=pass_rate, duration=round(elapsed, 2),
        is_llm=True,
        stdout="\n".join(r.get("stdout", "") for r in results),
        analysis=failure_analysis,
    )

    last_results = {
        "results": results,
        "total": total,
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": pass_rate,
        "duration": round(elapsed, 2),
        "failure_analysis": failure_analysis,
    }
    request.app.state.last_results = last_results

    return {
        "code": 0,
        "message": "执行完成",
        "data": last_results,
    }
