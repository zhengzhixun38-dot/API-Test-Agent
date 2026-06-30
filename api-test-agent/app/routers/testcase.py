"""测试用例路由 — 生成用例 + 入库"""
from fastapi import APIRouter, Request
from app.services.testcase_service import generate_for_endpoints
from app.db import get_endpoints, save_test_cases

router = APIRouter(prefix="/api", tags=["testcase"])


@router.post("/testcase/generate")
def generate_testcases(request: Request):
    endpoints = getattr(request.app.state, "endpoints", None)
    if not endpoints:
        return {"code": 400, "message": "请先解析 OpenAPI 文档"}

    all_cases = generate_for_endpoints(endpoints)

    # 入库
    project_id = getattr(request.app.state, "project_id", 1)
    db_endpoints = get_endpoints(project_id)
    ep_map = {}
    for e in db_endpoints:
        ep_map[f"{e.method} {e.path}"] = e.id
    for key, cases in all_cases.items():
        ep_id = ep_map.get(key)
        if ep_id:
            save_test_cases(ep_id, cases, is_llm=True)

    request.app.state.test_cases = all_cases
    request.app.state.current_endpoints = endpoints

    total = sum(len(cases) for cases in all_cases.values())
    return {
        "code": 0,
        "message": "测试用例生成完成",
        "data": {
            "total_cases": total,
            "cases": all_cases,
        },
    }
