# Dashboard 自动化巡检报告

测试时间: 2026-01-10 23:56:24

| 模块名称 | 状态 | 错误信息 |
| :--- | :--- | :--- |
| Gitprime | ✅ PASS |  |
| DORA Metrics | ✅ PASS |  |
| Project Health | ✅ PASS |  |
| Compliance Audit | ✅ PASS |  |
| ABI Analysis | ❌ FAILED | sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column "cognitive_complexity" does not exist LINE 6: cognitive_complexity, ^ [SQL: SELECT project_name, impact_in_degree, complexity_score, cognitive_complexity, coverage_pct, brittleness_index, architectural_health_status FROM public_marts.fct_architectural_brittleness ORDER BY brittleness_index DESC ] (Background on this error at: https://sqlalche.me/e/20/f405); sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column "cognitive_complexity" does not exist LINE 6: cognitive_complexity, ^ [SQL: SELECT project_name, impact_in_degree, complexity_score, cognitive_complexity, coverage_pct, brittleness_index, architectural_health_status FROM public_marts.fct_architectural_brittleness ORDER BY brittleness_index DESC ] (Background on this error at: https://sqlalche.me/e/20/f405) |
| User Profile | ✅ PASS |  |
| Capitalization Audit | ✅ PASS |  |
| Shadow IT | ✅ PASS |  |
| Talent Radar | ❌ FAILED | KeyError: 'department_id'; KeyError: 'department_id' |
| Metrics Guard | ❌ FAILED | KeyError: 'is_anomaly'; KeyError: 'is_anomaly' |
| Unified Activities | ❌ FAILED | sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column "author_name" does not exist LINE 5: author_name, ^ [SQL: SELECT occurred_at, activity_type, author_name, project_id, summary, base_impact_score FROM public_intermediate.int_unified_activities WHERE activity_type IN ('COMMIT','MR_MERGE') ORDER BY occurred_at DESC LIMIT 500 ] (Background on this error at: https://sqlalche.me/e/20/f405); sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column "author_name" does not exist LINE 5: author_name, ^ [SQL: SELECT occurred_at, activity_type, author_name, project_id, summary, base_impact_score FROM public_intermediate.int_unified_activities WHERE activity_type IN ('COMMIT','MR_MERGE') ORDER BY occurred_at DESC LIMIT 500 ] (Background on this error at: https://sqlalche.me/e/20/f405) |
| Work Items | ✅ PASS |  |
| Entity Alignment | ✅ PASS |  |
| Delivery Costs | ✅ PASS |  |
| Metadata Governance | ✅ PASS |  |
| Michael Feathers Code Hotspots | ⚠️ SKIPPED | Link not found in sidebar |
| SPACE Framework | ⚠️ SKIPPED | Link not found in sidebar |
| Value Stream | ⚠️ SKIPPED | Link not found in sidebar |
| Strategic Executive Cockpit | ⚠️ SKIPPED | Link not found in sidebar |
