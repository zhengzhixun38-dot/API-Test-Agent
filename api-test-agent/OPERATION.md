# API Test Agent — 操作文档

## 环境要求

- Python 3.10+
- Docker Desktop（可选）
- 大模型 API Key（DeepSeek / OpenAI / 通义千问 均可）

---

## 一、快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd api-test-agent
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
source venv/Scripts/activate

# Mac / Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 Key：

```env
# DeepSeek（推荐）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

### 5. 启动

**方式一：Docker 一键启动（推荐）**

```bash
docker compose up -d
```

三个服务自动启动：

| 服务 | 端口 | 地址 |
|------|------|------|
| Mock 接口 | 8001 | http://localhost:8001 |
| Streamlit 前端 | 8501 | http://localhost:8501 |
| FastAPI + Swagger | 8000 | http://localhost:8000/docs |

**方式二：本地启动**

```bash
# 终端 1：启动 Mock 服务
uvicorn mock_server.mock_api:app --host 127.0.0.1 --port 8001 --reload

# 终端 2：启动 Streamlit 前端
streamlit run app/streamlit_app.py
```

---

## 二、使用流程

### 通过 Streamlit 前端操作

1. 打开 http://localhost:8501
2. **Upload**：上传 `openapi.json`
3. **Parse**：点击 Parse 解析接口
4. **Generate**：点击 Generate with LLM 生成用例
5. **Execute**：点击 Run Tests 执行测试（实时日志滚动）
6. **Analyze**：如有失败，点击 Analyze Failures 分析根因

### 通过命令行操作

```bash
# 一键手写用例测试（40 条 ⇒ 100%）
python run_all_tests.py

# 一键 LLM 全链路（含自修正）
python run_llm_tests.py

# RAG A/B 对比
python run_rag_compare.py
```

---

## 三、项目界面说明

### Streamlit 三种页面

| 页面 | 功能 |
|------|------|
| **Run Tests** | 主流程：上传 → 解析 → 生成 → 执行 → 分析 |
| **History** | 历史执行记录 + 通过率趋势折线图 |
| **Projects** | 项目管理，查看所有已上传的 OpenAPI 项目 |

### FastAPI Swagger 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务信息 |
| POST | `/api/upload` | 上传 OpenAPI 文档 |
| POST | `/api/parse` | 解析接口 |
| POST | `/api/testcase/generate` | LLM 生成测试用例 |
| POST | `/api/execute?analyze=true` | 执行测试 + 失败分析 |
| GET | `/api/report` | 最近一次执行结果 |
| GET | `/api/report/history?project_id=1` | 历史执行记录 |
| GET | `/api/report/trend?project_id=1` | 通过率趋势 |
| GET | `/api/projects` | 所有项目列表 |
| WebSocket | `/ws/execute` | 实时执行日志 |

---

## 四、Docker 操作

```bash
docker compose up -d          # 启动
docker compose down           # 停止
docker compose up -d --build  # 重建并启动
docker compose ps             # 查看状态
docker compose logs -f mock   # 查看 Mock 日志
```

---

## 五、Mock 接口说明

Mock 服务模拟 4 个电商业务接口，端口 8001。

| 方法 | 路径 | 鉴权 | 测试账号 |
|------|------|------|----------|
| POST | `/api/user/login` | 无 | admin / 123456 |
| GET | `/api/user/info` | Bearer Token | token: mock-token-2024 |
| GET | `/api/product/list?page=1&page_size=10` | 无 | page 1-100, size 1-100 |
| POST | `/api/order/create` | Bearer Token | product_id 1-100, count 1-999 |

### 校验规则

| 字段 | 规则 |
|------|------|
| username | 3-20 位，仅字母数字下划线 |
| password | 6-20 位 |
| page | ≥ 1 |
| page_size | 1-100 |
| keyword | ≤ 50 字符 |
| product_id | 1-100 |
| count | 1-999 |

### 状态码说明

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 业务规则错误 |
| 401 | 鉴权失败 |
| 404 | 资源不存在 |
| 422 | 参数校验失败(Pydantic) |

---

## 六、测试用例类型

系统生成 5 种类型：

| case_type | 说明 | 示例场景 |
|-----------|------|----------|
| normal | 合法参数 | 正确用户名密码登录 |
| missing_param | 必填参数缺失/为空 | 用户名为空字符串 |
| invalid_type | 类型错误/格式非法 | 用户名含特殊字符 |
| boundary | 边界值 | 密码仅 5 位（要求 ≥6） |
| auth_error | 鉴权失败 | 缺少/无效 Token |

---

## 七、断言类型

用例中 `assert_rules` 支持 7 种断言：

```json
{
  "contains_fields": ["code", "message", "data"],
  "data_contains_fields": ["token", "username"],
  "list_not_empty": true,
  "response_time_lt": 500,
  "field_types": {"total": "int"},
  "equals": {"code": 0},
  "not_empty": true
}
```

| 断言 | 用途 | 接口示例 |
|------|------|----------|
| contains_fields | 顶层字段存在 | 所有接口 |
| data_contains_fields | data 内部字段 | 登录（token, username） |
| list_not_empty | 列表不为空 | 商品列表 |
| response_time_lt | 响应时间阈值 | 性能测试 |
| field_types | 字段类型 | - |
| equals | 精确值匹配 | - |
| not_empty | 响应体非空 | - |

---

## 八、数据库表结构

| 表 | 主要字段 | 说明 |
|----|----------|------|
| projects | id, name, openapi_filename | 项目 |
| endpoints | id, project_id, path, method, request_body, headers | 解析后的接口 |
| test_cases | id, endpoint_id, case_name, case_type, request_data, headers, expected_status, assert_rules | 生成的用例 |
| executions | id, project_id, total, passed, failed, pass_rate, duration, failure_analysis, stdout | 执行记录 |

数据库文件：`data/api_test_agent.db`

---

## 九、常见问题

### Q: 启动报 "端口被占用"

```bash
# 查找占用端口的进程
netstat -ano | grep 8001

