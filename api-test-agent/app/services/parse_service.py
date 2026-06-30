"""
解析服务 — 调用 openapi_parser，按文件名或内容解析 OpenAPI 文档
"""
from app.tools.openapi_parser import parse_openapi, _build_body_params, _build_params, _build_responses


def parse_by_file(file_path: str) -> list[dict]:
    """根据文件路径解析 OpenAPI 文档"""
    return parse_openapi(file_path)


def parse_by_content(content: dict) -> list[dict]:
    """直接解析 OpenAPI JSON/dict 内容"""
    endpoints = []
    for path, methods in content.get("paths", {}).items():
        for method, detail in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue

            endpoints.append({
                "path": path,
                "method": method.upper(),
                "summary": detail.get("summary", ""),
                "request_body": _build_body_params(detail),
                "query_params": _build_params(detail, "query"),
                "path_params": _build_params(detail, "path"),
                "headers": _build_params(detail, "header"),
                "responses": _build_responses(detail),
            })
    return endpoints
