# DevOps Platform 自动化运维方案

.PHONY: help init test build up down logs sync-all

# 颜色定义
YELLOW := \033[1;33m
GREEN := \033[1;32m
RESET := \033[0m

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'

init: ## 初始化系统（安装依赖、初始化数据库）
	@echo "$(GREEN)🚀 Initializing DevOps Platform...$(RESET)"
	pip install -r requirements.txt
	python scripts/init_discovery.py
	python scripts/init_cost_codes.py
	python scripts/init_labor_rates.py
	python scripts/init_purchase_contracts.py
	python scripts/init_revenue_contracts.py

test: ## 运行所有测试
	@echo "$(GREEN)🧪 Running unit and integration tests...$(RESET)"
	pytest tests/

build: ## 构建 Docker 镜像
	@echo "$(GREEN)📦 Building Docker images...$(RESET)"
	docker-compose build

up: ## 启动 Docker 容器
	@echo "$(GREEN)🆙 Starting services...$(RESET)"
	docker-compose up -d

down: ## 停止并移除容器
	@echo "$(GREEN)🛑 Stopping services...$(RESET)"
	docker-compose down

logs: ## 查看实时日志
	docker-compose logs -f

sync-all: ## 手动触发全量数据同步
	@echo "$(GREEN)🔄 Triggering full sync...$(RESET)"
	python -m devops_collector.scheduler --force-all
	python -m devops_collector.worker --once

dbt-build: ## 执行 dbt 建模转换
	@echo "$(GREEN)🏗️ Running dbt transformations...$(RESET)"
	cd dbt_project && dbt build

dashboard: ## 启动 DevOps 智能决策仪表盘
	@echo "$(GREEN)🖥️ Starting Streamlit Dashboard...$(RESET)"
	streamlit run dashboard/Home.py

validate: ## 执行数据质量校验 (Great Expectations)
	@echo "$(GREEN)⚖️ Running Data Quality Validation...$(RESET)"
	python scripts/validate_models.py

orchestrate: ## 启动资产编排控制台 (Dagster)
	@echo "$(GREEN)🏗️ Starting Dagster Orchestrator...$(RESET)"
	dagster dev -f dagster_repo/__init__.py

datahub-ingest: ## 同步元数据到 DataHub (PostgreSQL & dbt)
	@echo "$(GREEN)🔭 Ingesting metadata to DataHub...$(RESET)"
	datahub ingest -c datahub/recipe_postgres.yml
	datahub ingest -c datahub/recipe_dbt.yml

clean: ## 清理临时文件
	@echo "$(GREEN)🧹 Cleaning temporary files...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
