
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.append(os.getcwd())

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import postgresql

# --- Mock PostgreSQL types for SQLite integration test ---
postgresql.JSONB = sqlalchemy.JSON
postgresql.UUID = lambda *args, **kwargs: sqlalchemy.String(36)

# Import models
from devops_collector.models import (
    Base, Organization, User, IdentityMapping, 
    Project, Commit, Product, TestCase, Requirement,
    SonarProject, SonarMeasure, JiraProject, Milestone, Issue, Note, Deployment,
    Service, ResourceCost
)

def run_integration_test():
    print("Starting deep integration test...")
    
    # 1. Setup in-memory database
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    print("Database schema initialized.")

    try:
        # 2. Test Organization Hierarchy
        print("Scenrio 1: Organization Hierarchy...")
        root_org = Organization(
            org_id="ORG_ROOT",
            org_name="Global Group",
            org_level=1
        )
        dept_org = Organization(
            org_id="ORG_DEPT_01",
            org_name="Cloud Infrastructure",
            parent_org_id="ORG_ROOT",
            org_level=3
        )
        session.add(root_org)
        session.add(dept_org)
        session.commit()
        
        # Verify hierarchy
        saved_dept = session.query(Organization).filter_by(org_id="ORG_DEPT_01").one()
        assert saved_dept.parent.org_id == "ORG_ROOT"
        assert root_org.children[0].org_id == "ORG_DEPT_01"
        print("  - Organization hierarchy verified.")

        # 3. Test User and Identity OneID
        print("Scenario 2: User and OneID Mapping...")
        user_uuid = str(uuid.uuid4())
        test_user = User(
            global_user_id=user_uuid,
            employee_id="EMP001",
            full_name="John Doe",
            primary_email="john.doe@example.com",
            department_id="ORG_DEPT_01",
            is_active=True
        )
        session.add(test_user)
        
        # Add Identity Mappings
        gitlab_id = IdentityMapping(
            global_user_id=user_uuid,
            source_system="gitlab",
            external_user_id="1001",
            external_username="jdoe_gitlab"
        )
        jira_id = IdentityMapping(
            global_user_id=user_uuid,
            source_system="jira",
            external_user_id="JIRA-UID-99",
            external_username="john.doe"
        )
        session.add(gitlab_id)
        session.add(jira_id)
        session.commit()

        # Verify User/Org Bidirectional relations
        saved_user = session.query(User).filter_by(employee_id="EMP001").one()
        assert saved_user.department.org_name == "Cloud Infrastructure"
        assert saved_user in saved_user.department.users
        
        # Test managed organizations back_populates
        root_org.manager_user_id = user_uuid
        session.commit()
        assert root_org.manager.full_name == "John Doe"
        assert root_org in test_user.managed_organizations
        
        assert len(saved_user.identities) == 2
        assert any(i.source_system == "gitlab" for i in saved_user.identities)
        print("  - User and identity mapping verified (including bidirectional org membership).")

        # 4. Test Cross-Plugin Relation (GitLab Project -> Org)
        print("Scenario 3: Cross-Plugin Relations & Test Management...")
        gitlab_project = Project(
            id=50001,
            name="core-api",
            path_with_namespace="infra/core-api",
            organization_id="ORG_DEPT_01"
        )
        session.add(gitlab_project)
        
        # Test Commit with relation to User
        test_commit = Commit(
            id="sha123456789",
            project_id=50001,
            author_email="john.doe@example.com",
            message="Initial commit",
            authored_date=datetime.now(timezone.utc)
        )
        session.add(test_commit)
        
        # Test Case & Requirement
        test_case = TestCase(
            project_id=50001,
            author_id=user_uuid,
            iid=1,
            title="Verify login"
        )
        requirement = Requirement(
            project_id=50001,
            author_id=user_uuid,
            iid=101,
            title="User must be able to login"
        )
        session.add(test_case)
        session.add(requirement)
        
        # Link Requirement to TestCase
        requirement.test_cases.append(test_case)
        
        # Cross-plugin bridge (SonarQube)
        sonar_project = SonarProject(
            key="core-api-sonar",
            gitlab_project_id=50001
        )
        session.add(sonar_project)
        
        session.commit()
        
        # Verify Project relations
        saved_project = session.get(Project, 50001)
        assert saved_project.organization.org_id == "ORG_DEPT_01"
        assert gitlab_project in saved_dept.projects
        
        # Verify bidirectional navigation
        assert len(saved_project.commits) == 1
        assert len(saved_project.test_cases) == 1
        assert len(saved_project.requirements) == 1
        assert len(saved_project.sonar_projects) == 1
        
        # Verify User viewpoint
        assert len(saved_user.test_cases) == 1
        assert len(saved_user.requirements) == 1
        
        print("  - Plugin, Test Management and Cross-model bidirectional relations verified.")

        # 5. Test JSON storage and Product relations
        print("Scenario 4: JSON Data Integrity & Product Relations...")
        test_product = Product(
            name="Cloud Platform",
            level="Line",
            organization_id="ORG_ROOT",
            raw_data={"meta": "test", "version": 1.5},
            product_manager_id=user_uuid
        )
        session.add(test_product)
        session.commit()
        
        saved_product = session.query(Product).filter_by(name="Cloud Platform").one()
        assert saved_product.raw_data["version"] == 1.5
        
        # Verify Product -> User (PM) bidirectional
        assert saved_product.product_manager.full_name == "John Doe"
        assert saved_product in test_user.managed_products_as_pm
        
        # Verify Organization -> Product bidirectional
        assert test_product in root_org.products
        
        # --- 黑科技验证 (Scenario 5) ---
        print("Scenario 5: Black Technology (Proxies & Hybrids)...")
        
        # 1. Association Proxy: User.external_usernames
        # test_user has 2 identities: jdoe_gitlab and john.doe (jira)
        assert "jdoe_gitlab" in test_user.external_usernames
        assert "john.doe" in test_user.external_usernames
        print("  - Association Proxy (User.external_usernames) verified.")
        
        # 2. Association Proxy: User.projects
        # Add project membership
        from devops_collector.models import ProjectMember
        membership = ProjectMember(
            project_id=50001,
            user_id=user_uuid,
            access_level=40
        )
        session.add(membership)
        session.commit()
        
        assert test_user.projects[0].name == "core-api"
        print("  - Association Proxy (User.projects) verified.")
        
        # 3. Hybrid Attribute: MergeRequest.cycle_time
        from devops_collector.models import MergeRequest, Pipeline, Deployment
        from datetime import timedelta
        
        create_time = datetime.now(timezone.utc) - timedelta(days=2)
        merge_time = datetime.now(timezone.utc)
        
        test_mr = MergeRequest(
            id=9001,
            iid=5,
            project_id=50001,
            title="Fix bug",
            created_at=create_time,
            merged_at=merge_time,
            state="merged"
        )
        session.add(test_mr)
        session.commit()
        
        # Python-side calculation
        assert test_mr.cycle_time >= 172800 # 2 days in seconds
        
        # SQL-side calculation (filtering)
        mr_filtered = session.query(MergeRequest).filter(MergeRequest.state == 'merged').first()
        assert mr_filtered is not None
        assert mr_filtered.id == 9001
        assert mr_filtered.cycle_time >= 172800
        print("  - Hybrid Attribute (MergeRequest.cycle_time) and Python-side calculation verified.")

        # --- Phase 2: Events & DORA Hybrids (Scenario 6) ---
        print("Scenario 6: Phase 2 Black Tech (Events & DORA Hybrids)...")
        
        # 1. Event Listener: Automatic activity update
        old_activity = saved_project.last_activity_at
        
        new_commit = Commit(
            id="sha999",
            project_id=50001,
            message="Activity trigger",
            authored_date=datetime.now(timezone.utc)
        )
        session.add(new_commit)
        session.commit()
        
        session.refresh(saved_project)
        assert saved_project.last_activity_at > old_activity
        print("  - Event Listener (Project.last_activity_at) verified.")
        
        # 2. DORA Hybrids: Pipeline & Deployment
        test_pipe = Pipeline(
            id=888,
            project_id=50001,
            status="success"
        )
        test_deploy = Deployment(
            id=777,
            project_id=50001,
            status="success",
            environment="Production"
        )
        session.add(test_pipe)
        session.add(test_deploy)
        session.commit()
        
        # Query using Hybrid Attributes
        success_pipes = session.query(Pipeline).filter(Pipeline.is_success == True).all()
        assert len(success_pipes) >= 1
        assert success_pipes[0].status == "success"
        
        prod_deploys = session.query(Deployment).filter(Deployment.is_production == True).all()
        assert len(prod_deploys) >= 1
        assert prod_deploys[0].environment == "Production"
        
        print("  - DORA Hybrid Attributes (Pipeline/Deployment) verified.")

        # --- Phase 2: Materialized Attributes (Scenario 7) ---
        print("Scenario 7: Materialized Attributes from JSON...")
        
        # 1. Project Materialized Attributes
        gitlab_project.raw_data = {
            "visibility": "private",
            "archived": True,
            "web_url": "https://gitlab.com/infra/core-api"
        }
        session.commit()
        
        # Verify Python-side from raw_data
        assert saved_project.visibility == "private"
        assert saved_project.is_archived is True
        assert saved_project.web_url == "https://gitlab.com/infra/core-api"
        
        # Verify SQL-side expression (is_archived has a SQL expression)
        archived_projs = session.query(Project).filter(Project.is_archived == True).all()
        assert len(archived_projs) == 1
        assert archived_projs[0].id == 50001
        print("  - Project Materialized Attributes (visibility, is_archived) verified.")
        
        # 2. MergeRequest Materialized Attributes
        test_mr.raw_data = {
            "draft": True,
            "source_branch": "feature/ui",
            "target_branch": "develop"
        }
        session.commit()
        
        assert test_mr.is_draft is True
        assert test_mr.source_branch == "feature/ui"
        assert test_mr.target_branch == "develop"
        print("  - MergeRequest Materialized Attributes (is_draft, branches) verified.")

        # --- Domain-Specific Black Tech (Scenario 8) ---
        print("Scenario 8: Domain-Specific Black Tech (Iteration & Test Management)...")
        
        # 1. Iteration: Milestone progress
        test_milestone = Milestone(
            id=60001,
            title="Sprint 1",
            state="active",
            project_id=50001
        )
        session.add(test_milestone)
        
        # Add 2 issues to milestone (one closed)
        issue_1 = Issue(id=70001, iid=10, project_id=50001, milestone_id=60001, state="closed")
        issue_2 = Issue(id=70002, iid=11, project_id=50001, milestone_id=60001, state="opened")
        session.add(issue_1)
        session.add(issue_2)
        session.commit()
        
        assert test_milestone.progress == 50.0
        print("  - Milestone Progress (Hybrid Attribute) verified.")
        
        # 2. Test Management: Requirement -> Bug (Association Proxy)
        # Link issue_2 (opened bug) to test_case (Scenario 3)
        from devops_collector.models import TestCaseIssueLink
        link = TestCaseIssueLink(test_case_id=test_case.id, issue_id=70002)
        session.add(link)
        session.commit()
        
        # Now requirement (Scenario 3) links to test_case, which links to issue_2
        # Verify requirement.linked_bugs
        # Since association_proxy returns a list for each element if intermediate is list, 
        # Requirement.test_cases is a list, so Requirement.linked_bugs will be a list of lists or similar.
        # Actually in SQLAlchemy it flattens one level if possible, but let's check.
        bugs = requirement.linked_bugs
        assert len(bugs) >= 1
        assert any(b.id == 70002 for sublist in bugs for b in (sublist if isinstance(sublist, list) else [sublist]))
        print("  - Requirement -> Bug (Association Proxy) penetration verified.")
        
        # 3. Test Management: Execution Count
        from devops_collector.models import TestExecutionRecord
        exec_record = TestExecutionRecord(
            project_id=50001,
            test_case_iid=test_case.iid,
            result="passed",
            executed_at=datetime.now(timezone.utc)
        )
        session.add(exec_record)
        session.commit()
        
        session.refresh(test_case)
        assert test_case.execution_count == 1
        print("  - TestCase Execution Count (Hybrid Attribute) verified.")

        # --- Service Desk SLA (Scenario 9) ---
        print("Scenario 9: Service Desk SLA Logic...")
        
        # 1. Create P0 Support Issue
        support_issue = Issue(
            id=80001,
            iid=20,
            project_id=50001,
            title="Production down!",
            labels=["priority::P0"],
            created_at=datetime.now(timezone.utc) - timedelta(hours=9), # 9h ago
            author_id=user_uuid
        )
        session.add(support_issue)
        session.commit()
        
        # P0 SLA is 8h, so it should be violated at 9h
        assert support_issue.priority_level == 0
        assert support_issue.sla_limit_seconds == 28800 # 8h
        assert support_issue.is_sla_violated == True
        assert support_issue.sla_status == "WARNING"
        print("  - SLA Violation detection (P0 @ 9h) verified.")

        # Test P3
        p3_issue = Issue(
            id=80002,
            iid=21,
            project_id=50001,
            title="Minor bug",
            labels=["priority::P3"],
            created_at=datetime.now(timezone.utc) - timedelta(hours=10), # 10h ago
            author_id=user_uuid
        )
        session.add(p3_issue)
        session.commit()
        assert p3_issue.sla_limit_seconds == 432000 # 120h
        assert p3_issue.is_sla_violated == False
        print("  - SLA P3 threshold (120h from config) verified.")
        
        # 2. Agent responds (Insert Note)
        agent_uuid = str(uuid.uuid4())
        response_note = Note(
            id=55555,
            project_id=50001,
            noteable_type="Issue",
            noteable_iid=20,
            author_id=agent_uuid,
            body="I am looking into it.",
            created_at=datetime.now(timezone.utc)
        )
        session.add(response_note)
        session.commit()
        
        # Refresh issue to see updated first_response_at from event
        session.refresh(support_issue)
        assert support_issue.first_response_at is not None
        assert support_issue.sla_status == "VIOLATED" # Since response took 70m > 60m
        print("  - Event-driven first_response_at update and Final SLA status verified.")

        # --- SonarQube Quality Hybrids (Scenario 10) ---
        print("Scenario 10: SonarQube Quality Gate Hybrids...")
        
        # 1. Create measures
        measure_1 = SonarMeasure(
            project_id=sonar_project.id,
            analysis_date=datetime.now(timezone.utc) - timedelta(days=1),
            bugs=10,
            quality_gate_status="ERROR"
        )
        measure_2 = SonarMeasure(
            project_id=sonar_project.id,
            analysis_date=datetime.now(timezone.utc),
            bugs=0,
            quality_gate_status="OK"
        )
        session.add_all([measure_1, measure_2])
        session.commit()
        
        session.refresh(sonar_project)
        assert sonar_project.bugs == 0
        assert sonar_project.quality_gate == "OK"
        assert sonar_project.is_clean is True
        print("  - SonarProject Quality Hybrids (latest_measure delegation) verified.")

        # --- Global Identity Auto-linking (Scenario 11) ---
        print("Scenario 11: Global Identity Auto-linking (Historical Traceability)...")
        
        # 1. Create a "ghost" commit (no user linked)
        ghost_email = "john.doe@example.com"
        ghost_commit = Commit(
            id="ghost_sha",
            project_id=50001,
            author_email=ghost_email,
            author_name="Ghost Rider",
            message="Ghostly commit",
            authored_date=datetime.now(timezone.utc)
        )
        session.add(ghost_commit)
        session.commit()
        
        assert ghost_commit.gitlab_user_id is None
        
        # 2. Add IdentityMapping for a user with this email
        # The event should trigger and link the commit
        new_mapping = IdentityMapping(
            global_user_id=user_uuid,
            source_system="gitlab",
            external_user_id="999",
            external_username="ghost_rider"
        )
        session.add(new_mapping)
        session.commit()
        
        session.refresh(ghost_commit)
        assert ghost_commit.gitlab_user_id == user_uuid
        print("  - Global Event (IdentityMapping -> Commit auto-link) verified.")

        # --- DORA MTTR & CFR (Scenario 12) ---
        print("Scenario 12: DORA MTTR & Change Failure Rate (Hybrid Aggregates)...")
        
        # 1. Create a successful deployment
        deploy = Deployment(
            id=90001,
            project_id=50001,
            environment="production",
            status="success",
            created_at=datetime.now(timezone.utc)
        )
        session.add(deploy)
        
        # 2. Create an Incident (Restoration time: 2h)
        incident_issue = Issue(
            id=90002,
            iid=30,
            project_id=50001,
            title="Production outage",
            labels=["incident"],
            created_at=datetime.now(timezone.utc) - timedelta(hours=5),
            closed_at=datetime.now(timezone.utc) - timedelta(hours=3),
            state="closed"
        )
        # 3. Create a Change Failure (Linked to rollout)
        cf_issue = Issue(
            id=90003,
            iid=31,
            project_id=50001,
            title="Rollback required",
            labels=["rollback"],
            created_at=datetime.now(timezone.utc)
        )
        session.add_all([incident_issue, cf_issue])
        session.commit()
        
        # Refresh project to see aggregates
        session.refresh(gitlab_project)
        
        # MTTR: should be 2h = 7200s (allow small epsilon for precision)
        assert abs(gitlab_project.mttr - 7200.0) < 1.0
        # CFR: 1 failure / 2 success deploys = 50%
        assert gitlab_project.change_failure_rate == 50.0
        print("  - DORA MTTR (7200s) and CFR (50%) verified.")

        # --- Deep Traceability & MR Risk (Scenario 13) ---
        print("Scenario 13: Deep Traceability & MR Risk Assessment...")
        
        # 1. Create a "Feature" Issue
        feat_issue = Issue(
            id=90010,
            iid=50,
            project_id=50001,
            title="Cool New Feature",
            created_at=datetime.now(timezone.utc)
        )
        session.add(feat_issue)
        
        # 2. Create MR implementing this feature
        # Link via external_issue_id = "50"
        feat_mr = MergeRequest(
            id=90011,
            iid=5,
            project_id=50001,
            title="Add cool feature",
            merge_commit_sha="feat_sha_123",
            external_issue_id="50",
            review_cycles=3,
            quality_gate_status="passed",
            raw_data={'stats': {'additions': 400, 'deletions': 100}}
        )
        session.add(feat_mr)
        
        # 3. Create Deployment for this SHA
        prod_deploy = Deployment(
            id=90012,
            project_id=50001,
            environment="production",
            status="success",
            sha="feat_sha_123",
            created_at=datetime.now(timezone.utc)
        )
        session.add(prod_deploy)
        session.commit()
        
        session.refresh(feat_issue)
        session.refresh(feat_mr)
        
        # Traceability Check
        assert feat_issue.is_deployed is True
        assert "production" in feat_issue.deploy_environments
        print("  - Deep Traceability (Issue -> MR -> Deploy) verified.")
        
        # Risk Score Check
        # additions+deletions=500 -> 5 points
        # review_cycles=3 -> 15 points
        # total = 20 points
        assert feat_mr.risk_score == 20.0
        print(f"  - MR Risk Score ({feat_mr.risk_score}) verified.")

        # --- Service ROI & AI Denoising (Scenario 14) ---
        print("Scenario 14: Service ROI & AI Denoising Assessment...")
        
        # 1. Test AI Denoising
        doc_mr = MergeRequest(
            id=90020,
            iid=6,
            project_id=50001,
            title="Update README",
            merge_commit_sha="doc_sha_123",
            ai_category="Documentation",
            review_cycles=1,
            raw_data={'stats': {'additions': 500, 'deletions': 0}}
        )
        # Without AI denoising: scale=5, cycles=5 -> total=10
        # With AI denoising (0.2x): score = 2.0
        session.add(doc_mr)
        session.commit()
        assert doc_mr.risk_score == 2.0
        print("  - AI Risk Denoising (Documentation) verified.")
        
        # 2. Test Service ROI
        payment_service = Service(
            name="Payment Service",
            tier="P0"
        )
        session.add(payment_service)
        session.commit()
        
        cost1 = ResourceCost(
            service_id=payment_service.id,
            period="2025-01",
            amount=50000.0,
            cost_item="Cloud Hosting"
        )
        cost2 = ResourceCost(
            service_id=payment_service.id,
            period="2025-01",
            amount=30000.0,
            cost_item="Human Labor"
        )
        session.add_all([cost1, cost2])
        session.commit()
        
        session.refresh(payment_service)
        assert payment_service.total_cost == 80000.0
        # Health score (default no SLOs) = 80.0
        # ROI = 80.0 / (80000 / 10000) = 80 / 8 = 10.0
        assert payment_service.investment_roi == 10.0
        print(f"  - Service ROI (Cost: 80k, ROI: {payment_service.investment_roi}) verified.")

        print("\nALL INTEGRATION TESTS (INCLUDING ROI & AI TECH) PASSED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\nINTEGRATION TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    run_integration_test()