# 关闭进程（替换 PID）
taskkill //F //PID xxxx
```

### Q: LLM 调用失败

检查 `.env` 中 API Key 是否有效，Base URL 是否匹配。

### Q: 手写用例不是 100%

确保 Mock 服务在 8001 端口运行中，登录接口使用 admin/123456。

### Q: Docker 首次构建很慢

首次需下载 Python 镜像 + 所有依赖，约 3-5 分钟。后续构建会使用缓存。

### Q: 如何换大模型

编辑 `.env` 中的 `BASE_URL` 和 `MODEL_NAME`：

```env
# OpenAI
BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini

# 通义千问
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-turbo

# 智谱
BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-4-flash

# 本地 Ollama
BASE_URL=http://localhost:11434/v1
MODEL_NAME=qwen2.5:7b
```

---

## 十、项目结构速查

```
api-test-agent/
├── mock_server/mock_api.py      # Mock 业务接口
├── app/
│   ├── agents/                  # LLM Agent（用例生成/失败分析/RAG增强）
│   ├── tools/                   # 工具（解析/脚本生成/执行）
│   ├── services/                # 服务编排
│   ├── routers/                 # API 路由
│   ├── rag/                     # RAG 知识库
│   ├── models.py / db.py        # 数据库
│   ├── main.py                  # FastAPI 入口 + WebSocket
│   ├── config.py                # 配置
│   └── streamlit_app.py         # Streamlit 前端
├── run_all_tests.py             # 手写用例一键测试
├── run_llm_tests.py             # LLM 全链路测试
├── run_rag_compare.py           # RAG A/B 对比
├── build_knowledge_base.py      # 构建 RAG 知识库
├── Dockerfile / docker-compose  # Docker 部署
├── openapi.json                 # 测试用 OpenAPI 文档
└── .env                         # API Key 配置
```

## 十一、命令速查

```bash
# 环境
source venv/Scripts/activate      # 激活虚拟环境
pip install -r requirements.txt   # 安装依赖

# 启动
streamlit run app/streamlit_app.py                   # Streamlit 前端
uvicorn mock_server.mock_api:app --port 8001         # Mock 服务
uvicorn app.main:app --port 8000                     # FastAPI
docker compose up -d                                 # Docker 一键

# 测试
python run_all_tests.py             # 手写用例（40条，100%）
python run_llm_tests.py             # LLM 全链路
python run_rag_compare.py           # RAG 对比
python build_knowledge_base.py      # 构建 RAG

# Docker
docker compose ps                   # 查看状态
docker compose logs -f streamlit    # 查看日志
docker compose down                 # 停止
docker compose up -d --build        # 重建
```
