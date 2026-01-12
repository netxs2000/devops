# DevOps Platform 自动化运维方案
# -----------------------------------------------------------
#  标准化 Docker 部署与运维命令规范
#  所有操作均在容器内部执行，确保环境一致性
# -----------------------------------------------------------

.PHONY: help deploy init test build up down logs sync-all shell clean lock install

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
# 核心部署流程 (One-Click Deployment)
# =============================================================================

deploy: down build up init ## [一键部署] 重建镜像 -> 启动服务 -> 初始化数据
	@echo "$(CYAN)DevOps Platform deployed successfully!$(RESET)"

init: ## [初始化] 在容器内安装依赖并初始化数据库数据
	@echo "$(GREEN)Initializing data inside container...$(RESET)"
	$(MAKE) install
	$(EXEC_CMD) python scripts/init_discovery.py
	$(EXEC_CMD) python scripts/init_rbac.py
	$(EXEC_CMD) python scripts/init_organizations.py
	$(EXEC_CMD) python scripts/init_calendar.py
	$(EXEC_CMD) python scripts/init_mdm_location.py
	$(EXEC_CMD) python scripts/init_service_catalog.py
	$(EXEC_CMD) python scripts/init_cost_codes.py
	$(EXEC_CMD) python scripts/init_labor_rates.py
	$(EXEC_CMD) python scripts/init_purchase_contracts.py
	$(EXEC_CMD) python scripts/init_revenue_contracts.py

install: ## [内用] 安装生产环境或开发环境依赖
	@echo "$(GREEN)Installing dependencies...$(RESET)"
	$(EXEC_CMD) pip install -i https://pypi.tuna.tsinghua.edu.cn/simple .

lock: ## [工具] 将 pyproject.toml 的依赖锁定到 requirements.txt
	@echo "$(GREEN)Locking dependencies to requirements.txt (Inside Container)...$(RESET)"
	$(EXEC_CMD) pip-compile pyproject.toml -o requirements.txt --resolver=backtracking --no-header

# =============================================================================
# 离线包构建与部署 (Offline Deployment)
# =============================================================================

package: ## [本地构建] 构建并打包镜像为 tar 文件 (devops-platform.tar)
	@echo "$(GREEN)Building Docker images...$(RESET)"
	docker build -t devops-platform:latest .
	docker build -t devops-platform-datahub:latest datahub/
	@echo "$(GREEN)Saving images to devops-platform.tar...$(RESET)"
	docker save -o devops-platform.tar devops-platform:latest devops-platform-datahub:latest
	@echo "$(CYAN)Package created: devops-platform.tar$(RESET)"
	@echo "Upload this file to your server and run 'make deploy-offline'"

deploy-offline: check-env ## [服务器专用] 加载本地镜像并部署 (无需构建/网络)
ifeq ($(wildcard devops-platform.tar),)
	@echo "$(YELLOW)devops-platform.tar not found. Checking if image exists...$(RESET)"
else
	@echo "$(GREEN)Loading Docker image from tar...$(RESET)"
	docker load -i devops-platform.tar
endif
	@echo "$(GREEN)Starting Offline Deployment...$(RESET)"
	$(PROD_CMD) down --remove-orphans
	@echo "$(GREEN)Starting services...$(RESET)"
	# 注意：这里不执行 build，直接启动，依赖已加载的镜像
	$(PROD_CMD) up -d --wait --no-build
	@echo "$(GREEN)Initializing system data...$(RESET)"
	$(PROD_CMD) exec -T api python scripts/init_discovery.py
	$(PROD_CMD) exec -T api python scripts/init_cost_codes.py
	$(PROD_CMD) exec -T api python scripts/init_labor_rates.py
	$(PROD_CMD) exec -T api python scripts/init_purchase_contracts.py
	$(PROD_CMD) exec -T api python scripts/init_revenue_contracts.py
	@echo "$(CYAN)Offline deployment completed successfully!$(RESET)"

