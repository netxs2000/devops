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

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install python dependencies using uv
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Copy project code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Startup script
COPY docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "devops_portal.main:app", "--host", "0.0.0.0", "--port", "8000"]

