"""
执行服务 (V2)
生成 pytest 脚本 + 执行 + 可选失败分析
"""
import os
from app.tools.test_file_writer import write_test_file
from app.tools.pytest_runner import run_pytest, run_pytest_all
from app.config import settings


def generate_and_run(api_info: dict, test_cases: list[dict]) -> dict:
    """
    为单个接口生成测试脚本并执行

    Returns:
        {
            "file_path": str,
            "test_cases_count": int,
            "execution": {...},
            "failures": [...]     # 失败用例详情
        }
    """
    file_path = write_test_file(api_info, test_cases, output_dir=settings.OUTPUT_DIR)
    exec_result = run_pytest(file_path)

    # 提取失败用例详情
    failures = _extract_failures(api_info, test_cases, exec_result)

    return {
        "file_path": file_path,
        "test_cases_count": len(test_cases),
        "execution": exec_result,
        "failures": failures,
    }


def run_all_tests() -> dict:
    """执行 generated_tests 目录下所有测试"""
    test_dir = settings.OUTPUT_DIR
    if not os.path.isdir(test_dir):
        return {"error": f"目录不存在: {test_dir}"}
    return run_pytest_all(test_dir)


def _extract_failures(
    api_info: dict, test_cases: list[dict], exec_result: dict
) -> list[dict]:
    """
    从执行结果中提取失败用例的详细信息，
    供 report_agent 分析使用
    """
    failures = []
    stdout = exec_result.get("stdout", "")
    json_report = exec_result.get("json_report", {})

    # 方法1: 从 JSON report 提取
    if json_report:
        for test in json_report.get("tests", []):
            if test.get("outcome") == "failed":
                nodeid = test.get("nodeid", "")
                call = test.get("call", {})
                longrepr = call.get("longrepr", "")

                # 尝试匹配对应的用例
                matched_case = _match_test_case(nodeid, test_cases)

                failures.append({
                    "endpoint": api_info,
                    "test_case": matched_case,
                    "nodeid": nodeid,
                    "error": longrepr,
                })

    # 方法2: 从 stdout 兜底
    if not failures and "FAILED" in stdout:
        for line in stdout.splitlines():
            if "FAILED" in line and "::" in line:
                parts = line.split("::")
                nodeid = parts[-1].strip() if len(parts) > 1 else line.strip()
                failures.append({
                    "endpoint": api_info,
                    "test_case": {"case_name": nodeid},
                    "nodeid": nodeid,
                    "error": stdout,
                })

    return failures


def _match_test_case(nodeid: str, test_cases: list[dict]) -> dict:
    """根据 pytest nodeid 匹配对应的测试用例（通过 func_name 精确匹配）"""
    func_name = nodeid.split("::")[-1] if "::" in nodeid else nodeid
    for case in test_cases:
        if case.get("func_name") == func_name:
            return case
    return test_cases[0] if test_cases else {"case_name": func_name}
