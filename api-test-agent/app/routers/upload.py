"""上传路由 — 接收 OpenAPI 文档 + 创建项目"""
import json
from fastapi import APIRouter, UploadFile, File, Request
from app.db import create_project

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_openapi(request: Request, file: UploadFile = File(...)):
    content = await file.read()
    try:
        if file.filename.endswith((".yaml", ".yml")):
            import yaml
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
    except Exception:
        return {"code": 400, "message": f"无法解析 {file.filename}"}

    # 创建项目并入DB
    title = data.get("info", {}).get("title", file.filename)
    project = create_project(name=title, openapi_filename=file.filename)

    # 存到 app.state 供后续步骤使用（兼容旧版）
    request.app.state.openapi_raw = data
    request.app.state.project_id = project.id

    path_count = len(data.get("paths", {}))
    return {
        "code": 0,
        "message": "上传成功",
        "data": {
            "project_id": project.id,
            "filename": file.filename,
            "api_count": path_count,
        },
    }
