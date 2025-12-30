import sys
import os

# 确保可以导入项目模块
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from devops_collector.auth.database import SessionLocal, engine
from devops_collector.models.base_models import User, Organization, IdentityMapping
from devops_collector.gitlab_sync.models.issue_metadata import IssueMetadata
from devops_collector.gitlab_sync.services.security import IssueSecurityProvider

def setup_test_data(db: Session):
    """准备测试数据：创建用户、部门和工单镜像"""
    print("--- 步骤 1: 准备测试数据 ---")
    
    # 1. 创建部门
    biz_dept = db.query(Organization).filter(Organization.org_name == "业务部").first()
    if not biz_dept:
        biz_dept = Organization(org_name="业务部", org_code="BIZ")
        db.add(biz_dept)
    
    rd_dept = db.query(Organization).filter(Organization.org_name == "研发部").first()
    if not rd_dept:
        rd_dept = Organization(org_name="研发部", org_code="RD")
        db.add(rd_dept)
    
    db.commit()
    db.refresh(biz_dept)
    db.refresh(rd_dept)

    # 2. 创建用户 (业务部用户)
    test_user = db.query(User).filter(User.primary_email == "biz_user@example.com").first()
    if not test_user:
        test_user = User(
            full_name="业务员小张",
            primary_email="biz_user@example.com",
            employee_id="BIZ001",
            department_id=biz_dept.org_id,
            identity_map={"gitlab": {"username": "zhangsan_biz"}}
        )
        db.add(test_user)
    else:
        # 确保数据最新
        test_user.department_id = biz_dept.org_id
        test_user.identity_map = {"gitlab": {"username": "zhangsan_biz"}}
    
    db.commit()
    db.refresh(test_user)

    # 3. 清理旧测试工单
    db.query(IssueMetadata).filter(IssueMetadata.title.like("TEST_VISIBILITY_%")).delete()
    
    # 4. 创建模拟工单：
    # 工单 A: 研发部的项目，由业务员小张提报 (跨部门工单)
    issue_cross = IssueMetadata(
        gitlab_project_id=999,
        gitlab_issue_iid=1,
        global_issue_id=10001,
        dept_name="研发部", # 这个工单归属于研发部项目
        title="TEST_VISIBILITY_跨部门需求",
        state="opened",
        author_username="zhangsan_biz", # 提报人是业务部的小张
        author_dept_name="业务部",
        sync_status=1
    )
    
    # 工单 B: 研发部的项目，由研发人员提报 (小张不应该看到)
    issue_private = IssueMetadata(
        gitlab_project_id=999,
        gitlab_issue_iid=2,
        global_issue_id=10002,
        dept_name="研发部",
        title="TEST_VISIBILITY_研发部内部任务",
        state="opened",
        author_username="rd_engineer",
        author_dept_name="研发部",
        sync_status=1
    )

    db.add(issue_cross)
    db.add(issue_private)
    db.commit()
    
    return test_user

def run_visibility_test():
    """执行可见性验证"""
    db = SessionLocal()
    try:
        test_user = setup_test_data(db)
        print(f"当前测试用户: {test_user.full_name} (部门: 业务部, GitLab账号: zhangsan_biz)")
        
        print("\n--- 步骤 2: 执行安全过滤查询 ---")
        visible_issues = IssueSecurityProvider.get_visible_issues(db, test_user)
        
        print(f"找到可见工单数量: {len(visible_issues)}")
        
        titles = [i.title for i in visible_issues if i.title.startswith("TEST_VISIBILITY")]
        print(f"可见工单标题列表: {titles}")

        # 验证逻辑
        has_cross = "TEST_VISIBILITY_跨部门需求" in titles
        has_private = "TEST_VISIBILITY_研发部内部任务" in titles

        print("\n--- 步骤 3: 验证结果判定 ---")
        if has_cross and not has_private:
            print("✅ 验证通过！")
            print("  - 用户成功看到了自己跨部门提报的工单。")
            print("  - 用户被成功拦截，无法看到研发部内部的其他工单。")
        else:
            print("❌ 验证失败！")
            if not has_cross: print("  - 错误：用户没看到自己提报的工单。")
            if has_private: print("  - 错误：隔离泄露，用户看到了研发部内部工单。")

    finally:
        db.close()

if __name__ == "__main__":
    run_visibility_test()
