FROM python:3.12-slim

WORKDIR /app

# 安装依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 common 模块
COPY common/ /app/common/
COPY containerized_experiment/ /app/

# 创建日志和数据目录
RUN mkdir -p /app/logs /app/data

# 默认命令
CMD ["python", "-c", "print('HVRT container ready')"]
