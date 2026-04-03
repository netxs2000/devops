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

# Install python dependencies using uv (Frozen mode via uv.lock)
ARG PIP_INDEX_URL
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --index-url ${PIP_INDEX_URL} --trusted-host 192.168.5.64 || \
    uv sync --frozen --no-install-project --no-dev --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Copy project code
COPY . .

# Final sync to install the project itself and dev/test extras if needed 
# (Standardizing on --no-dev for production, use --all-groups if tests are run in-container)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-groups

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Startup script
COPY docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "devops_portal.main:app", "--host", "0.0.0.0", "--port", "8000"]

