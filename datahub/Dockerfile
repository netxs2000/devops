# Lightweight image for DataHub ingestion tasks
FROM python:3.11-slim-bookworm

WORKDIR /app

# Change sources to aliyun for speed (matching main Dockerfile)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# Install basic deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Default command (can be overridden by docker-compose or manual run)
CMD ["datahub", "--help"]
