"""集成测试模块。

验证跨模型、跨插件的关联关系、Hybrid 属性计算以及 Association Proxy 逻辑。
"""
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
sys.path.append(os.getcwd())
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
def run_integration_test():
    """执行深度集成测试，涵盖组织架构、用户身份、跨插件关联、DORA 指标等 14 个场景。"""
    print('Starting deep integration test...')
    
    # 延迟加载，防止 collection 阶段死锁
    from devops_collector.core.plugin_loader import PluginLoader
    PluginLoader.autodiscover()
    PluginLoader.load_models()

    from devops_collector.models import Base, Organization, User, IdentityMapping, Product, GTMTestCase, GTMRequirement, Service, ResourceCost
    from devops_collector.plugins.gitlab.models import (
        GitLabProject as Project, GitLabCommit as Commit, GitLabIssue as Issue,
        GitLabMilestone as Milestone, GitLabNote as Note, GitLabDeployment as Deployment,
        GitLabProjectMember as ProjectMember
    )
    from devops_collector.plugins.sonarqube.models import SonarProject, SonarMeasure
    from devops_collector.plugins.jira.models import JiraProject

    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    print('Database schema initialized.')
    try:
        print('Scenrio 1: Organization Hierarchy...')
        root_org = Organization(org_id='ORG_ROOT', org_name='Global Group', org_level=1)
        dept_org = Organization(org_id='ORG_DEPT_01', org_name='Cloud Infrastructure', parent_org_id='ORG_ROOT', org_level=3)
        session.add(root_org)
        session.add(dept_org)
        session.commit()
        saved_dept = session.query(Organization).filter_by(org_id='ORG_DEPT_01').one()
        assert saved_dept.parent.org_id == 'ORG_ROOT'
        assert root_org.children[0].org_id == 'ORG_DEPT_01'
        print('  - Organization hierarchy verified.')
        print('Scenario 2: User and OneID Mapping...')
        user_uuid = uuid.uuid4()
        test_user = User(global_user_id=user_uuid, employee_id='EMP001', full_name='John Doe', primary_email='john.doe@example.com', department_id='ORG_DEPT_01', is_active=True)
        session.add(test_user)
        gitlab_id = IdentityMapping(global_user_id=user_uuid, source_system='gitlab', external_user_id='1001', external_username='jdoe_gitlab')
        jira_id = IdentityMapping(global_user_id=user_uuid, source_system='jira', external_user_id='JIRA-UID-99', external_username='john.doe')
        session.add(gitlab_id)
        session.add(jira_id)
        session.commit()
        saved_user = session.query(User).filter_by(employee_id='EMP001').one()
        assert saved_user.department.org_name == 'Cloud Infrastructure'
        assert saved_user in saved_user.department.users
        root_org.manager_user_id = user_uuid
        session.commit()
        assert root_org.manager.full_name == 'John Doe'
        assert root_org in test_user.managed_organizations
        assert len(saved_user.identities) == 2
        assert any((i.source_system == 'gitlab' for i in saved_user.identities))
        print('  - User and identity mapping verified (including bidirectional org membership).')
        print('Scenario 3: Cross-Plugin Relations & Test Management...')
        gitlab_project = Project(id=50001, name='core-api', path_with_namespace='infra/core-api', organization_id='ORG_DEPT_01')
        session.add(gitlab_project)
        test_commit = Commit(id='sha123456789', project_id=50001, author_email='john.doe@example.com', message='Initial commit', authored_date=datetime.now(timezone.utc))
        session.add(test_commit)
        test_case = GTMTestCase(project_id=50001, author_id=user_uuid, iid=1, title='Verify login')
        requirement = GTMRequirement(project_id=50001, author_id=user_uuid, iid=101, title='User must be able to login')
        session.add(test_case)
        session.add(requirement)
        requirement.test_cases.append(test_case)
        sonar_project = SonarProject(key='core-api-sonar', gitlab_project_id=50001)
        session.add(sonar_project)
        session.commit()
        saved_project = session.get(Project, 50001)
        assert saved_project.organization.org_id == 'ORG_DEPT_01'
        assert gitlab_project in saved_dept.gitlab_projects
        assert len(saved_project.commits) == 1
        assert len(saved_project.test_cases) == 1
        assert len(saved_project.requirements) == 1
        assert len(saved_project.sonar_projects) == 1
        assert len(saved_user.test_cases) == 1
        assert len(saved_user.requirements) == 1
        print('  - Plugin, Test Management and Cross-model bidirectional relations verified.')
        print('Scenario 4: JSON Data Integrity & Product Relations...')
        test_product = Product(product_id='PROD_01', product_name='Cloud Platform', product_description='Desc', version_schema='1.0', owner_team_id='ORG_ROOT', product_manager_id=user_uuid)
        session.add(test_product)
        session.commit()
        saved_product = session.query(Product).filter_by(product_name='Cloud Platform').one()
        assert saved_product.product_name == 'Cloud Platform'
        assert saved_product.product_manager.full_name == 'John Doe'
        assert saved_product in test_user.managed_products_as_pm
        assert test_product in root_org.products
        print('Scenario 5: Black Technology (Proxies & Hybrids)...')
        assert 'jdoe_gitlab' in test_user.external_usernames
        assert 'john.doe' in test_user.external_usernames
        print('  - Association Proxy (User.external_usernames) verified.')
        # ProjectMember already imported as alias
        membership = ProjectMember(project_id=50001, user_id=user_uuid, access_level=40)
        session.add(membership)
        session.commit()
        assert test_user.projects[0].name == 'core-api'
        print('  - Association Proxy (User.projects) verified.')
        from devops_collector.plugins.gitlab.models import GitLabMergeRequest as MergeRequest, GitLabPipeline as Pipeline, GitLabDeployment as Deployment
        from datetime import timedelta
        create_time = datetime.now(timezone.utc) - timedelta(days=2)
        merge_time = datetime.now(timezone.utc)
        test_mr = MergeRequest(id=9001, iid=5, project_id=50001, title='Fix bug', created_at=create_time, merged_at=merge_time, state='merged')
        session.add(test_mr)
        session.commit()
        assert test_mr.cycle_time >= 172800
        mr_filtered = session.query(MergeRequest).filter(MergeRequest.state == 'merged').first()
        assert mr_filtered is not None
        assert mr_filtered.id == 9001
        assert mr_filtered.cycle_time >= 172800
        print('  - Hybrid Attribute (MergeRequest.cycle_time) and Python-side calculation verified.')
        print('Scenario 6: Phase 2 Black Tech (Events & DORA Hybrids)...')
        old_activity = saved_project.last_activity_at
        new_commit = Commit(id='sha999', project_id=50001, message='Activity trigger', authored_date=datetime.now(timezone.utc))
        session.add(new_commit)
        session.commit()
        session.refresh(saved_project)
        assert saved_project.last_activity_at > old_activity
        print('  - Event Listener (Project.last_activity_at) verified.')
        test_pipe = Pipeline(id=888, project_id=50001, status='success')
        test_deploy = Deployment(id=777, project_id=50001, status='success', environment='Production')
        session.add(test_pipe)
        session.add(test_deploy)
        session.commit()
        success_pipes = session.query(Pipeline).filter(Pipeline.is_success == True).all()
        assert len(success_pipes) >= 1
        assert success_pipes[0].status == 'success'
        prod_deploys = session.query(Deployment).filter(Deployment.is_production == True).all()
        assert len(prod_deploys) >= 1
        assert prod_deploys[0].environment == 'Production'
        print('  - DORA Hybrid Attributes (Pipeline/Deployment) verified.')
        print('Scenario 7: Materialized Attributes from JSON...')
        gitlab_project.raw_data = {'visibility': 'private', 'archived': True, 'web_url': 'https://gitlab.com/infra/core-api'}
        session.commit()
        assert saved_project.visibility == 'private'
        assert saved_project.is_archived is True
        assert saved_project.web_url == 'https://gitlab.com/infra/core-api'
        archived_projs = session.query(Project).filter(Project.is_archived == True).all()
        assert len(archived_projs) == 1
        assert archived_projs[0].id == 50001
        print('  - Project Materialized Attributes (visibility, is_archived) verified.')
        test_mr.raw_data = {'draft': True, 'source_branch': 'feature/ui', 'target_branch': 'develop'}
        session.commit()
        assert test_mr.is_draft is True
        assert test_mr.source_branch == 'feature/ui'
        assert test_mr.target_branch == 'develop'
        print('  - MergeRequest Materialized Attributes (is_draft, branches) verified.')
        print('Scenario 8: Domain-Specific Black Tech (Iteration & Test Management)...')
        test_milestone = Milestone(id=60001, title='Sprint 1', state='active', project_id=50001)
        session.add(test_milestone)
        issue_1 = Issue(id=70001, iid=10, project_id=50001, milestone_id=60001, state='closed')
        issue_2 = Issue(id=70002, iid=11, project_id=50001, milestone_id=60001, state='opened')
        session.add(issue_1)
        session.add(issue_2)
        session.commit()
        assert test_milestone.progress == 50.0
        print('  - Milestone Progress (Hybrid Attribute) verified.')
        from devops_collector.models import GTMTestCaseIssueLink
        link = GTMTestCaseIssueLink(test_case_id=test_case.id, issue_id=70002)
        session.add(link)
        session.commit()
        bugs = requirement.linked_bugs
        assert len(bugs) >= 1
        assert any((b.id == 70002 for sublist in bugs for b in (sublist if isinstance(sublist, list) else [sublist])))
        print('  - Requirement -> Bug (Association Proxy) penetration verified.')
        from devops_collector.models import GTMTestExecutionRecord
        exec_record = GTMTestExecutionRecord(project_id=50001, test_case_iid=test_case.iid, result='passed', executed_at=datetime.now(timezone.utc))
        session.add(exec_record)
        session.commit()
        session.refresh(test_case)
        assert test_case.execution_count == 1
        print('  - TestCase Execution Count (Hybrid Attribute) verified.')
        print('Scenario 9: Service Desk SLA Logic...')
        support_issue = Issue(id=80001, iid=20, project_id=50001, title='Production down!', labels=['priority::P0'], created_at=datetime.now(timezone.utc) - timedelta(hours=9), author_id=user_uuid)
        session.add(support_issue)
        session.commit()
        assert support_issue.priority_level == 0
        assert support_issue.sla_limit_seconds == 28800
        assert support_issue.is_sla_violated == True
        assert support_issue.sla_status == 'WARNING'
        print('  - SLA Violation detection (P0 @ 9h) verified.')
        p3_issue = Issue(id=80002, iid=21, project_id=50001, title='Minor bug', labels=['priority::P3'], created_at=datetime.now(timezone.utc) - timedelta(hours=10), author_id=user_uuid)
        session.add(p3_issue)
        session.commit()
        assert p3_issue.sla_limit_seconds == 432000
        assert p3_issue.is_sla_violated == False
        print('  - SLA P3 threshold (120h from config) verified.')
        agent_uuid = uuid.uuid4()
        response_note = Note(id=55555, project_id=50001, noteable_type='Issue', noteable_iid=20, author_id=agent_uuid, body='I am looking into it.', created_at=datetime.now(timezone.utc))
        session.add(response_note)
        session.commit()
        session.refresh(support_issue)
        assert support_issue.first_response_at is not None
        assert support_issue.sla_status == 'VIOLATED'
        print('  - Event-driven first_response_at update and Final SLA status verified.')
        print('Scenario 10: SonarQube Quality Gate Hybrids...')
        measure_1 = SonarMeasure(project_id=sonar_project.id, analysis_date=datetime.now(timezone.utc) - timedelta(days=1), bugs=10, quality_gate_status='ERROR')
        measure_2 = SonarMeasure(project_id=sonar_project.id, analysis_date=datetime.now(timezone.utc), bugs=0, quality_gate_status='OK')
        session.add_all([measure_1, measure_2])
        session.commit()
        session.refresh(sonar_project)
        assert sonar_project.bugs == 0
        assert sonar_project.quality_gate == 'OK'
        assert sonar_project.is_clean is True
        print('  - SonarProject Quality Hybrids (latest_measure delegation) verified.')
        print('Scenario 11: Global Identity Auto-linking (Historical Traceability)...')
        ghost_email = 'john.doe@example.com'
        ghost_commit = Commit(id='ghost_sha', project_id=50001, author_email=ghost_email, author_name='Ghost Rider', message='Ghostly commit', authored_date=datetime.now(timezone.utc))
        session.add(ghost_commit)
        session.commit()
        assert ghost_commit.gitlab_user_id is None
        new_mapping = IdentityMapping(global_user_id=user_uuid, source_system='gitlab', external_user_id='999', external_username='ghost_rider')
        session.add(new_mapping)
        session.commit()
        session.refresh(ghost_commit)
        assert ghost_commit.gitlab_user_id == user_uuid
        print('  - Global Event (IdentityMapping -> Commit auto-link) verified.')
        print('Scenario 12: DORA MTTR & Change Failure Rate (Hybrid Aggregates)...')
        deploy = Deployment(id=90001, project_id=50001, environment='production', status='success', created_at=datetime.now(timezone.utc))
        session.add(deploy)
        incident_issue = Issue(id=90002, iid=30, project_id=50001, title='Production outage', labels=['incident'], created_at=datetime.now(timezone.utc) - timedelta(hours=5), closed_at=datetime.now(timezone.utc) - timedelta(hours=3), state='closed')
        cf_issue = Issue(id=90003, iid=31, project_id=50001, title='Rollback required', labels=['rollback'], created_at=datetime.now(timezone.utc))
        session.add_all([incident_issue, cf_issue])
        session.commit()
        session.refresh(gitlab_project)
        assert abs(gitlab_project.mttr - 7200.0) < 1.0
        assert gitlab_project.change_failure_rate == 50.0
        print('  - DORA MTTR (7200s) and CFR (50%) verified.')
        print('Scenario 13: Deep Traceability & MR Risk Assessment...')
        feat_issue = Issue(id=90010, iid=50, project_id=50001, title='Cool New Feature', created_at=datetime.now(timezone.utc))
        session.add(feat_issue)
        feat_mr = MergeRequest(id=90011, iid=5, project_id=50001, title='Add cool feature', merge_commit_sha='feat_sha_123', external_issue_id='50', review_cycles=3, quality_gate_status='passed', raw_data={'stats': {'additions': 400, 'deletions': 100}})
        session.add(feat_mr)
        prod_deploy = Deployment(id=90012, project_id=50001, environment='production', status='success', sha='feat_sha_123', created_at=datetime.now(timezone.utc))
        session.add(prod_deploy)
        session.commit()
        session.refresh(feat_issue)
        session.refresh(feat_mr)
        assert feat_issue.is_deployed is True
        assert 'production' in feat_issue.deploy_environments
        print('  - Deep Traceability (Issue -> MR -> Deploy) verified.')
        assert feat_mr.risk_score == 20.0
        print(f'  - MR Risk Score ({feat_mr.risk_score}) verified.')
        print('Scenario 14: Service ROI & AI Denoising Assessment...')
        doc_mr = MergeRequest(id=90020, iid=6, project_id=50001, title='Update README', merge_commit_sha='doc_sha_123', ai_category='Documentation', review_cycles=1, raw_data={'stats': {'additions': 500, 'deletions': 0}})
        session.add(doc_mr)
        session.commit()
        assert doc_mr.risk_score == 2.0
        print('  - AI Risk Denoising (Documentation) verified.')
        payment_service = Service(name='Payment Service', tier='P0')
        session.add(payment_service)
        session.commit()
        cost1 = ResourceCost(service_id=payment_service.id, period='2025-01', amount=50000.0, cost_item='Cloud Hosting')
        cost2 = ResourceCost(service_id=payment_service.id, period='2025-01', amount=30000.0, cost_item='Human Labor')
        session.add_all([cost1, cost2])
        session.commit()
        session.refresh(payment_service)
        assert payment_service.total_cost == 80000.0
        assert payment_service.investment_roi == 10.0
        print(f'  - Service ROI (Cost: 80k, ROI: {payment_service.investment_roi}) verified.')
        print('Scenario 15: Jenkins Test Execution (Renamed Model) Validation...')
        from devops_collector.models import JenkinsTestExecution
        jenkins_test = JenkinsTestExecution(
            project_id=gitlab_project.id,
            build_id='jenkins-build-999',
            test_level='Unit',
            total_cases=100,
            passed_count=98,
            failed_count=2,
            pass_rate=98.0
        )
        session.add(jenkins_test)
        session.commit()
        session.refresh(jenkins_test)
        assert jenkins_test.project_id == 50001
        assert jenkins_test.pass_rate == 98.0
        try:
             # Verify Unique Constraint: (project_id, build_id, test_level)
            dup_test = JenkinsTestExecution(
                project_id=gitlab_project.id,
                build_id='jenkins-build-999',
                test_level='Unit'
            )
            session.add(dup_test)
            session.commit()
            print('  - ERROR: Unique Constraint FAILED!')
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            print('  - Unique Constraint (project, build, test_level) verified.')
        
        print('\nALL INTEGRATION TESTS (INCLUDING ROI, AI TECH & JENKINS MODELS) PASSED SUCCESSFULLY!')
    except Exception as e:
        print(f'\nINTEGRATION TEST FAILED: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()
if __name__ == '__main__':
    run_integration_test()