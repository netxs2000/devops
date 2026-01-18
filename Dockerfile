# 使用多阶段构建以优化镜像体积
# 第一阶段：编译环境
# 禁用官方镜像源：
FROM python:3.11-slim-bookworm AS builder
# 使用国内代理镜像源，例如阿里或特定的加速地址
# FROM docker.m.daocloud.io/library/python:3.11-slim-bookworm AS builder

WORKDIR /app

# 替换为国内镜像源以加速构建
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 (使用国内镜像源加速)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install --default-timeout=100 -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 第二阶段：运行时环境
# 禁用官方镜像：
FROM python:3.11-slim-bookworm
# 使用国内代理镜像源，例如阿里或特定的加速地址
# FROM docker.m.daocloud.io/library/python:3.11-slim-bookworm

WORKDIR /app

# 替换为国内镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装运行时系统依赖
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
