# API Test Agent

基于大模型的接口自动化测试 Agent 系统。上传 OpenAPI 文档 → LLM 自动生成测试用例 → 执行 pytest → 失败自动分析根因。

## 核心链路

```
OpenAPI 文档 → 解析接口信息 → LLM 生成测试用例 → 生成 pytest 脚本 → 执行测试 → 失败分析
                                                                          ↓
                                                                  自修正闭环（第二轮）
```

## 功能特性

- **LLM 自动生成测试用例**：基于 DeepSeek API，从 OpenAPI 文档生成 5 种类型用例（normal / missing_param / invalid_type / boundary / auth_error）
- **模板化 pytest 生成**：用例用模板渲染为可执行脚本，稳定可靠
- **失败根因分析**：失败用例自动交给 LLM 诊断，输出根因 + 排查建议
- **自修正闭环**：分析结果反馈给 LLM，自动修正用例并重新执行
- **数据库持久化**：SQLite 存储项目、接口、用例、执行历史，支持通过率趋势
- **Streamlit 前端**：可视化操作界面，上传→解析→生成→执行→报告一步到位

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI + Uvicorn |
| LLM 调用 | OpenAI SDK（兼容 DeepSeek / 通义千问 / 智谱 / Ollama） |
| 测试框架 | pytest + requests |
| 数据库 | SQLite + SQLAlchemy ORM |
| 前端 | Streamlit |
| Mock 服务 | FastAPI + Pydantic 校验 |

## 快速开始

### 1. 环境准备

```bash
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `.env` 文件，填入大模型 API Key：

```env
# DeepSeek（推荐，便宜好用）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat

# OpenAI
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
# BASE_URL=https://api.openai.com/v1
# MODEL_NAME=gpt-4o-mini
```

### 3. 启动

**方式一：Streamlit 前端（推荐）**

```bash
# 终端 1：启动 Mock 服务（被测接口）
uvicorn mock_server.mock_api:app --host 127.0.0.1 --port 8001

# 终端 2：启动 Streamlit
streamlit run app/streamlit_app.py
```

浏览器打开 `http://localhost:8501`，上传 `openapi.json`，按步骤操作。

**方式二：Docker 一键启动（推荐部署）**

```bash
docker-compose up -d
```

自动启动 3 个服务：
| 服务 | 端口 | 说明 |
|------|------|------|
| mock-server | 8001 | 模拟业务接口 |
| streamlit-ui | 8501 | 前端操作界面 |
| fastapi-api | 8000 | FastAPI + Swagger（可选） |

```bash
# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

**方式三：命令行一键运行**

```bash
# 终端 1：Mock 服务
uvicorn mock_server.mock_api:app --host 127.0.0.1 --port 8001

# 终端 2：全链路测试
python run_llm_tests.py
```

**方式三：FastAPI + Swagger**

```bash
uvicorn app.main:app --port 8000
# 浏览器打开 http://localhost:8000/docs
```

## 项目结构

```
api-test-agent/
│
├── mock_server/
│   └── mock_api.py              # 模拟业务接口（4个REST API）
│
├── app/
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 配置读取
│   ├── models.py                # SQLAlchemy ORM 模型（4表）
│   ├── db.py                    # 数据库 CRUD
│   ├── streamlit_app.py         # Streamlit 前端（3页面）
│   │
│   ├── agents/
│   │   ├── testcase_agent.py    # 用例生成 Agent
│   │   └── report_agent.py      # 失败分析 Agent
│   │
│   ├── tools/
│   │   ├── openapi_parser.py    # OpenAPI 解析器
│   │   ├── test_file_writer.py  # pytest 脚本生成器
│   │   └── pytest_runner.py     # 测试执行引擎
│   │
│   ├── services/
│   │   ├── parse_service.py     # 解析编排
│   │   ├── testcase_service.py   # 用例生成编排
│   │   └── execute_service.py   # 执行编排
│   │
│   ├── routers/
│   │   ├── upload.py            # 上传 OpenAPI
│   │   ├── parse.py             # 解析接口
│   │   ├── testcase.py          # 生成用例
│   │   ├── execute.py           # 执行测试
│   │   └── report.py            # 查看报告/历史/趋势
│   │
│   └── prompts/
│       ├── testcase_prompt.txt  # 用例生成 prompt
│       └── report_prompt.txt    # 失败分析 prompt
│
├── generated_tests/             # 生成的 pytest 脚本
├── reports/                     # 测试报告
├── uploaded_docs/               # 上传的 OpenAPI 文档
│
├── openapi.json                 # 测试用 OpenAPI 文档
├── run_all_tests.py             # 手写用例一键测试
├── run_llm_tests.py             # LLM 驱动一键测试（含自修正）
├── requirements.txt
└── .env
```

## Mock 接口列表

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/user/login` | 用户登录 | 无 |
| GET | `/api/user/info` | 获取用户信息 | Bearer Token |
| GET | `/api/product/list` | 商品列表（分页+搜索） | 无 |
| POST | `/api/order/create` | 创建订单 | Bearer Token |

## 测试用例类型

| case_type | 说明 | 示例 |
|-----------|------|------|
| normal | 合法参数，期望成功 | 正确用户名密码登录 |
| missing_param | 必填参数缺失或为空 | 用户名为空字符串 |
| invalid_type | 类型错误或格式非法 | 用户名含特殊字符 |
| boundary | 边界值测试 | 密码仅5位（要求≥6） |
| auth_error | 鉴权失败 | 缺少/无效 Token |

## 执行效果

```
============================================================
  FINAL REPORT
============================================================
  Endpoints:     4
  Total Cases:   57 (LLM Generated)
  Passed:        46
  Failed:        11
  Pass Rate:     80.7%
============================================================

失败分析示例:
  [test_case_xxx] 接口返回401未授权，预期200
    根因: 测试用例未携带有效 token
    建议: 在 headers 中添加 Authorization: Bearer mock-token-2024
    严重程度: major
```

> 手写用例用于验证核心链路的正确性。通过率受 Mock 服务逻辑影响，可自行调整。

## 数据库表

| 表 | 字段 | 说明 |
|----|------|------|
| projects | id, name, openapi_filename, created_at | 项目 |
| endpoints | id, project_id, path, method, request_body, responses | 接口 |
| test_cases | id, endpoint_id, case_name, case_type, request_data, headers, expected_status, assert_rules | 用例 |
| executions | id, project_id, total, passed, failed, pass_rate, duration, failure_analysis, created_at | 执行记录 |

## License

MIT
