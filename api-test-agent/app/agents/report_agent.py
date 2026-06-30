"""
报告分析 Agent (V1)
把失败用例 + 接口信息 + pytest 报错 交给 LLM，
输出根因分析和排查建议
"""
import json
import re
import logging
from openai import OpenAI
from app.config import Settings

logger = logging.getLogger(__name__)

# ── Prompt ─────────────────────────────────────────────

FAILURE_ANALYSIS_PROMPT = """你是一个资深测试开发工程师，负责分析自动化测试失败的原因。

## 背景信息

### 被测接口
```
{endpoint_info}
```

### 测试用例
```
{test_case}
```

### Pytest 报错信息
```
{pytest_error}
```

## 任务

请分析这个失败用例，按以下 JSON 格式输出（只输出 JSON，不要其他内容）:

```json
{{
  "failure_type": "断言失败 | 服务端异常 | 网络错误 | 超时 | 其他",
  "root_cause": "一句话描述根本原因",
  "detail": "详细分析（限200字内）",
  "possible_reasons": ["可能原因1", "可能原因2", "可能原因3"],
  "suggestions": ["排查建议1", "排查建议2"],
  "severity": "critical | major | minor"
}}
```

分析角度:
1. 预期状态码和实际状态码的差异说明了什么？
2. 是测试用例的预期写错了，还是被测接口的返回值不对？
3. 如果是服务端错误(500)，可能是哪一层的问题？
4. 如果是 4xx，是参数校验、鉴权还是业务规则触发？

## 输出:"""

# ── LLM 调用 ──────────────────────────────────────────

def analyze_failure(
    endpoint_info: dict,
    test_case: dict,
    pytest_error: str,
    settings: Settings,
) -> dict:
    """
    分析单个失败用例

    Args:
        endpoint_info: 接口元数据 {"path", "method", ...}
        test_case: 失败的测试用例
        pytest_error: pytest 的报错信息
        settings: 应用配置

    Returns:
        {"failure_type": "...", "root_cause": "...", "detail": "...",
         "possible_reasons": [...], "suggestions": [...], "severity": "..."}
    """
    prompt = FAILURE_ANALYSIS_PROMPT
    prompt = prompt.replace("{endpoint_info}", json.dumps(endpoint_info, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{test_case}", json.dumps(test_case, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{pytest_error}", pytest_error[:2000])

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.BASE_URL,
    )

    try:
        response = client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return _parse_analysis(response.choices[0].message.content or "")
    except Exception as e:
        logger.error("Failure analysis LLM call failed: %s", e)
        return _fallback_analysis(str(e))


def analyze_all_failures(
    failures: list[dict],
    settings: Settings,
) -> list[dict]:
    """
    批量分析所有失败用例

    Args:
        failures: [{"endpoint": {...}, "test_case": {...}, "error": "..."}, ...]
        settings: 应用配置

    Returns:
        [{"endpoint_key": "...", "case_name": "...", "analysis": {...}}, ...]
    """
    results = []
    for f in failures:
        analysis = analyze_failure(
            f["endpoint"], f["test_case"], f["error"], settings
        )
        results.append({
            "endpoint_key": f"{f['endpoint']['method']} {f['endpoint']['path']}",
            "case_name": f["test_case"].get("case_name", "unknown"),
            "analysis": analysis,
        })
    return results


def _parse_analysis(raw: str) -> dict:
    """解析 LLM 返回的分析 JSON"""
    # 去掉 markdown 代码块
    text = re.sub(r"```(?:json)?\s*", "", raw)
    text = re.sub(r"```\s*", "", text)

    # 找 JSON 对象
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 返回原始文本兜底
    return {
        "failure_type": "解析失败",
        "root_cause": raw[:200],
        "detail": raw[:500],
        "possible_reasons": [],
        "suggestions": [],
        "severity": "minor",
    }


def _fallback_analysis(error_msg: str) -> dict:
    """LLM 调用失败时的兜底分析"""
    return {
        "failure_type": "LLM 调用失败",
        "root_cause": f"分析 Agent 调用异常: {error_msg[:100]}",
        "detail": "请检查 API Key 配置或网络连接",
        "possible_reasons": ["API Key 未配置", "网络不通", "模型服务异常"],
        "suggestions": ["检查 .env 配置", "测试网络连通性"],
        "severity": "critical",
    }
