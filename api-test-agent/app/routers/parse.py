"""解析路由 — 解析 OpenAPI + 入库"""
from fastapi import APIRouter, Request
from app.services.parse_service import parse_by_content
from app.db import save_endpoints

router = APIRouter(prefix="/api", tags=["parse"])


@router.post("/parse")
def parse_openapi(request: Request):
    raw = getattr(request.app.state, "openapi_raw", None)
    if raw is None:
        return {"code": 400, "message": "请先上传 OpenAPI 文档"}

    endpoints = parse_by_content(raw)

    # 入库
    project_id = getattr(request.app.state, "project_id", 1)
    save_endpoints(project_id, endpoints)

    request.app.state.endpoints = endpoints

    return {
        "code": 0,
        "message": "解析完成",
        "data": {
            "endpoint_count": len(endpoints),
            "endpoints": endpoints,
        },
    }
