"""
数据库操作封装 — CRUD
"""
from datetime import datetime
from sqlalchemy import desc
from app.models import (
    get_session, init_db,
    Project, Endpoint, TestCase, Execution,
)


# ── 初始化 ────────────────────────────────────────────

def setup():
    init_db()


# ── Project ───────────────────────────────────────────

def create_project(name: str, openapi_filename: str = "") -> Project:
    with get_session() as s:
        p = Project(name=name, openapi_filename=openapi_filename)
        s.add(p)
        s.commit()
        s.refresh(p)
        return p


def list_projects() -> list[Project]:
    with get_session() as s:
        return s.query(Project).order_by(desc(Project.created_at)).all()


def get_project(project_id: int) -> Project | None:
    with get_session() as s:
        return s.get(Project, project_id)


# ── Endpoint ──────────────────────────────────────────

def save_endpoints(project_id: int, endpoints: list[dict]) -> list[int]:
    """批量保存解析后的接口信息，返回 ID 列表"""
    with get_session() as s:
        s.query(Endpoint).filter(Endpoint.project_id == project_id).delete()
        ids = []
        for ep in endpoints:
            obj = Endpoint(
                project_id=project_id,
                path=ep["path"],
                method=ep["method"],
                summary=ep.get("summary", ""),
                request_body=ep.get("request_body", {}),
                responses=ep.get("responses", {}),
            )
            s.add(obj)
            s.flush()
            ids.append(obj.id)
        s.commit()
        return ids


def get_endpoints(project_id: int) -> list[Endpoint]:
    with get_session() as s:
        return s.query(Endpoint).filter(Endpoint.project_id == project_id).all()


# ── TestCase ──────────────────────────────────────────

def save_test_cases(endpoint_id: int, cases: list[dict], is_llm: bool = True) -> list[TestCase]:
    """保存某个接口的测试用例"""
    with get_session() as s:
        # 先删旧数据
        s.query(TestCase).filter(TestCase.endpoint_id == endpoint_id).delete()
        objs = []
        for c in cases:
            if "error" in c:
                continue
            obj = TestCase(
                endpoint_id=endpoint_id,
                case_name=c.get("case_name", ""),
                case_type=c.get("case_type", "normal"),
                request_data=c.get("request_data", {}),
                headers=c.get("headers", {}),
                expected_status=c.get("expected_status", 200),
                assert_rules=c.get("assert_rules", {}),
                is_llm_generated=1 if is_llm else 0,
            )
            s.add(obj)
            objs.append(obj)
        s.commit()
        return objs


def get_test_cases(endpoint_id: int) -> list[TestCase]:
    with get_session() as s:
        return s.query(TestCase).filter(TestCase.endpoint_id == endpoint_id).all()


# ── Execution ──────────────────────────────────────────

def save_execution(
    project_id: int,
    total: int, passed: int, failed: int,
    pass_rate: float, duration: float = 0,
    is_llm: bool = False, is_corrected: bool = False,
    stdout: str = "", analysis: list[dict] | None = None,
) -> Execution:
    with get_session() as s:
        obj = Execution(
            project_id=project_id,
            total=total,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            duration=duration,
            is_llm_generated=1 if is_llm else 0,
            is_self_corrected=1 if is_corrected else 0,
            stdout=stdout[:10000],
            failure_analysis=analysis,
        )
        s.add(obj)
        s.commit()
        s.refresh(obj)
        return obj


def list_executions(project_id: int, limit: int = 20) -> list[Execution]:
    with get_session() as s:
        return (
            s.query(Execution)
            .filter(Execution.project_id == project_id)
            .order_by(desc(Execution.created_at))
            .limit(limit)
            .all()
        )


def get_pass_rate_trend(project_id: int, limit: int = 10) -> list[dict]:
    """获取通过率趋势，供前端画图"""
    with get_session() as s:
        rows = (
            s.query(Execution)
            .filter(Execution.project_id == project_id)
            .order_by(desc(Execution.created_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "pass_rate": r.pass_rate,
                "total": r.total,
                "passed": r.passed,
                "failed": r.failed,
                "is_llm": bool(r.is_llm_generated),
                "corrected": bool(r.is_self_corrected),
                "time": r.created_at.isoformat() if r.created_at else "",
            }
            for r in reversed(rows)
        ]
