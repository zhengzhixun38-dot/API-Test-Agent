"""
测试用例服务 (V2)
调用 LLM Agent 生成测试用例，含增强解析和校验
"""
import json
import re
import logging
from app.agents.testcase_agent import generate_testcases, _extract_json_array
from app.config import settings

logger = logging.getLogger(__name__)

VALID_CASE_TYPES = {"normal", "missing_param", "invalid_type", "boundary", "auth_error"}


def generate_for_endpoint(api_info: dict) -> list[dict]:
    """
    为单个接口生成测试用例
    """
    api_json_str = json.dumps(api_info, ensure_ascii=False, indent=2)
    raw_output = generate_testcases(api_json_str, settings)
    return _parse_and_validate(raw_output)


def generate_for_endpoints(endpoints: list[dict]) -> dict[str, list[dict]]:
    """
    为多个接口生成测试用例

    Returns:
        {"POST /api/user/login": [case1, ...], ...}
    """
    result = {}
    for ep in endpoints:
        key = f"{ep['method']} {ep['path']}"
        logger.info("Generating testcases for: %s", key)
        result[key] = generate_for_endpoint(ep)
    return result


def _parse_and_validate(raw: str) -> list[dict]:
    """
    解析 LLM 输出的 JSON，做全量校验和自动修复
    """
    json_str = _extract_json_array(raw) or raw
    json_str = json_str.strip()

    try:
        cases = json.loads(json_str)
    except json.JSONDecodeError:
        # 尝试修复常见问题: 尾部逗号、单引号
        fixed = json_str.replace("'", '"')
        fixed = re.sub(r",\s*\]", "]", fixed)
        fixed = re.sub(r",\s*}", "}", fixed)
        try:
            cases = json.loads(fixed)
        except json.JSONDecodeError:
            return [{"error": "LLM输出无法解析为JSON", "raw": raw[:500]}]

    if not isinstance(cases, list):
        return [{"error": "LLM输出不是JSON数组", "raw": raw[:500]}]

    # 逐条校验 + 补全
    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            cases[i] = {"case_name": f"test_case_{i}"}
            case = cases[i]

        if "case_name" not in case or not case["case_name"]:
            case["case_name"] = f"test_case_{i}"

        if "case_type" not in case or case["case_type"] not in VALID_CASE_TYPES:
            case["case_type"] = "normal"

        if "request_data" not in case:
            case["request_data"] = {}

        if "expected_status" not in case:
            case["expected_status"] = 200

        if "assert_rules" not in case:
            case["assert_rules"] = {}

        # 如果是 2xx 成功，默认加 contains_fields
        if case["expected_status"] == 200 and not case["assert_rules"]:
            case["assert_rules"] = {"contains_fields": ["code"]}

    return cases


def get_case_type_stats(cases: list[dict]) -> dict:
    """统计各类型用例数量"""
    stats = {t: 0 for t in VALID_CASE_TYPES}
    for c in cases:
        ct = c.get("case_type", "normal")
        if ct in stats:
            stats[ct] += 1
    stats["total"] = len(cases)
    return stats
