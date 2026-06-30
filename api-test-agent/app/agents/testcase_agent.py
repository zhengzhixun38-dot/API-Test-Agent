"""
测试用例生成 Agent (V2)
增强：多示例 few-shot、重试机制、鲁棒 JSON 解析
"""
import json
import re
import logging
from openai import OpenAI
from app.config import Settings

logger = logging.getLogger(__name__)

# ── Prompt 模板（含多类型 few-shot 示例）────────────────

TESTCASE_GENERATION_PROMPT = """你是一个资深接口测试工程师。
请根据下面的接口信息，设计全面的接口测试用例。

## 输出规则（严格遵守）
1. 只输出 JSON 数组，不要任何解释、注释或 markdown 标记
2. 所有值必须是 JSON 字面量（字符串、数字、布尔值、数组、对象）
3. 禁止使用任何代码表达式或函数调用（如 "x".repeat()、String.fromCharCode() 等）
4. 需要用超长字符串时，直接用引号包裹的字面量，如 "xxxxx...xxxxx"
5. 如果某个场景的值无法用 JSON 表达，用一个合理的示例值代替

## 覆盖要求
- case_type 只能是 normal、missing_param、invalid_type、boundary、auth_error
- 必须覆盖: normal(至少2个)、missing_param、invalid_type、boundary、auth_error
- request_data 的值优先使用接口文档中的 example
- expected_status 参考接口文档的 responses
- 鉴权信息用 headers 字段传递，如 "headers": {"Authorization": "Bearer mock-token-2024"}
- 参数校验失败(Pydantic/类型错误)返回 422，业务规则错误返回 400，鉴权失败返回 401，资源不存在返回 404
- 如果接口需要 token，所有 auth_error 类型用例必须在 headers 中包含 Authorization
- 错误响应的 assert_rules 使用 contains_fields: ["code", "message"]，不要用 "detail"
- 成功响应的 assert_rules 使用 contains_fields: ["code", "message", "data"]
- 可用断言类型（按场景选用）：
  * contains_fields: ["field1","field2"] — 顶层字段存在
  * data_contains_fields: ["token","username"] — data 内部字段存在（登录接口必用！）
  * list_not_empty: true — 列表型 data 不能为空（列表接口用）
  * response_time_lt: 500 — 响应时间小于指定毫秒（可选）
  * equals: {"code":0} — 字段精确值匹配

## Few-shot 示例

### 示例 1: POST 登录接口
输入:
```json
{
  "path": "/api/user/login",
  "method": "POST",
  "summary": "用户登录",
  "request_body": {
    "username": {"type": "string", "required": true, "example": "admin"},
    "password": {"type": "string", "required": true, "example": "123456"}
  },
  "responses": {"200": "登录成功", "401": "用户名或密码错误"}
}
```
输出:
```json
[
  {"case_name": "正常登录", "case_type": "normal", "request_data": {"username": "admin", "password": "123456"}, "expected_status": 200, "assert_rules": {"contains_fields": ["code", "message", "data"]}},
  {"case_name": "密码错误", "case_type": "auth_error", "request_data": {"username": "admin", "password": "wrong_pass"}, "expected_status": 401, "assert_rules": {"contains_fields": ["code", "message"]}},
  {"case_name": "用户名为空", "case_type": "missing_param", "request_data": {"username": "", "password": "123456"}, "expected_status": 422, "assert_rules": {"contains_fields": ["detail"]}},
  {"case_name": "密码为空", "case_type": "missing_param", "request_data": {"username": "admin", "password": ""}, "expected_status": 422, "assert_rules": {"contains_fields": ["detail"]}},
  {"case_name": "用户名含特殊字符", "case_type": "invalid_type", "request_data": {"username": "admin<script>", "password": "123456"}, "expected_status": 422, "assert_rules": {"contains_fields": ["detail"]}},
  {"case_name": "用户名仅2位", "case_type": "boundary", "request_data": {"username": "ab", "password": "123456"}, "expected_status": 422, "assert_rules": {"contains_fields": ["detail"]}},
  {"case_name": "密码仅5位", "case_type": "boundary", "request_data": {"username": "admin", "password": "12345"}, "expected_status": 422, "assert_rules": {"contains_fields": ["detail"]}}
]
```

### 示例 2: GET 查询接口
输入:
```json
{
  "path": "/api/product/list",
  "method": "GET",
  "summary": "商品列表",
  "request_body": {
    "page": {"type": "integer", "required": false, "example": 1},
    "page_size": {"type": "integer", "required": false, "example": 10}
  },
  "responses": {"200": "成功", "400": "参数错误"}
}
```
输出:
```json
[
  {"case_name": "默认分页", "case_type": "normal", "request_data": {}, "expected_status": 200, "assert_rules": {"contains_fields": ["code", "data"]}},
  {"case_name": "自定义分页", "case_type": "normal", "request_data": {"page": 2, "page_size": 20}, "expected_status": 200, "assert_rules": {"contains_fields": ["code", "data"]}},
  {"case_name": "page为0", "case_type": "boundary", "request_data": {"page": 0}, "expected_status": 400, "assert_rules": {"contains_fields": ["code", "message"]}},
  {"case_name": "page为负数", "case_type": "boundary", "request_data": {"page": -1}, "expected_status": 400, "assert_rules": {"contains_fields": ["code", "message"]}},
  {"case_name": "page_size为0", "case_type": "boundary", "request_data": {"page_size": 0}, "expected_status": 400, "assert_rules": {"contains_fields": ["code", "message"]}},
  {"case_name": "page_size超上限", "case_type": "boundary", "request_data": {"page_size": 101}, "expected_status": 400, "assert_rules": {"contains_fields": ["code", "message"]}}
]
```

## 接口信息
{api_info}

## 请输出（只输出 JSON 数组，不要任何其他内容）:"""

