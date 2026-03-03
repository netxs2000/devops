# DevOps Platform 自动化运维方案
# -----------------------------------------------------------
#  标准化 Docker 部署与运维命令规范
#  所有操作均在容器内部执行，确保环境一致性
# -----------------------------------------------------------

.PHONY: help deploy init test test-local test-int-local test-all lint fmt diagnose check-imports build up down logs sync-all shell clean lock install init-dev docs e2e-install e2e-test e2e-test-headed e2e-test-trace e2e-smoke e2e-show-trace

# 颜色定义
YELLOW := \033[1;33m
GREEN := \033[1;32m
CYAN := \033[1;36m
RESET := \033[0m

# 统一执行前缀：在 api 容器中执行 (使用 -T 避免 TTY 问题)
EXEC_CMD := docker-compose exec -T api
NEXUS_DOCKER_REGISTRY ?= 192.168.5.64:8082

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'

# =============================================================================
# 核心部署流程 (One-Click Deployment)
# =============================================================================

deploy: down build up init docs ## [一键部署] 重建镜像 -> 启动服务 -> 初始化数据 -> 更新文档
	@echo "$(CYAN)DevOps Platform deployed successfully!$(RESET)"

init: ## [初始化] 在容器内安装依赖并重置并初始化数据库数据
	@echo "$(GREEN)Initializing data inside container...$(RESET)"
	$(MAKE) install
	$(EXEC_CMD) python scripts/reset_database.py
	$(EXEC_CMD) python -m devops_collector.utils.schema_sync
	$(EXEC_CMD) python scripts/init_rbac.py
	$(EXEC_CMD) python scripts/import_employees.py
	$(EXEC_CMD) python scripts/init_organizations.py
	$(EXEC_CMD) python scripts/init_products_projects.py
	$(EXEC_CMD) python scripts/link_users_to_entities.py
	$(EXEC_CMD) python scripts/init_okrs.py
	$(EXEC_CMD) python scripts/init_calendar.py
	$(EXEC_CMD) python scripts/init_mdm_location.py
	$(EXEC_CMD) python scripts/init_cost_codes.py
	$(EXEC_CMD) python scripts/init_labor_rates.py
	$(EXEC_CMD) python scripts/init_purchase_contracts.py
	$(EXEC_CMD) python scripts/init_revenue_contracts.py
	$(EXEC_CMD) python scripts/init_catalog.py
	$(EXEC_CMD) python scripts/init_discovery.py
	$(EXEC_CMD) python scripts/init_gitlab_mappings.py
	$(EXEC_CMD) python scripts/init_zentao_mappings.py

install: ## [内用] 安装生产环境或开发环境依赖
	@echo "$(GREEN)Installing dependencies (Nexus -> Official -> Tsinghua)...$(RESET)"
	$(EXEC_CMD) bash -c "pip install --no-build-isolation --default-timeout=5 -i http://192.168.5.64:8082/repository/group-pypi/simple --trusted-host 192.168.5.64 . || \
		pip install --no-build-isolation --default-timeout=30 . || \
		pip install --no-build-isolation -i https://pypi.tuna.tsinghua.edu.cn/simple --default-timeout=60 ."

init-dev: ## [本地] 初始化开发环境依赖 (Nexus优先)
	@echo "$(GREEN)Initializing local development environment (Nexus -> Official -> Tsinghua)...$(RESET)"
	python -m pip install --upgrade pip -i http://192.168.5.64:8082/repository/group-pypi/simple --trusted-host 192.168.5.64 || python -m pip install --upgrade pip || python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
	pip install -e .[dev] -i http://192.168.5.64:8082/repository/group-pypi/simple --trusted-host 192.168.5.64 || pip install -e .[dev] || pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .[dev]
	@echo "$(CYAN)Local environment initialized successfully!$(RESET)"

lock: ## [工具] 将 pyproject.toml 的依赖锁定到 requirements.txt
	@echo "$(GREEN)Locking dependencies (Nexus -> Official -> Tsinghua)...$(RESET)"
	$(EXEC_CMD) bash -c "pip-compile pyproject.toml -o requirements.txt --resolver=backtracking --no-header -i http://192.168.5.64:8082/repository/group-pypi/simple --trusted-host 192.168.5.64 || \
		pip-compile pyproject.toml -o requirements.txt --resolver=backtracking --no-header || \
		pip-compile pyproject.toml -o requirements.txt --resolver=backtracking --no-header -i https://pypi.tuna.tsinghua.edu.cn/simple"

# =============================================================================
# 离线包构建与部署 (Offline Deployment)
# =============================================================================

package: pull-images ## [本地构建] 构建并打包镜像为 tar 文件 (devops-platform.tar)
	@echo "$(GREEN)Building Docker images with BuildKit...$(RESET)"
	@powershell -Command "$$env:DOCKER_BUILDKIT=1; docker build -t devops-platform:latest ."
# docker build -t devops-platform-datahub:latest datahub/
	@echo "$(GREEN)Saving images to devops-platform.tar...$(RESET)"
	docker save -o devops-platform.tar devops-platform:latest
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
	$(PROD_CMD) exec -T api python -m devops_collector.utils.schema_sync
	$(PROD_CMD) exec -T api python scripts/init_rbac.py
	$(PROD_CMD) exec -T api python scripts/init_organizations.py
	$(PROD_CMD) exec -T api python scripts/init_products_projects.py
	$(PROD_CMD) exec -T api python scripts/import_employees.py
	$(PROD_CMD) exec -T api python scripts/link_users_to_entities.py
	$(PROD_CMD) exec -T api python scripts/init_okrs.py
	$(PROD_CMD) exec -T api python scripts/init_calendar.py
	$(PROD_CMD) exec -T api python scripts/init_mdm_location.py
	$(PROD_CMD) exec -T api python scripts/init_cost_codes.py
	$(PROD_CMD) exec -T api python scripts/init_labor_rates.py
	$(PROD_CMD) exec -T api python scripts/init_purchase_contracts.py
	$(PROD_CMD) exec -T api python scripts/init_revenue_contracts.py
	$(PROD_CMD) exec -T api python scripts/init_catalog.py
	$(PROD_CMD) exec -T api python scripts/init_discovery.py
	$(PROD_CMD) exec -T api python scripts/init_gitlab_mappings.py
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
	$(PROD_CMD) exec -T api python -m devops_collector.utils.schema_sync
	$(PROD_CMD) exec -T api python scripts/init_rbac.py
	$(PROD_CMD) exec -T api python scripts/init_organizations.py
	$(PROD_CMD) exec -T api python scripts/init_products_projects.py
	$(PROD_CMD) exec -T api python scripts/import_employees.py
	$(PROD_CMD) exec -T api python scripts/link_users_to_entities.py
	$(PROD_CMD) exec -T api python scripts/init_okrs.py
	$(PROD_CMD) exec -T api python scripts/init_calendar.py
	$(PROD_CMD) exec -T api python scripts/init_mdm_location.py
	$(PROD_CMD) exec -T api python scripts/init_cost_codes.py
	$(PROD_CMD) exec -T api python scripts/init_labor_rates.py
	$(PROD_CMD) exec -T api python scripts/init_purchase_contracts.py
	$(PROD_CMD) exec -T api python scripts/init_revenue_contracts.py
	$(PROD_CMD) exec -T api python scripts/init_catalog.py
	$(PROD_CMD) exec -T api python scripts/init_discovery.py
	$(PROD_CMD) exec -T api python scripts/init_gitlab_mappings.py
	@echo "$(CYAN)Production deployment completed successfully!$(RESET)"

prod-logs: ## [服务器专用] 查看生产日志
	$(PROD_CMD) logs -f --tail=100

prod-down: ## [服务器专用] 停止生产服务
	$(PROD_CMD) down

# =============================================================================
# Docker 基础操作
# =============================================================================

build: pull-images ## 构建 Docker 镜像 (Local First + BuildKit Cache)
	@echo "$(GREEN)Building Docker images with BuildKit cache...$(RESET)"
	@powershell -Command "$$env:DOCKER_BUILDKIT=1; $$env:COMPOSE_DOCKER_CLI_BUILD=1; docker-compose build"

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

test: ## 运行单元+集成测试 (容器内)
	@echo "$(GREEN)Running unit and integration tests (inside container)...$(RESET)"
	$(EXEC_CMD) pytest tests/unit/ tests/integration/ -v

test-local: ## [本地] 运行单元测试 (快速验证)
	@echo "$(GREEN)Running unit tests locally...$(RESET)"
	pytest tests/unit/ -v

test-int-local: ## [本地] 运行集成测试 (如授权、同步流)
	@echo "$(GREEN)Running integration tests locally...$(RESET)"
	pytest tests/integration/ -v

test-all: ## [本地] 运行全量测试 (单元+集成)
	@echo "$(GREEN)Running all tests locally...$(RESET)"
	pytest tests/unit/ tests/integration/ -v

lint: ## [本地] 代码质量检查 (flake8, pylint, frontend)
	@echo "$(GREEN)Running flake8 check...$(RESET)"
	flake8 devops_collector/ devops_portal/
	@echo "$(GREEN)Running pylint check...$(RESET)"
	pylint devops_collector/ devops_portal/
	@echo "$(GREEN)Running frontend line-limit check...$(RESET)"
	python scripts/lint_frontend.py


fmt: ## [本地] 代码格式化 (black)
	@echo "$(GREEN)Formatting code with black...$(RESET)"
	black devops_collector/ devops_portal/ tests/ scripts/

ruff-check: ## [实验] 使用 Ruff 进行代码质量检查
	@echo "$(GREEN)Running Ruff check...$(RESET)"
	ruff check devops_collector/ devops_portal/ tests/ scripts/

ruff-fmt: ## [实验] 使用 Ruff 进行代码格式化
	@echo "$(GREEN)Formatting code with Ruff...$(RESET)"
	ruff format devops_collector/ devops_portal/ tests/ scripts/

ruff-fix: ## [实验] 使用 Ruff 自动修复 (仅限 Import 排序)
	@echo "$(GREEN)Running Ruff check with --select I --fix...$(RESET)"
	ruff check --select I --fix devops_collector/ devops_portal/ tests/ scripts/

diagnose: ## [本地] 系统综合诊断 (API, DB, Config)
	@echo "$(GREEN)Running system diagnosis...$(RESET)"
	python scripts/sys_diagnose.py

diag-db: ## [本地] 数据库专项诊断
	@echo "$(GREEN)Running database diagnosis...$(RESET)"
	python scripts/diag_db.py

diag-mq: ## [本地] 消息队列专项诊断
	@echo "$(GREEN)Running RabbitMQ diagnosis...$(RESET)"
	python scripts/diag_mq.py

check-imports: ## [本地] 检查核心模块导入依赖
	@echo "$(GREEN)Checking module imports...$(RESET)"
	python scripts/check_imports.py

sync-all: ## 手动触发全量数据同步
	@echo "$(GREEN)Triggering full sync...$(RESET)"
	$(EXEC_CMD) python -m devops_collector.scheduler --force-all
	$(EXEC_CMD) python -m devops_collector.worker --once

pull-images: ## [工具] 尝试从 Nexus 预拉取基础镜像并打标 (Fallback 机制)
	@echo "$(GREEN)Checking base images (Local First Strategy)...$(RESET)"
	@powershell -Command " \
		$$images = @('python:3.11-slim-bookworm', 'postgres:15-alpine', 'rabbitmq:3-management-alpine'); \
		foreach ($$img in $$images) { \
			if (docker images -q $$img) { \
				Write-Host \"Image $$img already exists locally, skipping pull.\" -ForegroundColor Cyan; \
				continue; \
			} \
			$$nexusImg = '$(NEXUS_DOCKER_REGISTRY)/' + $$img; \
			Write-Host \"Pulling $$nexusImg ...\"; \
			docker pull $$nexusImg 2>$$null; \
			if ($$?) { \
				Write-Host \"Tagging $$nexusImg as $$img ...\" -ForegroundColor Green; \
				docker tag $$nexusImg $$img; \
			} else { \
				Write-Host \"Nexus pull failed and $$img not found locally, will use default registry during build.\" -ForegroundColor Yellow; \
			} \
		} \
	"

dbt-build: ## 执行 dbt 建模转换
	@echo "$(GREEN)Running dbt transformations...$(RESET)"
	$(EXEC_CMD) bash -c "cd dbt_project && dbt build"

validate: ## 执行数据质量校验 (Great Expectations)
	@echo "$(GREEN)Running Data Quality Validation...$(RESET)"
	$(EXEC_CMD) python scripts/validate_models.py

# =============================================================================
# E2E 测试 (Playwright)
# =============================================================================

e2e-install: ## [本地] 安装 Playwright E2E 测试依赖
	@echo "$(GREEN)Installing E2E test dependencies (Nexus -> Official -> Tsinghua)...$(RESET)"
	pip install -e .[e2e] -i http://192.168.5.64:8082/repository/group-pypi/simple --trusted-host 192.168.5.64 || \
		pip install -e .[e2e] || pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .[e2e]
	playwright install chromium
	@echo "$(CYAN)E2E dependencies installed successfully!$(RESET)"

e2e-test: ## [本地] 运行 Service Desk E2E 测试 (无头模式)
	@echo "$(GREEN)Running E2E tests (headless)...$(RESET)"
	pytest tests/e2e/service_desk/ -v --headed=false

e2e-test-headed: ## [本地] 运行 E2E 测试 (可视化模式, 用于调试)
	@echo "$(GREEN)Running E2E tests (headed mode for debugging)...$(RESET)"
	pytest tests/e2e/service_desk/ -v --headed

e2e-test-trace: ## [本地] 运行 E2E 测试并保留失败追踪
	@echo "$(GREEN)Running E2E tests with tracing...$(RESET)"
	pytest tests/e2e/service_desk/ -v --tracing=retain-on-failure

e2e-smoke: ## [本地] 运行 E2E 冒烟测试 (快速验证)
	@echo "$(GREEN)Running E2E smoke tests...$(RESET)"
	pytest tests/e2e/service_desk/ -v -m smoke

e2e-show-trace: ## [本地] 打开 Playwright Trace Viewer 分析失败测试
	@echo "$(GREEN)Opening Playwright Trace Viewer...$(RESET)"
	playwright show-trace test-results/


# 定义 DataHub CLI 运行命令 (临时容器)
DATAHUB_CMD := docker-compose run --rm datahub-cli

datahub-ingest: ## 同步元数据到 DataHub (PostgreSQL & dbt)
	@echo "$(GREEN)Ingesting metadata to DataHub...$(RESET)"
	$(DATAHUB_CMD) datahub ingest -c datahub/recipe_postgres.yml
	$(DATAHUB_CMD) datahub ingest -c datahub/recipe_dbt.yml

clean: ## [增强] 清理所有临时文件、日志和 AI 调试脚本 (Environment Hygiene)
	@echo "$(GREEN)Cleaning temporary files and test artifacts...$(RESET)"
	@powershell -Command " \
		# 1. 清理 Python 编译缓存 \
		Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; \
		# 2. 清理通用垃圾后缀 (保持 .env 完整) \
		Get-ChildItem -Path . -Include *.pyc,*.pyo,*.log,.coverage,*.tmp,traceback.txt,debug_output.txt -File -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue; \
		# 3. 针对性清理 AI 调试/脚本残留 \
		Get-ChildItem -Path . -Include debug_*.py,test_tmp_*.py,tmp_*.py -File -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue; \
		# 4. 清理测试产出文件夹 \
		if (Test-Path htmlcov) { Remove-Item -Path htmlcov -Recurse -Force }; \
		if (Test-Path .pytest_cache) { Remove-Item -Path .pytest_cache -Recurse -Force }; \
		if (Test-Path .ruff_cache) { Remove-Item -Path .ruff_cache -Recurse -Force }; \
		if (Test-Path test-results) { Remove-Item -Path test-results -Recurse -Force }; \
	"

# =============================================================================
# 文档生成工具
# =============================================================================

docs: ## [工具] 自动生成/更新数据字典文档
	@echo "$(GREEN)Generating Data Dictionary...$(RESET)"
	$(EXEC_CMD) python scripts/generate_data_dictionary.py
	@echo "$(CYAN)Data Dictionary updated: docs/api/DATA_DICTIONARY.md$(RESET)"

