"""DORA Lead Time for Changes 专项测试用例

验证从首次提交到最终部署的全链路耗时计算逻辑。
"""

import unittest
from datetime import datetime, timedelta, timezone
from tests.analytics.metric_validator import MetricValidatorFramework
from devops_collector.plugins.gitlab.models import Project, MergeRequest, Commit, Deployment

class TestLeadTimeScenarios(MetricValidatorFramework):
    """验证 Lead Time for Changes 核心指标。"""

    def test_end_to_end_lead_time(self):
        """测试一个完整的全链路交付场景。
        
        场景描述:
        1. 2025-01-01 10:00: 首次提交 (Commit A)
        2. 2025-01-01 12:00: 创建 MR (MR 1)
        3. 2025-01-01 14:00: MR 合并 (Merged)
        4. 2025-01-01 16:00: 部署到生产 (Deployment Success)
        
        预期结果:
        - 编码时间: 2h (7200s)
        - 评审时间: 2h (7200s)
        - 部署时间: 2h (7200s)
        - 总交付时间: 6h (21600s)
        """
        # 1. 设置时间断点 (使用 UTC)
        base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        commit_at = base_time
        mr_created_at = base_time + timedelta(hours=2)
        mr_merged_at = base_time + timedelta(hours=4)
        deployed_at = base_time + timedelta(hours=6)

        # 2. 构造黄金数据
        proj = Project(id=200, name="Testing Project")
        
        commit = Commit(
            id="sha_commit_001", 
            project_id=proj.id, 
            authored_date=commit_at,
            message="Initial feature"
        )
        
        mr = MergeRequest(
            id=3001,
            iid=1,
            project_id=proj.id,
            state='merged',
            created_at=mr_created_at,
            merged_at=mr_merged_at,
            merge_commit_sha="sha_commit_001" # 简化：MR 只包含一个提交
        )
        
        deploy = Deployment(
            id=5001,
            project_id=proj.id,
            status='success',
            environment='prod',
            sha="sha_commit_001",
            created_at=deployed_at
        )

        self.insert_golden_data([proj, commit, mr, deploy])

        # 3. 部署 DORA 视图
        self.deploy_view('dora_metrics.sql')

        # 4. 执行验证
        # 预期 total_lead_time_seconds = 6 hours = 21600
        expected = [{
            "project_id": 200,
            "mr_iid": 1,
            "total_lead_time_seconds": 21600.0,
            "coding_time_seconds": 7200.0,
            "review_time_seconds": 7200.0,
            "deploy_time_seconds": 7200.0
        }]

        self.assert_view_results('dora_lead_time_for_changes', expected, key_fields=['project_id', 'mr_iid'])

    def test_change_failure_rate_logic(self):
        """测试变更失败率逻辑。
        
        场景描述:
        - 项目 201 有 2 次部署。
        - 关联了 1 个标记为 'bug-source::production' 的 Issue。
        预期失败率: 50.0%
        """
        from devops_collector.plugins.gitlab.models import Issue
        
        proj = Project(id=201, name="Failure Rate Project")
        
        # 两次部署
        d1 = Deployment(id=6001, project_id=proj.id, status='success', environment='prod')
        d2 = Deployment(id=6002, project_id=proj.id, status='success', environment='prod')
        
        # 一个线上事故 Issue
        issue = Issue(
            id=9001, 
            project_id=proj.id, 
            title="Production Crash",
            labels=["bug-source::production"] # 触发 SQL View 中的 LIKE 逻辑
        )
        
        self.insert_golden_data([proj, d1, d2, issue])
        self.deploy_view('dora_metrics.sql')

        expected = [{
            "project_id": 201,
            "total_deployments": 2,
            "production_incidents": 1,
            "failure_rate_percentage": 50.0
        }]
        
        self.assert_view_results('dora_change_failure_rate', expected, key_fields=['project_id'])

if __name__ == "__main__":
    unittest.main()
