FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制源码
COPY . .

# 创建运行时目录
RUN mkdir -p generated_tests reports uploaded_docs data

# 暴露端口
# 8001: mock_server  8000: fastapi  8501: streamlit
EXPOSE 8000 8001 8501

# 默认启动命令（由 docker-compose 覆盖）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
