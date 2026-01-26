# Project Contexts

## Overview
**DevOps Data Application Platform** is an enterprise-grade R&D efficiency data collection and analysis platform. It aggregates data from GitLab, SonarQube, Jenkins, etc., to provide actionable insights.

## Core Architecture
- **Tech Stack**: Python 3.12 (Backend), PostgreSQL (DB), dbt (Transformation), Native Portal (Vanilla JS/CSS, Apple Style), Streamlit (Internal BI/Reporting).
- **Component Model**: 
    - **Backend**: Micro-kernel + Plugin Factory pattern (`devops_collector/plugins/`).
    - **Frontend**: Component-based architecture using Browser-native Web Components (Shadow DOM).
- **Data Flow**: Airbyte (Extract) -> PostgreSQL (Load) -> dbt (Transform) -> FastAPI/SQL -> Native Portal / Streamlit.
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
    - **Domain Prefixes**: Mandatory application of prefixes (e.g., `qa_` for Test Management, `sd_` for Service Desk).
    - Strict Google Style for Python.
    - **Frontend Convention**: Follow `docs/frontend/CONVENTIONS.md` for Native CSS & JS standards (Apple Style).
5.  **Validation**: `make deploy` triggers full containerized deployment & initialization.

## Directory Structure
- `devops_collector/`: Core Python application logic and data collection.
- `devops_portal/`: FastAPI backend and Native Frontend (HTML/JS/CSS).
    - `static/js/components/`: Web Component implementations.
    - `static/js/modules/`: Domain-specific business logic (e.g., `qa_test_cases.js`).
- `dbt_project/`: Data transformation models.
- `docs/`: Documentation.
- `scripts/`: Initialization and utility scripts.
- `Makefile`: Operation automation.

## Critical Workflows
- **New Feature**: Plan -> Review -> Task -> Confirm -> Execute.
- **SSL/Connectivity**: `BaseClient` supports `verify_ssl` config via `GITLAB__VERIFY_SSL`.
