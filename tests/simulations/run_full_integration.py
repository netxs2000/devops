"""DevOps 全链路集成验证与仿真测试脚本 (Full Stack Simulation)

验证路径：
1. GitLab 采集 (Group -> Project -> Issue -> MR)
2. SonarQube 采集 (Project Key -> Measures -> Quality Gate)
3. 跨系统关联 (SonarQube Project 关联到 GitLab Project)
4. 数据入库与 ORM 状态校验
"""

import sys
import os
import json
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 路径设置
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from devops_collector.models import (
    Base, Project, Issue, MergeRequest, Commit, 
    GitLabGroup, SyncLog, User, SonarProject, SonarMeasure,
    JiraProject, JiraIssue, ZenTaoProduct, ZenTaoIssue,
    NexusComponent, JFrogArtifact
)
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.sonarqube.client import SonarQubeClient
from devops_collector.plugins.sonarqube.worker import SonarQubeWorker

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FullSimulation')

# 加载数据辅助函数
def load_mock_json(filename):
    path = os.path.join(os.path.dirname(__file__), 'mock_data', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 数据缓存
MOCK_DATA = {
    'gl_projects': load_mock_json('gitlab_projects.json'),
    'gl_issues': load_mock_json('gitlab_issues.json'),
    'gl_mrs': load_mock_json('gitlab_mrs.json'),
    'gl_groups': load_mock_json('gitlab_group.json'),
    'sq_gate': load_mock_json('sonarqube_quality_gate.json'),
    'sq_measures': load_mock_json('sonarqube_measures.json'),
    'jk_jobs': load_mock_json('jenkins_jobs.json'),
    'jk_builds_list': load_mock_json('jenkins_builds_list.json'),
    'jk_build_detail': load_mock_json('jenkins_build_detail.json'),
    'jr_projects': load_mock_json('jira_projects.json'),
    'jr_boards': load_mock_json('jira_boards.json'),
    'jr_sprints': load_mock_json('jira_sprints.json'),
    'jr_issues': load_mock_json('jira_issues.json'),
    'jr_users': load_mock_json('jira_users.json'),
    'jr_groups': load_mock_json('jira_groups.json'),
    'zt_products': load_mock_json('zentao_products.json'),
    'zt_plans': load_mock_json('zentao_plans.json'),
    'zt_stories': load_mock_json('zentao_stories.json'),
    'nx_repos': load_mock_json('nexus_repositories.json'),
    'nx_comps': load_mock_json('nexus_components.json'),
    'jf_artifacts': load_mock_json('jfrog_artifacts.json'),
    'jf_stats': load_mock_json('jfrog_stats.json'),
    'jf_xray': load_mock_json('jfrog_xray.json')
}

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.headers = {'x-total': str(len(json_data)) if isinstance(json_data, list) else '1'}
    def json(self): return self.json_data
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(f"HTTP {self.status_code}")

def mocked_requests_get(*args, **kwargs):
    url = args[0]
    p_arg = kwargs.get('params')
    p = p_arg if p_arg else {}
    page = p.get('page', p.get('p', 1)) 
    
    # 1. GitLab Routing
    if "mock-gitlab.com" in url:
        if page > 1: return MockResponse([])
        if "/repository/commits" in url: return MockResponse([])
        if "/issues" in url: return MockResponse(MOCK_DATA['gl_issues'])
        if "/merge_requests" in url: return MockResponse(MOCK_DATA['gl_mrs'])
        if "/repository/tags" in url: return MockResponse([])
        if "/repository/branches" in url: return MockResponse([])
        if "/pipelines" in url: return MockResponse([])
        if "/deployments" in url: return MockResponse([])
        if "/milestones" in url: return MockResponse([])
        if "/packages" in url: return MockResponse([])
        if "projects/101" in url: return MockResponse(MOCK_DATA['gl_projects'][0])
        if "groups/10" in url: return MockResponse(MOCK_DATA['gl_groups'][0])
        return MockResponse([])

    # 2. SonarQube Routing
    if "mock-sonar.com" in url:
        if "projects/search" in url:
            return MockResponse({'components': [{'key': 'product-group/frontend-web-app', 'name': 'Frontend Web App', 'lastAnalysisDate': '2025-12-19T10:00:00Z'}]})
        if "measures/component" in url:
            return MockResponse(MOCK_DATA['sq_measures'])
        if "qualitygates/project_status" in url:
            return MockResponse(MOCK_DATA['sq_gate'])
        if "issues/search" in url:
            return MockResponse({'facets': [], 'issues': []})
        if "hotspots/search" in url:
            return MockResponse({'hotspots': []})
        return MockResponse({})

    # 3. Jenkins Routing
    if "mock-jenkins.com" in url:
        if url.endswith("api/json") and "job/" not in url:
            return MockResponse({'jobs': MOCK_DATA['jk_jobs']})
        if "api/json" in url and "job/" in url:
            tree = p.get('tree', '')
            if 'builds' in tree:
                return MockResponse({'builds': MOCK_DATA['jk_builds_list']})
            return MockResponse(MOCK_DATA['jk_build_detail'])
        return MockResponse({})

    # 4. Jira Routing
    if "mock-jira.com" in url:
        if "/rest/api/3/groups/picker" in url: return MockResponse(MOCK_DATA['jr_groups'])
        if "/rest/api/3/users/search" in url: return MockResponse(MOCK_DATA['jr_users'])
        if "/rest/api/3/project/PROJ" in url: return MockResponse(MOCK_DATA['jr_projects'][0])
        if "/rest/agile/1.0/board" in url and "sprint" not in url: return MockResponse(MOCK_DATA['jr_boards'])
        if "/rest/agile/1.0/board/1/sprint" in url: return MockResponse(MOCK_DATA['jr_sprints'])
        if "/rest/api/3/search" in url: return MockResponse(MOCK_DATA['jr_issues'])
        return MockResponse({})

    # 5. ZenTao Routing
    if "mock-zentao.com" in url:
        if url.endswith("/products"): return MockResponse({'products': MOCK_DATA['zt_products']})
        if "/products/1/plans" in url: return MockResponse(MOCK_DATA['zt_plans'])
        if "/products/1/stories" in url: return MockResponse(MOCK_DATA['zt_stories'])
        if "/products/1/bugs" in url: return MockResponse({'bugs': [], 'total': 0})
        if "/products/1/cases" in url: return MockResponse({'cases': []})
        if "/products/1/releases" in url: return MockResponse({'releases': []})
        if "/products/1/actions" in url: return MockResponse({'actions': []})
        if "/products/1" in url: return MockResponse(MOCK_DATA['zt_products'][0])
        if "/executions" in url: return MockResponse({'executions': []})
        if "/users" in url: return MockResponse({'users': []})
        if "/departments" in url: return MockResponse({'departments': []})
        return MockResponse({})

    # 6. Nexus Routing
    if "mock-nexus.com" in url:
        if "/components" in url: return MockResponse(MOCK_DATA['nx_comps'])
        if "/repositories" in url: return MockResponse(MOCK_DATA['nx_repos'])
        return MockResponse({})

    # 7. JFrog Routing
    if "mock-jfrog.com" in url:
        if "stats" in url: return MockResponse(MOCK_DATA['jf_stats'])
        if "xray/summary" in url: return MockResponse(MOCK_DATA['jf_xray'])
        return MockResponse({})

    return MockResponse({}, status_code=404)

def mocked_requests_post(*args, **kwargs):
    url = args[0]
    if "mock-jfrog.com" in url and "search/aql" in url:
        return MockResponse(MOCK_DATA['jf_artifacts'])
    return MockResponse({}, status_code=404)

def run_simulation():
    logger.info("🚀 Starting Comprehensive Full Stack Integration Simulation...")

    # 初始化内存数据库
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    with patch('requests.get', side_effect=mocked_requests_get), \
         patch('requests.post', side_effect=mocked_requests_post):
        # --- Stage 1: GitLab Sync ---
        logger.info("--- [STAGE 1] GitLab Data Collection ---")
        from devops_collector.plugins.gitlab.client import GitLabClient
        gl_client = GitLabClient(url="https://mock-gitlab.com", token="gl-fake")
        from devops_collector.plugins.gitlab.worker import GitLabWorker
        gl_worker = GitLabWorker(session=session, client=gl_client)
        gl_worker.process_task({'project_id': 101, 'job_type': 'full'})

        # --- Stage 2: SonarQube Sync ---
        logger.info("--- [STAGE 2] SonarQube Data Collection ---")
        from devops_collector.plugins.sonarqube.client import SonarQubeClient
        sq_client = SonarQubeClient(url="https://mock-sonar.com", token="sq-fake")
        from devops_collector.plugins.sonarqube.worker import SonarQubeWorker
        sq_worker = SonarQubeWorker(session=session, client=sq_client)
        sq_worker.process_task({'project_key': 'product-group/frontend-web-app'})

        # --- Stage 3: Jenkins Sync ---
        logger.info("--- [STAGE 3] Jenkins Data Collection ---")
        from devops_collector.plugins.jenkins.client import JenkinsClient
        jk_client = JenkinsClient(url="http://mock-jenkins.com", user="admin", token="jk-fake")
        from devops_collector.plugins.jenkins.worker import JenkinsWorker
        jk_worker = JenkinsWorker(session=session, client=jk_client)
        # Jenkins Job "frontend-build" should map to "Frontend Web App" by name
        jk_worker.process_task({'job_type': 'sync_all_jobs'})
        jk_worker.process_task({
            'job_type': 'sync_builds', 
            'job_full_name': 'frontend-build'
        })

        # --- Stage 4: Jira Sync ---
        logger.info("--- [STAGE 4] Jira Data Collection ---")
        from devops_collector.plugins.jira.client import JiraClient
        jr_client = JiraClient(url="https://mock-jira.com", email="admin@example.com", api_token="jr-fake")
        from devops_collector.plugins.jira.worker import JiraWorker
        jr_worker = JiraWorker(session=session, client=jr_client)
        jr_worker.process_task({'project_key': 'PROJ'})

        # --- Stage 5: ZenTao Sync ---
        logger.info("--- [STAGE 5] ZenTao Data Collection ---")
        from devops_collector.plugins.zentao.client import ZenTaoClient
        zt_client = ZenTaoClient(url="http://mock-zentao.com", token="zt-fake")
        from devops_collector.plugins.zentao.worker import ZenTaoWorker
        zt_worker = ZenTaoWorker(session=session, client=zt_client)
        zt_worker.process_task({'product_id': 1})

        # --- Stage 6: Nexus Sync ---
        logger.info("--- [STAGE 6] Nexus Data Collection ---")
        from devops_collector.plugins.nexus.client import NexusClient
        nx_client = NexusClient(url="http://mock-nexus.com", user="admin", password="password")
        from devops_collector.plugins.nexus.worker import NexusWorker
        nx_worker = NexusWorker(session=session, client=nx_client)
        nx_worker.process_task({'repository': 'maven-releases'})

        # --- Stage 7: JFrog Sync ---
        logger.info("--- [STAGE 7] JFrog Data Collection ---")
        from devops_collector.plugins.jfrog.client import JFrogClient
        jf_client = JFrogClient(url="http://mock-jfrog.com", token="jf-fake")
        from devops_collector.plugins.jfrog.worker import JFrogWorker
        jf_worker = JFrogWorker(session=session, client=jf_client)
        jf_worker.process_task({'repo': 'docker-local'})

        # --- Stage 8: Verification ---
        logger.info("--- [STAGE 8] Data Consistency Verification ---")
        
        # 1. 验证基础数据
        gl_proj = session.query(Project).get(101)
        issues = session.query(Issue).filter_by(project_id=101).all()
        logger.info(f"✅ GitLab Project: {gl_proj.name} (Issues: {len(issues)})")
        
        # 2. 跨系统关联：SonarQube -> GitLab
        sq_proj = session.query(SonarProject).filter_by(key='product-group/frontend-web-app').first()
        logger.info(f"🔗 Link SQ->GL: SonarProject.gitlab_project_id = {sq_proj.gitlab_project_id}")
        assert sq_proj.gitlab_project_id == 101, "SQ to GL mapping failed!"

        # 3. 跨系统关联：Jenkins -> GitLab
        from devops_collector.plugins.jenkins.models import JenkinsJob as JKJob
        jk_job = session.query(JKJob).filter_by(full_name='frontend-build').first()
        logger.info(f"🔗 Link JK->GL: JenkinsJob.gitlab_project_id = {jk_job.gitlab_project_id}")
        assert jk_job.gitlab_project_id == 101, "Jenkins to GL mapping failed!"

        # 4. 指标验证
        latest_measure = session.query(SonarMeasure).filter_by(project_id=sq_proj.id).first()
        logger.info(f"📊 Quality Metrics: Coverage={latest_measure.coverage}%")
        
        from devops_collector.plugins.jenkins.models import JenkinsBuild as JKBuild
        all_builds = session.query(JKBuild).all()
        for b in all_builds:
            logger.info(f"DEBUG: Found build {b.number} for job_id {b.job_id}")
        
        builds_count = len(all_builds)
        logger.info(f"🏗️ Build Metrics: Total builds in DB = {builds_count}")
        assert builds_count == 2

        # 5. Jira 验证
        jr_proj = session.query(JiraProject).filter_by(key='PROJ').first()
        jr_issues_count = session.query(JiraIssue).filter_by(project_id=jr_proj.id).count()
        logger.info(f"📝 Jira Metrics: Project={jr_proj.name}, Issues={jr_issues_count}")
        assert jr_issues_count == 2

        # 6. ZenTao 验证
        zt_proj = session.query(ZenTaoProduct).filter_by(id=1).first()
        zt_issues_count = session.query(ZenTaoIssue).filter_by(product_id=zt_proj.id).count()
        logger.info(f"🏯 ZenTao Metrics: Product={zt_proj.name}, Stories={zt_issues_count}")
        assert zt_issues_count == 1

        # 7. Nexus & JFrog 验证
        nx_comp = session.query(NexusComponent).filter_by(repository='maven-releases').first()
        jf_art = session.query(JFrogArtifact).filter_by(repo='docker-local').first()
        logger.info(f"📦 Artifactory Metrics: NexusComp={nx_comp.name}, JFrogArt={jf_art.name}")
        assert nx_comp.name == "core-library"
        assert jf_art.download_count == 150

        logger.info("✨ ALL SYSTEMS (GL+SQ+JK+JR+ZT+NX+JF) INTEGRATED AND VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    run_simulation()
