.PHONY: help install install-dev test lint format clean init-db deploy-views run-scheduler run-worker verify-data

# 默认目标
help:
	@echo "DevOps Collector - 常用命令"
	@echo ""
	@echo "环境管理:"
	@echo "  make install          - 安装生产依赖"
	@echo "  make install-dev      - 安装开发依赖"
	@echo "  make clean            - 清理临时文件"
	@echo ""
	@echo "数据库管理:"
	@echo "  make init-db          - 初始化数据库和组织架构"
	@echo "  make deploy-views     - 部署分析视图到数据库"
	@echo ""
	@echo "代码质量:"
	@echo "  make test             - 运行单元测试"
	@echo "  make test-cov         - 运行测试并生成覆盖率报告"
	@echo "  make lint             - 代码检查 (flake8)"
	@echo "  make format           - 代码格式化 (black)"
	@echo "  make type-check       - 类型检查 (mypy)"
	@echo ""
	@echo "运行服务:"
	@echo "  make run-scheduler    - 启动调度器"
	@echo "  make run-worker       - 启动数据采集 Worker"
	@echo ""
	@echo "数据验证:"
	@echo "  make verify-data      - 运行数据完整性验证"

# 环境管理
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -e .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache .coverage htmlcov/ dist/ build/ *.egg-info

# 数据库管理
init-db:
	python scripts/init_discovery.py
	python scripts/init_cost_codes.py
	python scripts/init_labor_rates.py

deploy-views:
	@echo "请手动执行以下命令部署视图:"
	@echo "psql -d devops_db -f devops_collector/sql/PROJECT_OVERVIEW.sql"
	@echo "psql -d devops_db -f devops_collector/sql/PMO_ANALYTICS.sql"
	@echo "psql -d devops_db -f devops_collector/sql/HR_ANALYTICS.sql"

# 代码质量
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=devops_collector --cov-report=html --cov-report=term

lint:
	flake8 devops_collector/ tests/ scripts/ --max-line-length=100 --exclude=__pycache__

format:
	black devops_collector/ tests/ scripts/ --line-length=100

type-check:
	mypy devops_collector/ --ignore-missing-imports

# 运行服务
run-scheduler:
	python -m devops_collector.scheduler

run-worker:
	python -m devops_collector.worker

# 数据验证
verify-data:
	@echo "请指定项目 ID: make verify-data PROJECT_ID=123"
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "错误: 请设置 PROJECT_ID 参数"; \
		exit 1; \
	fi
	python scripts/verify_data_integrity.py --project-id $(PROJECT_ID)
