
# Engineering Metrics Architecture (v2.0)

> **Version**: 2.0  
> **Last Updated**: 2026-01-04  
> **Scope**: ELOC 2.0, Flow Framework, SPACE, DORA, Code Hotspots

## 1. Overview

This document defines the comprehensive engineering metrics system implemented in the DevOps platform. It moves beyond simple "lines of code" to a multi-dimensional value stream management system tailored for modern engineering teams.

The system is built on four theoretical pillars:

1. **ELOC 2.0 (GitPrime Style)**: Quantifying engineer output with impact and rework contexts.
2. **DORA (Google)**: Measuring delivery speed and stability.
3. **SPACE (Microsoft/GitHub)**: Balancing productivity across 5 dimensions (including well-being).
4. **Flow Framework (Tasktop)**: Visualizing business value flow (Feature vs Debt).

---

## 2. Core Metrics Definitions

### 2.1 ELOC 2.0 (Equivalent Lines of Code)

Standardizes "effort" by weighting code changes based on context, reducing the bias of raw LOC.

| **ELOC Score** | The weighted coding volume. | `(Additions + Deletions) * FileWeight * ContextWeight` |
| **Impact Score** | Measures value of work, rewarding work on legacy code. | `ELOC Score * LegacyFactor` (LegacyFactor = 1.5 if file age > 180 days) |
| **Churn Lines** | Code rewritten shortly after being merged (Waste). | Lines modified within **21 days** of previous commit. |
| **Active Days** | Coding focus and consistency. | Count of distinct days with at least one commit. |
| **Sherpa Score** | Collaboration impact (Reviewer capability). | `ReviewCount * 5` points. |

### 2.2 Flow Framework (Value Stream)

Classifies all work items (Issues/Tickets) into four mutually exclusive categories to visualize "what we work on".

* **Classification Logic** (SQL View: `view_flow_items`):
    1. **🛡️ Risks**: Labels contain `security`, `compliance`, `risk`.
    2. **🐛 Defects**: Labels contain `bug`, `fix`, `incident`.
    3. **💰 Debts**: Labels contain `refactor`, `debt`, `cleanup`.
    4. **✨ Features**: Everything else (Default).

* **Metrics**:
  * **Flow Velocity**: Items completed per week.
  * **Flow Distribution**: % allocation across the 4 types (e.g., "Are we drowning in defects?").
  * **Flow Efficiency**: active_time / flow_time (Approx).

### 2.3 SPACE Framework

A balanced scorecard to prevent over-indexing on a single metric.

| Dimension | Implementation | Data Source |
| :--- | :--- | :--- |
| **S (Satisfaction)** | **DevEx Pulse** (Daily Mood Check) | `satisfaction_records` (Sidebar Widget) |
| **P (Performance)** | **DORA Metrics** (Deploy Freq, CFR) | `fct_dora_metrics` |
| **A (Activity)** | **ELOC / Commit Volume** | `commit_metrics` |
| **C (Collaboration)** | **Sherpa Score** (Code Reviews) | `daily_dev_stats` |
| **E (Efficiency)** | **Flow Time** / Lead Time | `view_flow_metrics` |

### 2.4 Code Hotspots (Risk Analysis)

Based on **Michael Feathers' F-C Analysis**, identifying high-risk technical debt.

* **X-Axis (Complexity)**: Estimated Lines of Code (Net Growth).
* **Y-Axis (Churn)**: Frequency of changes in last 90 days.
* **Actionable Insight**: Files in the "Top-Right" quadrant (High Complexity + High Churn) are **Refactoring Candidates**.

---

## 3. Implementation Architecture

### 3.1 Data Flow

```mermaid
graph LR
    GitLab[GitLab Worker] --> |Raw Commits| DB[(PostgreSQL)]
    Jira[Jira Worker] --> |Raw Issues| DB
    
    subgraph "Analytics Layer (SQL Views)"
        DB --> V1[ELOC Logic (Python)]
        DB --> V2[Value_Stream.sql]
        DB --> V3[project_health.sql]
        DB --> V4[Michael_Feathers_Code_Hotspots.sql]
    end
    
    subgraph "Presentation Layer (Streamlit)"
        V1 --> P0[0_Gitprime.py]
        V2 --> P17[17_Value_Stream.py]
        V3 --> P2[2_Project_Health.py]
        V4 --> P15[15_Michael_Feathers_Code_Hotspots.py]
    end
```

### 3.2 File Mapping Structure

To ensure maintainability, Dashboard Pages are strictly mapped to underlying SQL definitions where applicable.

| Python Dashboard Page | SQL Definition File (`devops_collector/sql/`) |
| :--- | :--- |
| `0_Gitprime.py` | `Gitprime.sql` |
| `2_Project_Health.py` | `Project_Health.sql` |
| `3_Compliance_Audit.py` | `Compliance_Audit.sql` |
| `4_ABI_Analysis.py` | `ABI_Analysis.sql` |
| `5_User_Profile.py` | `User_Profile.sql` |
| `6_Capitalization_Audit.py` | `Capitalization_Audit.sql` |
| `8_Talent_Radar.py` | `Talent_Radar.sql` |
| `11_Work_Items.py` | `Work_Items.sql` |
| `15_Michael_Feathers_Code_Hotspots.py` | `Michael_Feathers_Code_Hotspots.sql` |
| `16_SPACE_Framework.py` | `SPACE_Framework.sql` |
| `17_Value_Stream.py` | `Value_Stream.sql` |

---

## 4. Key Configuration

### 4.1 Satisfaction Survey (Pulse)

* **Mechanism**: A simplified "Niko-Niko" calendar implemented as a Streamlit sidebar widget.
* **Storage**: `satisfaction_records` table.
* **Privacy**: Currently linked to user email; requires RBAC for viewing aggregate data.

### 4.2 Legacy Code Thresholds

* **Legacy Age**: 180 days (Configurable in `ELOCAnalyzer`).
* **Churn Window**: 21 days.
