"""GitLab 测试管理模块数据模型。

本模块定义了用于二开测试管理功能的核心模型，包括测试用例实体及其与 Issue 的关联关系。
遵循 GitLab 社区版二开建议书中的数据库设计原则。

Typical Usage:
    test_case = TestCase(title="验证登录", test_steps=[{"step": "输入密码", "expected": "显示星号"}])
    session.add(test_case)
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from devops_collector.models.base_models import Base, TimestampMixin


class TestCase(Base, TimestampMixin):
    """测试用例模型。
    
    存储测试用例的结构化信息，包括标题、描述（预置条件）和详细的执行步骤。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 归属项目的 ID（关联 projects 表）。
        author_id (int): 创建者的用户 ID（关联 users 表）。
        iid (int): 项目内自增 ID（类似 Issue #123）。
        title (str): 测试用例标题。
        description (str): 预置条件或详细描述。
        test_steps (list): 结构化步骤列表，存储为 JSONB。
            格式: [{"action": "动作", "expected": "预期结果"}]
        author (User): 关联的作者对象。
        project (Project): 关联的项目对象。
        linked_issues (list[Issue]): 该用例关联的 Issue 列表。
    """
    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', on_delete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    iid = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    priority = Column(String(20)) # P0, P1, P2, P3
    test_type = Column(String(50)) # 功能测试, 性能测试, 安全测试等
    pre_conditions = Column(Text)
    description = Column(Text)
    test_steps = Column(JSON, default=[])  # 存储结构化步骤: [{"action": "...", "expected": "..."}]

    # 关系映射
    author = relationship("User")
    project = relationship("Project")
    linked_issues = relationship(
        "Issue",
        secondary="test_case_issue_links",
        back_populates="associated_test_cases"
    )
    associated_requirements = relationship(
        "Requirement",
        secondary="requirement_test_case_links",
        back_populates="test_cases"
    )

    def __repr__(self) -> str:
        return f"<TestCase(iid={self.iid}, title='{self.title}')>"


class TestCaseIssueLink(Base, TimestampMixin):
    """测试用例与 Issue 的关联表。
    
    实现多对多关系，允许一个用例关联多个 Issue（如回归测试中涉及多个任务），
    也允许一个 Issue 关联多个用例。
    
    Attributes:
        id (int): 自增主键。
        test_case_id (int): 关联的测试用例 ID。
        issue_id (int): 关联的 Issue ID。
    """
    __tablename__ = 'test_case_issue_links'

    id = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, ForeignKey('test_cases.id', on_delete='CASCADE'), nullable=False)
    issue_id = Column(Integer, ForeignKey('issues.id', on_delete='CASCADE'), nullable=False)

    def __repr__(self) -> str:
        return f"<TestCaseIssueLink(tc={self.test_case_id}, issue={self.issue_id})>"


class Requirement(Base, TimestampMixin):
    """需求模型。

    代表业务层面的功能需求，用于实现从需求到测试用例的端到端追溯。

    Attributes:
        id (int): 自增主键。
        project_id (int): 归属项目的 ID。
        author_id (int): 创建者的用户 ID。
        iid (int): 项目内自增 ID。
        title (str): 需求标题。
        description (str): 需求详细描述。
        state (str): 需求状态 (opened, satisfied, failed)。
        test_cases (list[TestCase]): 关联的测试用例列表。
    """
    __tablename__ = 'requirements'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', on_delete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    iid = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    state = Column(String(20), default="opened") # opened, satisfied, failed

    # 关系映射
    author = relationship("User")
    project = relationship("Project")
    test_cases = relationship(
        "TestCase",
        secondary="requirement_test_case_links",
        back_populates="associated_requirements"
    )

    def __repr__(self) -> str:
        return f"<Requirement(iid={self.iid}, title='{self.title}', state='{self.state}')>"


class RequirementTestCaseLink(Base, TimestampMixin):
    """需求与测试用例的关联表。

    实现需求与测试用例之间的多对多关系。

    Attributes:
        id (int): 自增主键。
        requirement_id (int): 关联的需求 ID。
        test_case_id (int): 关联的测试用例 ID。
    """
    __tablename__ = 'requirement_test_case_links'

    id = Column(Integer, primary_key=True)
    requirement_id = Column(Integer, ForeignKey('requirements.id', on_delete='CASCADE'), nullable=False)
    test_case_id = Column(Integer, ForeignKey('test_cases.id', on_delete='CASCADE'), nullable=False)

    def __repr__(self) -> str:
        return f"<RequirementTestCaseLink(req={self.requirement_id}, tc={self.test_case_id})>"