# ── 输出示例（兼容旧版引用）────────────────────────────

TESTCASE_OUTPUT_EXAMPLE = [
    {
        "case_name": "用户正常登录",
        "case_type": "normal",
        "request_data": {"username": "admin", "password": "123456"},
        "expected_status": 200,
        "assert_rules": {"contains_fields": ["code", "message", "data"]},
    },
    {
        "case_name": "用户名为空",
        "case_type": "missing_param",
        "request_data": {"username": "", "password": "123456"},
        "expected_status": 400,
        "assert_rules": {"contains_fields": ["code", "message"]},
    },
]


# ── LLM 调用（含重试）───────────────────────────────────

def generate_testcases(
    api_info_json: str,
    settings: Settings,
    max_retries: int = 3,
) -> str:
    """
    调用 LLM 生成测试用例，失败自动重试

    Args:
        api_info_json: 接口信息 JSON 字符串
        settings: 应用配置
        max_retries: 最多重试次数

    Returns:
        LLM 原始输出文本
    """
    prompt = TESTCASE_GENERATION_PROMPT.replace("{api_info}", api_info_json)

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.BASE_URL,
    )

    last_raw = ""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            raw = response.choices[0].message.content or ""
            last_raw = raw

            # 记录 token 用量
            usage = response.usage
            if usage:
                logger.info(
                    "LLM tokens: prompt=%d completion=%d total=%d",
                    usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
                )

            if _validate_raw_output(raw):
                return raw

            logger.warning(
                "LLM output validation failed, retry %d/%d (got %d chars)",
                attempt + 1, max_retries, len(raw),
            )

        except Exception as e:
            last_error = e
            logger.warning(
                "LLM call failed (attempt %d/%d): %s", attempt + 1, max_retries, e
            )

    # 所有重试用完，如果最后一次有内容就用它（让上层去 parse）
    if last_raw:
        logger.warning("Returning unvalidated raw output (%d chars)", len(last_raw))
        return last_raw

    if last_error:
        raise RuntimeError(f"LLM 调用失败，已重试 {max_retries} 次: {last_error}")
    return ""  # 不会到达


def _validate_raw_output(raw: str) -> bool:
    """校验 LLM 输出是否包含有效 JSON 数组"""
    if not raw or not raw.strip():
        return False
    # 尝试提取 JSON 数组
    json_str = _extract_json_array(raw)
    if not json_str:
        return False
    try:
        data = json.loads(json_str)
        return isinstance(data, list) and len(data) > 0
    except json.JSONDecodeError:
        return False


def _extract_json_array(text: str) -> str | None:
    """从文本中提取第一个 JSON 数组"""
    # 去掉 markdown 代码块
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    # 找到最外层 [ ... ]
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)
    return None
