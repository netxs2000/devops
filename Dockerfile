# Default build arguments for registry and index
ARG UV_IMAGE=astral-sh/uv:latest
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# Copy uv binaries from the specified image
FROM ${UV_IMAGE} AS uv_bin

FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpq5 \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management (Allowing override from Nexus)
COPY --from=uv_bin /uv /uvx /bin/

# Install python dependencies (Falling back to Tsinghua if Nexus fails)
ARG PIP_INDEX_URL
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -i ${PIP_INDEX_URL} --trusted-host 192.168.5.64 -r requirements.txt || \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Copy project code
COPY . .

# Install extras and the package itself
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -i ${PIP_INDEX_URL} --trusted-host 192.168.5.64 .[dev,test] || \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple .[dev,test]

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Startup script
COPY docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "devops_portal.main:app", "--host", "0.0.0.0", "--port", "8000"]

