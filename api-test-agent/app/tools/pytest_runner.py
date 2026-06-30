"""
Pytest 执行器 (V2 - 支持流式回调)
通过子进程调用 pytest，返回结构化的执行结果
新增: run_pytest_stream 逐行回调，供 WebSocket 使用
"""
import subprocess
import os
import json
from typing import Any, Callable


def _run(args: list[str], json_path: str) -> dict:
    """统一的子进程调用"""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "summary": _parse_summary_from_stdout(result.stdout or ""),
        "json_path": json_path,
    }


def _try_load_json_report(output: dict) -> dict:
    """尝试加载 pytest-json-report 的 JSON 报告"""
    json_path = output.get("json_path", "")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            output["json_report"] = report
            output["summary"] = _extract_summary(report)
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    output.pop("json_path", None)
    return output


def run_pytest(test_file_path: str, extra_args: list[str] | None = None) -> dict:
    """执行单个测试文件"""
    args = ["pytest", test_file_path, "-v"]
    json_path = test_file_path + ".result.json"
    args += ["--json-report", f"--json-report-file={json_path}"]
    if extra_args:
        args.extend(extra_args)

    output = _run(args, json_path)
    output["file_path"] = test_file_path
    return _try_load_json_report(output)


def run_pytest_batch(test_files: list[str], extra_args: list[str] | None = None) -> list[dict]:
    """批量执行多个测试文件"""
    results = []
    for file_path in test_files:
        results.append(run_pytest(file_path, extra_args))
    return results


def run_pytest_all(test_dir: str, extra_args: list[str] | None = None) -> dict:
    """执行整个目录下的所有测试文件"""
    args = ["pytest", test_dir, "-v"]
    json_path = os.path.join(test_dir, "test_results.json")
    args += ["--json-report", f"--json-report-file={json_path}"]
    if extra_args:
        args.extend(extra_args)

    output = _run(args, json_path)
    output["file_path"] = test_dir
    return _try_load_json_report(output)


def _extract_summary(report: dict) -> dict:
    """从 pytest-json-report 报告中提取汇总信息"""
    summary = report.get("summary", {})
    return {
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "skipped": summary.get("skipped", 0),
        "error": summary.get("error", 0),
        "duration": summary.get("duration", 0),
    }


def _parse_summary_from_stdout(stdout: str) -> dict:
    """从标准输出中解析 pytest 汇总行，作为无 JSON 报告时的兜底"""
    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "error": 0,
        "duration": 0,
    }
    if not stdout:
        return summary

    for line in stdout.splitlines():
        line = line.strip().strip("=").strip()
        if " in " not in line:
            continue
        parts = line.rsplit(" in ", 1)
        if len(parts) != 2:
            continue
        try:
            summary["duration"] = float(parts[1].rstrip("s"))
        except ValueError:
            pass

        counts = parts[0]
        for chunk in counts.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            tokens = chunk.split()
            if len(tokens) < 2:
                continue
            try:
                num = int(tokens[0])
            except ValueError:
                continue
            label = tokens[1]
            if "passed" in label:
                summary["passed"] = num
            elif "failed" in label:
                summary["failed"] = num
            elif "skipped" in label:
                summary["skipped"] = num
            elif "error" in label:
                summary["error"] = num
        summary["total"] = summary["passed"] + summary["failed"] + summary["skipped"] + summary["error"]
    return summary


def run_pytest_stream(
    test_dir: str,
    on_line: Callable[[str], None],
    extra_args: list[str] | None = None,
) -> dict:
    """
    流式执行 pytest，每行输出通过回调实时推送

    Args:
        test_dir: 测试文件目录
        on_line: 每行输出的回调函数
        extra_args: 额外 pytest 参数

    Returns:
        同 run_pytest_all 的汇总结果
    """
    args = ["pytest", test_dir, "-v", "--tb=short"]
    json_path = os.path.join(test_dir, "test_results.json")
    args += ["--json-report", f"--json-report-file={json_path}"]
    if extra_args:
        args.extend(extra_args)

    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout_lines = []
    if process.stdout:
        for line in process.stdout:
            line = line.rstrip("\n")
            stdout_lines.append(line)
            on_line(line)

    returncode = process.wait()
    full_stdout = "\n".join(stdout_lines)

    output = {
        "returncode": returncode,
        "stdout": full_stdout,
        "stderr": "",
        "file_path": test_dir,
        "summary": _parse_summary_from_stdout(full_stdout),
    }

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            output["json_report"] = report
            output["summary"] = _extract_summary(report)
        except (json.JSONDecodeError, KeyError):
            pass

    return output
