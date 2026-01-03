# DevOps Platform 自动化运维方案
# -----------------------------------------------------------
#  标准化 Docker 部署与运维命令规范
#  所有操作均在容器内部执行，确保环境一致性
# -----------------------------------------------------------

.PHONY: help deploy init test build up down logs sync-all shell clean

# 颜色定义
YELLOW := \033[1;33m
GREEN := \033[1;32m
CYAN := \033[1;36m
RESET := \033[0m

# 统一执行前缀：在 api 容器中执行 (使用 -T 避免 TTY 问题)
EXEC_CMD := docker-compose exec -T api

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'

# =============================================================================
# 🚀 核心部署流程 (One-Click Deployment)
# =============================================================================

deploy: down build up init ## [一键部署] 重建镜像 -> 启动服务 -> 初始化数据
	@echo "$(CYAN)🎉 DevOps Platform deployed successfully!$(RESET)"

init: ## [初始化] 在容器内安装依赖并初始化数据库数据
	@echo "$(GREEN)🚀 Initializing data inside container...$(RESET)"
	$(EXEC_CMD) pip install -r requirements.txt
	$(EXEC_CMD) python scripts/init_discovery.py
	$(EXEC_CMD) python scripts/init_cost_codes.py
	$(EXEC_CMD) python scripts/init_labor_rates.py
	$(EXEC_CMD) python scripts/init_purchase_contracts.py
	$(EXEC_CMD) python scripts/init_revenue_contracts.py

# =============================================================================
# 🐳 Docker 基础操作
# =============================================================================

build: ## 构建 Docker 镜像
	@echo "$(GREEN)📦 Building Docker images...$(RESET)"
	docker-compose build

up: ## 启动 Docker 容器 (等待健康检查通过)
	@echo "$(GREEN)🆙 Starting services & waiting for DB...$(RESET)"
	docker-compose up -d --wait

down: ## 停止并移除容器
	@echo "$(GREEN)🛑 Stopping services...$(RESET)"
	docker-compose down

logs: ## 查看实时日志
	docker-compose logs -f --tail=100

shell: ## 进入 API 容器终端 (Debug 用)
	docker-compose exec api /bin/bash

# =============================================================================
# 🛠️ 运维与测试工具
# =============================================================================

test: ## 运行所有测试 (容器内)
	@echo "$(GREEN)🧪 Running unit and integration tests (inside container)...$(RESET)"
	$(EXEC_CMD) pytest tests/

sync-all: ## 手动触发全量数据同步
	@echo "$(GREEN)🔄 Triggering full sync...$(RESET)"
	$(EXEC_CMD) python -m devops_collector.scheduler --force-all
	$(EXEC_CMD) python -m devops_collector.worker --once

dbt-build: ## 执行 dbt 建模转换
	@echo "$(GREEN)🏗️ Running dbt transformations...$(RESET)"
	$(EXEC_CMD) bash -c "cd dbt_project && dbt build"

validate: ## 执行数据质量校验 (Great Expectations)
	@echo "$(GREEN)⚖️ Running Data Quality Validation...$(RESET)"
	$(EXEC_CMD) python scripts/validate_models.py

datahub-ingest: ## 同步元数据到 DataHub (PostgreSQL & dbt)
	@echo "$(GREEN)🔭 Ingesting metadata to DataHub...$(RESET)"
	$(EXEC_CMD) datahub ingest -c datahub/recipe_postgres.yml
	$(EXEC_CMD) datahub ingest -c datahub/recipe_dbt.yml

clean: ## 清理临时文件
	@echo "$(GREEN)🧹 Cleaning temporary files...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
