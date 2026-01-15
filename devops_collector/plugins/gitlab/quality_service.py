"""GitLab 质量分析业务服务层。

该模块封装了“质量分析模块”的核心业务逻辑，包括：
1. 质量门禁检查 (Quality Gate)
2. 变更请求分析 (MR Analytics)
3. 质量报告生成
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.gitlab.test_management_service import TestManagementService
from devops_portal import schemas

logger = logging.getLogger(__name__)

class QualityService:
    """GitLab 质量分析业务逻辑服务。"""

    def __init__(self, session: Session, client: GitLabClient):
        """初始化质量服务。

        Args:
            session (Session): 数据库会话。
            client (GitLabClient): GitLab API 客户端。
        """
        self.session = session
        self.client = client
        self.test_service = TestManagementService(session, client)

    async def get_quality_gate_status(self, project_id: int, current_user: Any) -> schemas.QualityGateStatus:
        """执行质量门禁检查。"""
        # 1. 需求覆盖率检查
        reqs = await self.test_service.list_requirements(project_id, current_user, self.session)
        approved_reqs = [r for r in reqs if r.review_state == 'approved']
        
        req_covered = False
        if approved_reqs:
            details = await asyncio.gather(*[self.test_service.get_requirement_detail(project_id, r.iid) for r in approved_reqs])
            covered_count = sum((1 for r in details if r and len(r.test_cases) > 0))
            coverage_rate = covered_count / len(approved_reqs) * 100
            req_covered = coverage_rate >= 80.0
            
        # 2. P0 Bug 检查 (从 Client 获取)
        all_issues = list(self.client.get_project_issues(project_id))
        p0_count = sum(1 for issue in all_issues if 'type::bug' in issue.get('labels', []) and 'severity::S0' in issue.get('labels', []) and issue['state'] == 'opened')
        p0_cleared = p0_count == 0
        
        # 3. 流水线健康度
        pipelines = list(self.client.get_project_pipelines(project_id, per_page=1))
        pipe_stable = pipelines[0]['status'] == 'success' if pipelines else False
            
        # 4. 地域风险检查
        prov_stats = {}
        for issue in all_issues:
            if 'type::bug' not in issue.get('labels', []):
                continue
            prov = 'nationwide'
            for l in issue.get('labels', []):
                if l.startswith('province::'):
                    prov = l.split('::')[1]
                    break
            prov_stats[prov] = prov_stats.get(prov, 0) + 1
        regional_free = all(count <= 10 for count in prov_stats.values())
        
        is_all_passed = all([req_covered, p0_cleared, pipe_stable, regional_free])
        summary = '质量门禁通过，准予发布。' if is_all_passed else '质量门禁拦截，存在合规性风险。'
        
        return schemas.QualityGateStatus(
            is_passed=is_all_passed,
            requirements_covered=req_covered,
            p0_bugs_cleared=p0_cleared,
            pipeline_stable=pipe_stable,
            regional_risk_free=regional_free,
            summary=summary
        )

    async def get_mr_analytics(self, project_id: int) -> Dict[str, Any]:
        """获取合并请求分析统计。"""
        return await self.test_service.get_mr_summary_stats(project_id)

    async def generate_report(self, project_id: int) -> str:
        """生成质量报告 Markdown。"""
        return await self.test_service.generate_quality_report(project_id)
