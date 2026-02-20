# 第一阶段：编译环境
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# 鉴于已启用 VPN TUN 模式，还原并使用官方源，避免镜像源签名冲突
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 (由于是企业环境，采用三级回退逻辑：1.Nexus私服 -> 2.官方源 -> 3.清华源)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install --default-timeout=5 \
    -i http://192.168.1.168:8081/repository/pypi-all/simple --trusted-host 192.168.1.168 -r requirements.txt || \
    pip install --no-cache-dir --prefix=/install --default-timeout=30 -r requirements.txt || \
    pip install --no-cache-dir --prefix=/install --default-timeout=60 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 第二阶段：运行时环境
FROM python:3.11-slim-bookworm

WORKDIR /app

# 还原官方源
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制安装好的 Python 包
COPY --from=builder /install /usr/local

# 复制项目代码
COPY . .

# 设置 PYTHONPATH 确保模块可发现
ENV PYTHONPATH=/app

# 给予启动脚本执行权限
COPY docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# 默认启动后端 API 服务
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "devops_portal.main:app", "--host", "0.0.0.0", "--port", "8000"]
