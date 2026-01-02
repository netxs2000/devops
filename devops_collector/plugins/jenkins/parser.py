"""Jenkins 测试报告解析器

负责将 Jenkins API 返回的 testReport JSON 解析为系统的 TestExecutionSummary 模型。
"""
import logging
from typing import Dict, Any, Optional
from devops_collector.models.base_models import TestExecutionSummary
logger = logging.getLogger(__name__)

class ReportParser:
    """Jenkins 测试报告解析器。"""

    @staticmethod
    def parse_jenkins_test_report(project_id: Optional[int], build_id: str, report_data: Dict[str, Any], job_name: str='') -> Optional[TestExecutionSummary]:
        """将 Jenkins testReport 转换为 TestExecutionSummary。
        
        Args:
            project_id: 关联的 GitLab 项目 ID。
            build_id: 构建 ID (通常是 Jenkins Build Number)。
            report_data: Jenkins /testReport/api/json 返回的原始数据。
            job_name: 任务名称，用于辅助判断测试层级。
            
        Returns:
            TestExecutionSummary 对象或 None。
        """
        if not report_data:
            return None
        try:
            total = report_data.get('totalCount', 0)
            failed = report_data.get('failCount', 0)
            skipped = report_data.get('skipCount', 0)
            passed = total - failed - skipped
            duration_s = report_data.get('duration', 0)
            duration_ms = int(duration_s * 1000)
            test_level = 'Automation'
            job_name_lower = job_name.lower()
            if 'unit' in job_name_lower or 'ut' in job_name_lower:
                test_level = 'Unit'
            elif 'api' in job_name_lower or 'interface' in job_name_lower:
                test_level = 'API'
            elif 'ui' in job_name_lower or 'web' in job_name_lower or 'e2e' in job_name_lower:
                test_level = 'UI'
            elif 'perf' in job_name_lower or 'stress' in job_name_lower:
                test_level = 'Performance'
            pass_rate = 0.0
            if total > 0:
                pass_rate = passed / total * 100
            summary = TestExecutionSummary(project_id=project_id, build_id=build_id, test_level=test_level, test_tool='Jenkins/JUnit', total_cases=total, passed_count=passed, failed_count=failed, skipped_count=skipped, pass_rate=pass_rate, duration_ms=duration_ms, raw_data=report_data)
            return summary
        except Exception as e:
            logger.error(f'Failed to parse Jenkins test report: {e}')
            return None