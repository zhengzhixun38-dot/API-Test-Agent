"""
数据库模型 — SQLAlchemy ORM
SQLite 存储：projects、endpoints、test_cases、executions
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session

# ── 引擎 ──────────────────────────────────────────────

import os
db_path = os.path.join(os.path.dirname(__file__), "..", "data", "api_test_agent.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_engine(
    f"sqlite:///{db_path}",
    connect_args={"check_same_thread": False},
    echo=False,
)


def get_session() -> Session:
    return Session(engine)


# ── 基类 ──────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── 表定义 ─────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    openapi_filename = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    endpoints = relationship("Endpoint", back_populates="project", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="project", cascade="all, delete-orphan")


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    summary = Column(String(500))
    request_body = Column(JSON)   # {"param_name": {"type":"string", "required":true, ...}}
    responses = Column(JSON)      # {"200": "success", "401": "..."}
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="endpoints")
    test_cases = relationship("TestCase", back_populates="endpoint", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    case_name = Column(String(500), nullable=False)
    case_type = Column(String(50), nullable=False)  # normal/missing_param/invalid_type/boundary/auth_error
    request_data = Column(JSON)
    headers = Column(JSON)
    expected_status = Column(Integer, default=200)
    assert_rules = Column(JSON)
    is_llm_generated = Column(Integer, default=1)  # 1=LLM生成, 0=手写
    created_at = Column(DateTime, default=datetime.utcnow)

    endpoint = relationship("Endpoint", back_populates="test_cases")


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    total = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    pass_rate = Column(Float, default=0.0)
    duration = Column(Float, default=0.0)
    is_llm_generated = Column(Integer, default=0)
    is_self_corrected = Column(Integer, default=0)
    stdout = Column(Text)
    failure_analysis = Column(JSON)  # LLM 分析结果
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="executions")


# ── 建表 ──────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(engine)
