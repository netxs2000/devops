# 文档整理脚本
# 将根目录的文档移动到 docs/ 子目录

# 架构文档 -> docs/architecture/
Move-Item -Path "ARCHITECTURE.md" -Destination "docs\architecture\" -Force
Move-Item -Path "Technical_Architecture.md" -Destination "docs\architecture\" -Force
Move-Item -Path "Planning_and_Design.md" -Destination "docs\architecture\" -Force

# 用户指南 -> docs/guides/
Move-Item -Path "USER_GUIDE.md" -Destination "docs\guides\" -Force
Move-Item -Path "DEPLOYMENT.md" -Destination "docs\guides\" -Force
Move-Item -Path "CONTRIBUTING.md" -Destination "docs\guides\" -Force
Move-Item -Path "TEST_STRATEGY.md" -Destination "docs\guides\" -Force

# 分析方案 -> docs/analytics/
Move-Item -Path "PMO_ANALYTICS_PLAN.md" -Destination "docs\analytics\" -Force
Move-Item -Path "HR_ANALYTICS_PLAN.md" -Destination "docs\analytics\" -Force
Move-Item -Path "TEAM_ANALYTICS_PLAN.md" -Destination "docs\analytics\" -Force
Move-Item -Path "FINANCE_ANALYTICS_GUIDE.md" -Destination "docs\analytics\" -Force
Move-Item -Path "COMPLIANCE_ANALYTICS_GUIDE.md" -Destination "docs\analytics\" -Force
Move-Item -Path "METRIC_THRESHOLDS_GUIDE.md" -Destination "docs\analytics\" -Force

# API 与数据 -> docs/api/
Move-Item -Path "DATA_DICTIONARY.md" -Destination "docs\api\" -Force
Move-Item -Path "DATA_GOVERNANCE.md" -Destination "docs\api\" -Force
Move-Item -Path "GITLAB_METRICS_DATA_SOURCES.md" -Destination "docs\api\" -Force
Move-Item -Path "Updated_Data_Dictionary.md" -Destination "docs\api\" -Force

# 功能指南 -> docs/guides/
Move-Item -Path "ISSUE_LABEL_ENFORCEMENT_GUIDE.md" -Destination "docs\guides\" -Force
Move-Item -Path "DEPENDENCY_CHECK_IMPLEMENTATION_GUIDE.md" -Destination "docs\guides\" -Force
Move-Item -Path "DEPENDENCY_CHECK_PERSISTENT_STORAGE_GUIDE.md" -Destination "docs\guides\" -Force
Move-Item -Path "DEPENDENCY_CHECK_COMPLETE.md" -Destination "docs\guides\" -Force
Move-Item -Path "OWASP_DEPENDENCY_CHECK_INTEGRATION.md" -Destination "docs\guides\" -Force

# 项目管理文档 -> docs/
Move-Item -Path "PROJECT_OVERVIEW.md" -Destination "docs\" -Force
Move-Item -Path "PROJECT_SUMMARY_AND_MANUAL.md" -Destination "docs\" -Force
Move-Item -Path "REQUIREMENTS_SPECIFICATION.md" -Destination "docs\" -Force
Move-Item -Path "CHANGELOG.md" -Destination "docs\" -Force
Move-Item -Path "DOCUMENTATION_UPDATE_SUMMARY.md" -Destination "docs\" -Force

# 其他说明文档 -> docs/guides/
Move-Item -Path "活跃度定义说明.md" -Destination "docs\guides\" -Force
Move-Item -Path "netxs.md" -Destination "docs\" -Force

Write-Host "文档整理完成!" -ForegroundColor Green
