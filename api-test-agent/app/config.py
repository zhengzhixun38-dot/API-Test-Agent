"""
应用配置 — 从 .env 读取
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── LLM ──
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    BASE_URL: str = os.getenv("BASE_URL", "https://api.openai.com/v1")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")

    # ── 被测服务 ──
    TEST_BASE_URL: str = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8001")

    # ── 路径 ──
    UPLOAD_DIR: str = "uploaded_docs"
    OUTPUT_DIR: str = os.getenv("TEST_OUTPUT_DIR", "generated_tests")
    REPORT_DIR: str = "reports"


settings = Settings()
