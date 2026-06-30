"""报告路由 — 查看历史报告"""
from fastapi import APIRouter, Request, Query
from app.db import list_executions, get_pass_rate_trend, list_projects

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report")
def get_report(request: Request):
    """获取最近一次执行结果"""
    last = getattr(request.app.state, "last_results", None)
    if last is None:
        return {"code": 400, "message": "暂无测试报告，请先执行测试"}
    return {"code": 0, "message": "success", "data": last}


@router.get("/report/history")
def get_history(project_id: int = Query(default=1), limit: int = Query(default=20)):
    """获取历史执行记录"""
    executions = list_executions(project_id, limit)
    return {
        "code": 0,
        "data": [
            {
                "id": e.id,
                "total": e.total,
                "passed": e.passed,
                "failed": e.failed,
                "pass_rate": e.pass_rate,
                "duration": e.duration,
                "is_llm": bool(e.is_llm_generated),
                "corrected": bool(e.is_self_corrected),
                "time": e.created_at.isoformat() if e.created_at else "",
            }
            for e in executions
        ],
    }


@router.get("/report/trend")
def get_trend(project_id: int = Query(default=1), limit: int = Query(default=10)):
    """获取通过率趋势"""
    trend = get_pass_rate_trend(project_id, limit)
    return {"code": 0, "data": trend}


@router.get("/projects")
def get_projects():
    """列出所有项目"""
    projects = list_projects()
    return {
        "code": 0,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "filename": p.openapi_filename,
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
            for p in projects
        ],
    }
