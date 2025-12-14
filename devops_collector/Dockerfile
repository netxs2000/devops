FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
# RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Put code into a package directory so "python -m devops_collector.xxx" works
# Context is usually the devops_collector directory itself
COPY . /app/devops_collector

# Set PYTHONPATH to /app so we can import devops_collector
ENV PYTHONPATH=/app

# We will use command line args to start different components
ENTRYPOINT ["python", "-m"]
