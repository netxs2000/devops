# 第一阶段：编译环境
FROM 192.168.5.64:8082/library/python:3.11-slim-bookworm AS builder

WORKDIR /app

# 鉴于已启用 VPN TUN 模式，还原并使用官方源，避免镜像源签名冲突
# 使用 BuildKit 缓存挂载点加速 apt 安装
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制 uv 二进制文件 (显式使用本地 Nexus 镜像加速安装，仅在 builder 阶段可见)
COPY --from=192.168.5.64:8082/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# 复制依赖文件并安装 (uv pip 支持原生并发安装，速度提升 10x-100x)
# 使用 BuildKit 缓存挂载点保存 uv 缓存路径 /root/.cache/uv
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --target /install --index-url http://192.168.5.64:8082/repository/group-pypi/simple --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host 192.168.5.64 -r requirements.txt

# 第二阶段：运行时环境
FROM 192.168.5.64:8082/library/python:3.11-slim-bookworm

WORKDIR /app

# 还原官方源
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
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
