"""
API Test Agent — FastAPI 后端入口 (V2)
新增：数据库持久化、历史查询
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import setup as db_setup
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json as json_module
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers import upload, parse, testcase, execute, report
from app.tools.pytest_runner import run_pytest_stream


@asynccontextmanager
async def lifespan(application: FastAPI):
    db_setup()
    yield


app = FastAPI(
    title="API Test Agent",
    description="基于大模型的接口自动化测试 Agent — V3 (WebSocket + Enhanced Assertions)",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(parse.router)
app.include_router(testcase.router)
app.include_router(execute.router)
app.include_router(report.router)


@app.get("/")
def root():
    return {
        "service": "API Test Agent",
        "version": "3.0.0",
        "docs": "/docs",
    }


@app.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    """WebSocket 端点 — 实时推送 pytest 执行日志"""
    await websocket.accept()

    test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_tests")

    if not os.path.isdir(test_dir) or not os.listdir(test_dir):
        await websocket.send_json({"type": "error", "message": "No test files found. Generate test cases first."})
        await websocket.close()
        return

    async def send_line(line: str):
        try:
            await websocket.send_json({"type": "log", "line": line})
        except Exception:
            pass

    await websocket.send_json({"type": "start", "message": "Execution started..."})

    # 在线程池中运行（不阻塞 event loop）
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: run_pytest_stream(test_dir, on_line=lambda l: None),
    )

    # 因为 run_in_executor 中 on_line 不在 async 上下文，直接一次性发日志
    stdout = result.get("stdout", "")
    for line in stdout.split("\n"):
        await send_line(line)
        await asyncio.sleep(0.001)

    s = result.get("summary", {})
    await websocket.send_json({
        "type": "done",
        "total": s.get("total", 0),
        "passed": s.get("passed", 0),
        "failed": s.get("failed", 0),
        "duration": s.get("duration", 0),
    })

    await websocket.close()
