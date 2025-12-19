import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, TraceabilityLink
from devops_collector.plugins.gitlab.models import Project, MergeRequest, Commit
from devops_collector.plugins.jenkins.models import JenkinsJob, JenkinsBuild
from devops_collector.plugins.jira.models import JiraProject, JiraIssue
from devops_collector.plugins.zentao.models import ZenTaoProduct, ZenTaoIssue

class TestTraceabilityModels(unittest.TestCase):
    """跨系统链路追踪元数据单元测试。
    
    验证各插件模型扩展字段的有效性以及 TraceabilityLink 的存储逻辑。
    """

    def setUp(self):
        """测试环境初始化：使用内存数据库。"""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """清理测试环境。"""
        self.session.close()

    def test_traceability_link_storage(self):
        """测试通用追溯映射表 (TraceabilityLink) 的基本存取。"""
        link = TraceabilityLink(
            source_system="jira",
            source_type="issue",
            source_id="PROJ-101",
            target_system="gitlab",
            target_type="mr",
            target_id="15",
            link_type="fixes",
            raw_data={"note": "Manual link from UI"}
        )
        self.session.add(link)
        self.session.commit()

        saved_link = self.session.query(TraceabilityLink).first()
        self.assertIsNotNone(saved_link)
        self.assertEqual(saved_link.source_id, "PROJ-101")
        self.assertEqual(saved_link.target_system, "gitlab")
        self.assertEqual(saved_link.link_type, "fixes")

    def test_gitlab_traceability_fields(self):
        """测试 GitLab 模型的追溯扩展字段。"""
        # 创建项目作为外键基础
        project = Project(id=1, name="Test Project")
        self.session.add(project)
        self.session.flush()

        # 1. 验证 MergeRequest 扩展字段
        mr = MergeRequest(
            id=101,
            iid=10,
            project_id=project.id,
            title="Fix bug for Jira-123",
            external_issue_id="JIRA-123",
            issue_source="jira"
        )
        self.session.add(mr)
        
        # 2. 验证 Commit 扩展字段
        commit = Commit(
            id="sha123456",
            project_id=project.id,
            message="Implement feature X, resolves #456 and #789",
            linked_issue_ids=["456", "789"],
            issue_source="zentao"
        )
        self.session.add(commit)
        self.session.commit()

        saved_mr = self.session.query(MergeRequest).filter_by(id=101).first()
        self.assertEqual(saved_mr.external_issue_id, "JIRA-123")
        self.assertEqual(saved_mr.issue_source, "jira")

        saved_commit = self.session.query(Commit).filter_by(id="sha123456").first()
        self.assertIn("456", saved_commit.linked_issue_ids)
        self.assertEqual(saved_commit.issue_source, "zentao")

    def test_jenkins_traceability_fields(self):
        """测试 Jenkins 模型的追溯扩展字段。"""
        job = JenkinsJob(name="build-pipeline", full_name="deploy/build-pipeline")
        self.session.add(job)
        self.session.flush()

        build = JenkinsBuild(
            job_id=job.id,
            number=42,
            gitlab_mr_iid=15,
            artifact_id="registry.example.com/app:v1.2.3",
            artifact_type="docker_image"
        )
        self.session.add(build)
        self.session.commit()

        saved_build = self.session.query(JenkinsBuild).filter_by(number=42).first()
        self.assertEqual(saved_build.gitlab_mr_iid, 15)
        self.assertEqual(saved_build.artifact_id, "registry.example.com/app:v1.2.3")
        self.assertEqual(saved_build.artifact_type, "docker_image")

    def test_management_system_traceability_fields(self):
        """测试 Jira 和 ZenTao 模型的追溯扩展字段。"""
        # 1. Jira 测试
        jira_proj = JiraProject(key="PROJ", name="Project")
        self.session.add(jira_proj)
        self.session.flush()
        
        jira_issue = JiraIssue(
            id=201,
            key="PROJ-201",
            project_id=jira_proj.id,
            first_commit_sha="sha999",
            first_fix_date=datetime.now(timezone.utc)
        )
        self.session.add(jira_issue)

        # 2. ZenTao 测试
        zt_prod = ZenTaoProduct(id=301, name="ZT Product")
        self.session.add(zt_prod)
        self.session.flush()

        zt_issue = ZenTaoIssue(
            id=401,
            product_id=zt_prod.id,
            title="Fixed bug",
            first_commit_sha="sha888",
            first_fix_date=datetime.now(timezone.utc)
        )
        self.session.add(zt_issue)
        self.session.commit()

        saved_jira = self.session.query(JiraIssue).filter_by(id=201).first()
        self.assertEqual(saved_jira.first_commit_sha, "sha999")
        self.assertIsNotNone(saved_jira.first_fix_date)

        saved_zt = self.session.query(ZenTaoIssue).filter_by(id=401).first()
        self.assertEqual(saved_zt.first_commit_sha, "sha888")

if __name__ == '__main__':
    unittest.main()
