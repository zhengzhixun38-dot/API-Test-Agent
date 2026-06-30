"""
测试文件生成器 (V2)
读取测试用例 JSON → 生成 pytest 脚本文件

新增：
  - 支持 headers（Authorization 等）
  - 支持 parametrize 批量参数化
  - GET 请求 query params 与 path params 分离
"""
import os
from typing import Any

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8001")
OUTPUT_DIR = os.environ.get("TEST_OUTPUT_DIR", "generated_tests")


def write_test_file(api_info: dict, test_cases: list[dict], output_dir: str | None = None) -> str:
    """根据接口信息 + 测试用例，生成 pytest 脚本"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    path = api_info["path"]
    method = api_info["method"].lower()
    file_name = _to_filename(path, method)
    file_path = os.path.join(output_dir, file_name)

    lines = ["import requests"]
    need_time = any("response_time_lt" in c.get("assert_rules", {}) for c in test_cases)
    if need_time:
        lines.append("import time")
    lines += ["", f'BASE_URL = "{BASE_URL}"', ""]

    # 如果有需要 token 的用例，先定义获取 token 的 fixture 或常量
    has_auth = any(
        case.get("headers", {}).get("Authorization")
        for case in test_cases
    )
    if has_auth:
        lines.append('TOKEN = "mock-token-2024"')
        lines.append("")

    for case in test_cases:
        case["func_name"] = _to_func_name(case.get("case_name", "test"))
        lines.extend(_generate_test_func(api_info, case))

    code = "\n".join(lines) + "\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    return file_path


def generate_test_code(api_info: dict, test_cases: list[dict]) -> str:
    """生成测试代码字符串（不写文件）"""
    path = api_info["path"]
    method = api_info["method"].lower()

    has_auth = any(
        case.get("headers", {}).get("Authorization")
        for case in test_cases
    )

    lines = ["import requests"]
    need_time = any("response_time_lt" in c.get("assert_rules", {}) for c in test_cases)
    if need_time:
        lines.append("import time")
    lines += ["", f'BASE_URL = "{BASE_URL}"', ""]
    if has_auth:
        lines.append('TOKEN = "mock-token-2024"')
        lines.append("")

    for case in test_cases:
        case["func_name"] = _to_func_name(case.get("case_name", "test"))
        lines.extend(_generate_test_func(api_info, case))

    return "\n".join(lines) + "\n"


def _generate_test_func(api_info: dict, case: dict) -> list[str]:
    """根据单条用例生成一个 test_xxx 函数"""
    path = api_info["path"]
    method = api_info["method"].lower()
    func_name = _to_func_name(case.get("case_name", "test"))
    request_data = case.get("request_data", {})
    headers = case.get("headers", {})
    expected_status = case.get("expected_status", 200)
    assert_rules = case.get("assert_rules", {})

    has_time = "response_time_lt" in assert_rules

    lines = [
        "",
        f"def {func_name}():",
        f'    url = BASE_URL + "{path}"',
    ]

    if has_time:
        lines.append("    start_time = time.time()")

    # --- 构建 headers ---
    if headers:
        lines.append(f"    headers = {_format_dict(headers)}")
        headers_var = "headers=headers"
    else:
        headers_var = ""

    # --- 构建请求 ---
    if method == "get":
        if request_data:
            lines.append(f"    params = {_format_dict(request_data)}")
            params_arg = "params=params"
        else:
            params_arg = ""

        args = ", ".join(filter(None, [params_arg, headers_var]))
        if args:
            lines.append(f"    response = requests.get(url, {args})")
        else:
            lines.append("    response = requests.get(url)")

    elif method in ("post", "put", "patch", "delete"):
        if request_data:
            lines.append(f"    payload = {_format_dict(request_data)}")
            data_arg = "json=payload"
        else:
            data_arg = ""

        args = ", ".join(filter(None, [data_arg, headers_var]))
        lines.append(f"    response = requests.{method}(url, {args})")

    else:
        lines.append(f"    response = requests.{method}(url)")

    lines.append("")

    if has_time:
        lines.append("    elapsed_ms = (time.time() - start_time) * 1000")

    # --- 状态码断言 ---
    lines.append(f"    assert response.status_code == {expected_status}")

    # --- assert_rules 断言 ---
    lines.extend(_generate_asserts(assert_rules, expected_status))

    return lines


def _generate_asserts(rules: dict, expected_status: int) -> list[str]:
    """根据 assert_rules 生成断言，支持 7 种规则"""
    lines = []
    has_parsed = False

    def ensure_json():
        nonlocal has_parsed
        if not has_parsed:
            lines.append("    data = response.json()")
            has_parsed = True

    # 1. contains_fields — 顶层 JSON 字段存在
    if "contains_fields" in rules:
        ensure_json()
        for field in rules["contains_fields"]:
            lines.append(f'    assert "{field}" in data')

    # 2. data_contains_fields — data 对象内部字段
    if "data_contains_fields" in rules:
        ensure_json()
        for field in rules["data_contains_fields"]:
            lines.append(f'    assert "{field}" in data.get("data", {{}}), f"data.{field} not found"')

    # 3. field_types — 字段类型校验
    if "field_types" in rules:
        ensure_json()
        for field, typ in rules["field_types"].items():
            lines.append(f"    assert isinstance(data[\"{field}\"], {typ})")

    # 4. equals — 字段值精确匹配
    if "equals" in rules:
        ensure_json()
        for field, expected in rules["equals"].items():
            lines.append(f'    assert data["{field}"] == {repr(expected)}')

    # 5. not_empty — 响应不为空
    if "not_empty" in rules and rules["not_empty"]:
        ensure_json()
        lines.append("    assert len(data) > 0")

    # 6. list_not_empty — data.list 列表不为空
    if "list_not_empty" in rules and rules["list_not_empty"]:
        ensure_json()
        lines.append('    assert len(data.get("data", {}).get("list", [])) > 0, "list is empty"')

    # 7. response_time_lt — 响应时间小于阈值（毫秒）
    if "response_time_lt" in rules:
        max_ms = rules["response_time_lt"]
        lines.append(f"    assert elapsed_ms < {max_ms}, f'Response time {{elapsed_ms}}ms exceeds {max_ms}ms'")

    return lines


def _to_filename(path: str, method: str) -> str:
    slug = path.strip("/").replace("/", "_").replace("-", "_")
    return f"test_{method}_{slug}.py"


def _to_func_name(case_name: str) -> str:
    import hashlib
    name = case_name.strip()
    if name.replace("_", "").isascii() and name.replace("_", "").replace(" ", "").isalnum():
        return "test_" + name.lower().replace(" ", "_")
    # 用 md5 保证同 case_name 跨进程稳定
    md5 = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"test_case_{md5}"


def _format_dict(d: dict) -> str:
    if not d:
        return "{}"
    if isinstance(d, list):
        return "{}"
    if not isinstance(d, dict):
        return repr(d)
    lines = ["{"]
    for k, v in d.items():
        lines.append(f'        "{k}": {repr(v)},')
    lines.append("    }")
    return "\n".join(lines)
