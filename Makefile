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
EXEC_CMD := docker-compose exec -T api uv run
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

install: ## [内用] 使用 uv sync (内网 Nexus 3次重试 -> 清华兜底)
	@echo "$(GREEN)Tiered Sync (Nexus Primary x3 -> Tsinghua Fallback)...$(RESET)"
	$(EXEC_CMD) bash -c " \
		for i in 1 2 3; do \
			echo \"[Attempt $$i/3] Trying Nexus (8081)...\"; \
			uv sync --frozen --all-groups --index-url http://192.168.5.64:8081/repository/group-pypi/simple --trusted-host 192.168.5.64 && exit 0; \
			sleep 1; \
		done; \
		echo \"$(YELLOW)Nexus failed after 3 attempts. Pulling directly from Internet (Tsinghua)...$(RESET)\"; \
		uv sync --frozen --all-groups --index-url http://192.168.5.64:8081/repository/group-pypi/simple --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host 192.168.5.64; \
	"

init-dev: ## [本地] 使用 uv sync 初始化开发环境 (内网 Nexus 3次重试 -> 清华兜底)
	@echo "$(GREEN)Local Dev Init (Nexus Primary x3 -> Tsinghua Fallback)...$(RESET)"
	@powershell -Command " \
		for ($$i=1; $$i -le 3; $$i++) { \
			Write-Host \"[Attempt $$i/3] Trying Nexus (8081)...\" -ForegroundColor Yellow; \
			uv sync --all-groups --index-url http://192.168.5.64:8081/repository/group-pypi/simple --trusted-host 192.168.5.64; \
			if ($$?) { Write-Host \"Local environment successfully synced with Nexus!\" -ForegroundColor Cyan; exit 0 } \
			Start-Sleep -Seconds 1; \
		} \
		Write-Host \"Nexus failed after 3 attempts. Pulling directly from Internet (Tsinghua)...\" -ForegroundColor White; \
		uv sync --all-groups --index-url http://192.168.5.64:8081/repository/group-pypi/simple --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host 192.168.5.64; \
	"

lock: ## [工具] 使用 uv 锁定依赖 (内网 Nexus 3次重试 -> 清华兜底)
	@echo "$(GREEN)Locking Dependencies (Nexus Primary x3 -> Tsinghua Fallback)...$(RESET)"
	$(EXEC_CMD) bash -c " \
		for i in 1 2 3; do \
			echo \"[Attempt $$i/3] Trying Nexus (8081) for locking...\"; \
			uv lock --index-url http://192.168.5.64:8081/repository/group-pypi/simple --trusted-host 192.168.5.64 && break; \
			sleep 1; \
		done; \
		uv export --no-dev --format requirements-txt -o requirements.txt; \
	"

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

# NEXUS_PYPI_URL: PyPI 仓库必须使用 8081 端口；8082 是 Docker 专用。
NEXUS_PYPI_URL ?= http://192.168.5.64:8081/repository/group-pypi/simple

build: pull-images ## 构建 Docker 镜像 (Local First + BuildKit Cache)
	@echo "$(GREEN)Building Docker images with BuildKit cache & Nexus args...$(RESET)"
	@powershell -Command " \
		$$env:DOCKER_BUILDKIT=1; \
		$$env:COMPOSE_DOCKER_CLI_BUILD=1; \
		docker-compose build --build-arg UV_IMAGE=astral-sh/uv:latest --build-arg PIP_INDEX_URL=$(NEXUS_PYPI_URL) \
	"

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

lint: ## [本地] 代码质量检查 (Ruff Only)
	@echo "$(GREEN)Running Ruff check...$(RESET)"
	ruff check devops_collector/ devops_portal/ tests/ scripts/
#	@echo "$(GREEN)Running frontend line-limit check...$(RESET)"
#	python scripts/lint_frontend.py


fmt: ## [本地] 代码格式化 (Ruff Format)
	@echo "$(GREEN)Formatting code with Ruff...$(RESET)"
	ruff format devops_collector/ devops_portal/ tests/ scripts/
	@echo "$(GREEN)Optimizing imports and fixing small issues with Ruff...$(RESET)"
	ruff check --select I --fix devops_collector/ devops_portal/ tests/ scripts/

ruff-check: ## 使用 Ruff 进行代码质量检查
	@echo "$(GREEN)Running Ruff check...$(RESET)"
	ruff check devops_collector/ devops_portal/ tests/ scripts/

ruff-fmt: ## 使用 Ruff 进行代码格式化
	@echo "$(GREEN)Formatting code with Ruff...$(RESET)"
	ruff format devops_collector/ devops_portal/ tests/ scripts/