# =============================================================================
# 生产环境部署 (Production Deployment - Legacy)
# =============================================================================

PROD_COMPOSE := -f docker-compose.prod.yml
PROD_CMD := docker-compose $(PROD_COMPOSE)

check-env:
ifeq ($(wildcard .env),)
	@echo "$(YELLOW).env file not found! Copying from .env.example...$(RESET)"
	@powershell -Command "Copy-Item .env.example .env"
	@echo "$(RED)Please edit .env file with your production credentials before running deploy!$(RESET)"
	@exit 1
endif

deploy-prod: check-env ## [服务器专用] 生产环境一键部署 (安全/稳定)
	@echo "$(GREEN)Starting Production Deployment...$(RESET)"
	$(PROD_CMD) down --remove-orphans
	@echo "$(GREEN)Building optimized production images...$(RESET)"
	$(PROD_CMD) build
	@echo "$(GREEN)Starting services...$(RESET)"
	$(PROD_CMD) up -d --wait
	@echo "$(GREEN)Initializing system data...$(RESET)"
	$(PROD_CMD) exec -T api python scripts/init_discovery.py
	$(PROD_CMD) exec -T api python scripts/init_cost_codes.py
	$(PROD_CMD) exec -T api python scripts/init_labor_rates.py
	$(PROD_CMD) exec -T api python scripts/init_purchase_contracts.py
	$(PROD_CMD) exec -T api python scripts/init_revenue_contracts.py
	@echo "$(CYAN)Production deployment completed successfully!$(RESET)"

prod-logs: ## [服务器专用] 查看生产日志
	$(PROD_CMD) logs -f --tail=100

prod-down: ## [服务器专用] 停止生产服务
	$(PROD_CMD) down

# =============================================================================
# Docker 基础操作
# =============================================================================

build: ## 构建 Docker 镜像
	@echo "$(GREEN)Building Docker images...$(RESET)"
	docker-compose build

up: ## 启动 Docker 容器 (等待健康检查通过)
	@echo "$(GREEN)Starting services & waiting for DB...$(RESET)"
	docker-compose up -d --wait

down: ## 停止并移除容器
	@echo "$(GREEN)Stopping services...$(RESET)"
	docker-compose down

logs: ## 查看实时日志
	docker-compose logs -f --tail=100

shell: ## 进入 API 容器终端 (Debug 用)
	docker-compose exec api /bin/bash

# =============================================================================
# 运维与测试工具
# =============================================================================

test: ## 运行所有测试 (容器内)
	@echo "$(GREEN)Running unit and integration tests (inside container)...$(RESET)"
	$(EXEC_CMD) pytest tests/

sync-all: ## 手动触发全量数据同步
	@echo "$(GREEN)Triggering full sync...$(RESET)"
	$(EXEC_CMD) python -m devops_collector.scheduler --force-all
	$(EXEC_CMD) python -m devops_collector.worker --once

dbt-build: ## 执行 dbt 建模转换
	@echo "$(GREEN)Running dbt transformations...$(RESET)"
	$(EXEC_CMD) bash -c "cd dbt_project && dbt build"

validate: ## 执行数据质量校验 (Great Expectations)
	@echo "$(GREEN)Running Data Quality Validation...$(RESET)"
	$(EXEC_CMD) python scripts/validate_models.py


# 定义 DataHub CLI 运行命令 (临时容器)
DATAHUB_CMD := docker-compose run --rm datahub-cli

datahub-ingest: ## 同步元数据到 DataHub (PostgreSQL & dbt)
	@echo "$(GREEN)Ingesting metadata to DataHub...$(RESET)"
	$(DATAHUB_CMD) datahub ingest -c datahub/recipe_postgres.yml
	$(DATAHUB_CMD) datahub ingest -c datahub/recipe_dbt.yml

clean: ## 清理临时文件
	@echo "$(GREEN)Cleaning temporary files...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
