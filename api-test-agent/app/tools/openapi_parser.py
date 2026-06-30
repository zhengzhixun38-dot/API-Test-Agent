"""
OpenAPI 规范解析器 (V2)
将 OpenAPI 3.x 文档解析为统一接口信息格式，区分参数位置：
  request_body  — JSON 请求体参数
  query_params  — URL 查询参数 (?key=value)
  path_params   — 路径参数 (/api/user/{id})
  headers       — 请求头参数 (Authorization 等)
"""
import json
import yaml
from typing import Any


def parse_openapi(file_path: str) -> list[dict]:
    """解析 OpenAPI 文件，返回统一格式的接口列表"""
    raw = _load_file(file_path)
    endpoints = []

    for path, methods in raw.get("paths", {}).items():
        for method, detail in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue

            api_info = {
                "path": path,
                "method": method.upper(),
                "summary": detail.get("summary", ""),
                "request_body": _build_body_params(detail),
                "query_params": _build_params(detail, "query"),
                "path_params": _build_params(detail, "path"),
                "headers": _build_params(detail, "header"),
                "responses": _build_responses(detail),
            }
            endpoints.append(api_info)

    return endpoints


def _load_file(file_path: str) -> dict:
    """加载 JSON 或 YAML 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(f)
        return json.load(f)


def _build_body_params(detail: dict) -> dict[str, Any]:
    """从 requestBody 中提取 JSON body 参数"""
    result = {}
    request_body = detail.get("requestBody", {})
    content = request_body.get("content", {}).get("application/json", {})
    schema = content.get("schema", {})
    required_fields = schema.get("required", [])

    for prop_name, prop_info in schema.get("properties", {}).items():
        result[prop_name] = {
            "type": prop_info.get("type", "string"),
            "required": prop_name in required_fields,
            "example": prop_info.get("example", ""),
            "description": prop_info.get("description", ""),
        }
    return result


def _build_params(detail: dict, param_in: str) -> dict[str, Any]:
    """按位置提取 parameters"""
    result = {}
    for param in detail.get("parameters", []):
        if param.get("in") == param_in:
            name = param.get("name", "")
            result[name] = {
                "type": param.get("schema", {}).get("type", "string"),
                "required": param.get("required", False),
                "example": param.get("example", param.get("schema", {}).get("example", "")),
                "description": param.get("description", ""),
            }
    return result


def _build_responses(detail: dict) -> dict[str, str]:
    """提取响应状态码和描述"""
    result = {}
    for status_code, resp in detail.get("responses", {}).items():
        result[status_code] = resp.get("description", "")
    return result
