# Project Contexts

## Overview
**DevOps Data Application Platform** is an enterprise-grade R&D efficiency data collection and analysis platform. It aggregates data from GitLab, SonarQube, Jenkins, etc., to provide actionable insights.

## Core Architecture
- **Tech Stack**: Python 3.9+ (Backend), PostgreSQL (DB), dbt (Transformation), Streamlit (Frontend/Dashboard).
- **Component Model**: Micro-kernel + Plugin Factory pattern (`devops_collector/plugins/`).
- **Data Flow**: Airbyte (Extract) -> PostgreSQL (Load) -> dbt (Transform/Data Warehouse) -> SQL Views/API -> Streamlit.
- **Dependency Management**: `pyproject.toml` (Source) -> `requirements.txt` (Lock via `pip-compile`).
- **Deployment**: Docker Compose (Dev/Prod/Offline modes).

## Key Principles & Rules
1.  **First Principles**: Analyze problems from the ground up using existing tools.
2.  **Fact-Based**: Correct errors immediately; assume "Minimum Viable Changes".
3.  **Environment**: 
    - Windows (Local Dev) / Linux (Container).
    - Config via `.env` (12-Factor App).
    - Cross-platform compatibility (Pathlib, etc.).
4.  **Naming & Consistency**: 
    - Align names across DB -> Model -> API -> Frontend.
    - Strict Google Style for Python.
    - Mandatory comments/docstrings.
5.  **Validation**: `make deploy` triggers full containerized deployment & initialization.

## Directory Structure
- `devops_collector/`: Core Python application.
    - `core/`: Base classes (Client, Worker, Registry).
    - `plugins/`: Data source implementations (GitLab, SonarQube, etc.).
    - `models/`: SQLAlchemy models.
- `dbt_project/`: Data transformation models.
- `docs/`: Documentation.
- `scripts/`: Initialization and utility scripts.
- `Makefile`: Operation automation.

## Critical Workflows
- **New Feature**: Plan -> Review -> Task -> Confirm -> Execute.
- **SSL/Connectivity**: `BaseClient` supports `verify_ssl` config via `GITLAB__VERIFY_SSL`.