ruff-fix: ## 使用 Ruff 自动修复 (包含 Import 排序与逻辑漏洞)
	@echo "$(GREEN)Running Ruff check with --fix...$(RESET)"
	ruff check --fix devops_collector/ devops_portal/ tests/ scripts/

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
		$$images = @('python:3.11-slim-bookworm', 'postgres:15-alpine', 'rabbitmq:3-management-alpine', 'astral-sh/uv:latest'); \
		foreach ($$img in $$images) { \
			if (docker images -q $$img) { \
				Write-Host \"[1/3] Image $$img already exists locally, skipping.\" -ForegroundColor Cyan; \
				continue; \
			} \
			$$nexusImg = '$(NEXUS_DOCKER_REGISTRY)/' + $$img; \
			Write-Host \"[2/3] Attempting Nexus Pull: $$nexusImg ...\" -ForegroundColor Yellow; \
			& docker pull $$nexusImg 2>&1 | Out-Null; \
			if ($$LASTEXITCODE -eq 0) { \
				Write-Host \"[MATCH] Successfully pulled from Nexus! Tagging as $$img ...\" -ForegroundColor Green; \
				docker tag $$nexusImg $$img; \
				docker rmi $$nexusImg; \
				continue; \
			} \
			Write-Host \"[3/3] Nexus missed. Falling back to Official Hub for $$img ...\" -ForegroundColor White; \
			& docker pull $$img 2>&1 | Out-Null; \
			if ($$LASTEXITCODE -eq 0) { \
				Write-Host \"[MATCH] Successfully pulled from Official Hub!\" -ForegroundColor Green; \
			} else { \
				Write-Host \"[WARN] All pull attempts failed for $$img. Build might still work if cached elsewhere.\" -ForegroundColor Gray; \
			} \
		} \
		exit 0; \
	"

dbt-build: ## 执行 dbt 建模转换
	@echo "$(GREEN)Running dbt transformations...$(RESET)"
	$(EXEC_CMD) bash -c "cd dbt_project && dbt build"


# =============================================================================
# E2E 测试 (Playwright)
# =============================================================================

e2e-install: ## [本地] 安装 Playwright E2E 测试依赖
	@echo "$(GREEN)Installing E2E test dependencies with uv (Nexus -> Official -> Tsinghua)...$(RESET)"
	uv sync --extra e2e --index-url http://192.168.5.64:8082/repository/group-pypi/simple --trusted-host 192.168.5.64 || \
		uv sync --extra e2e || \
		uv sync --extra e2e --index-url https://pypi.tuna.tsinghua.edu.cn/simple
	playwright install chromium
	@echo "$(CYAN)E2E dependencies installed successfully with uv!$(RESET)"

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

full-gate: ## [MANDATORY] 核心卡点：代码合并前全量校验 (Lint -> Test -> Build)
	@echo "$(CYAN)Launching Project Full Gate (Grader 3)...$(RESET)"
	python scripts/gatekeeper.py --mode full

verify: ## [MANDATORY] 100% 验证防御：包含覆盖率审计的全量校验 (Lint -> Imports -> Test + Cov)
	@echo "$(CYAN)Launching Total Verification Defense (AGENTS.md SOP)...$(RESET)"
	$(MAKE) lint
	$(MAKE) check-imports
	@echo "$(GREEN)Running tests with coverage audit (Target: 80%)...$(RESET)"
	$(EXEC_CMD) pytest tests/unit/ tests/integration/ --cov=devops_collector --cov=devops_portal --cov-report=term-missing --cov-fail-under=80
	@echo "$(CYAN)Recommendation: Run 'make security-audit' for L3/L4 tasks.$(RESET)"

# =============================================================================
# 安全审计工具 (Python 原生版 - 依托 Nexus PyPI)
# =============================================================================

scan-secrets: ## [SECURITY] 源码机密审计 (detect-secrets)
	@echo "$(CYAN)Scanning for hardcoded secrets using detect-secrets...$(RESET)"
	$(EXEC_CMD) detect-secrets scan --baseline .secrets.baseline --exclude-files ".*/tests/.*" --exclude-files ".*\.lock"

scan-sast: ## [SECURITY] 代码静态安全审计 (Bandit)
	@echo "$(GREEN)Running Bandit SAST (Static Application Security Testing)...$(RESET)"
	$(EXEC_CMD) bandit -r devops_collector/ devops_portal/ -ll -o reports/security/bandit_report.json

scan-deps: ## [SECURITY] 依赖漏洞审计 (Safety)
	@echo "\033[1;33mChecking dependencies for known vulnerabilities using Safety...\033[0m"
	docker-compose exec -T api safety check --ignore 64459 --ignore 64396 --ignore 86269 --json > reports/security/safety_report.json

security-audit: scan-secrets scan-sast scan-deps ## [SECURITY] 全量安全卡点：源码 + 逻辑 + 依赖

fast-gate: ## [L2/CI] 快速卡点：跳过容器构建阶段
	python scripts/gatekeeper.py --mode fast


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
		Get-ChildItem -Path . -Include *.pyc,*.pyo,*.log,.coverage,*.tmp,traceback.txt,debug_output.txt,dbt_*.txt -File -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue; \
		# 3. 针对性清理 AI 调试/脚本残留 \
		Get-ChildItem -Path . -Include debug_*.py,test_tmp_*.py,tmp_*.py,parse_dbt_*.py,drop_b.py -File -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue; \
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

