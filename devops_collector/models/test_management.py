"""GitLab 测试管理模块数据模型。

本模块定义了用于二开测试管理功能的核心模型，包括测试用例实体及其与 Issue 的关联关系。
遵循 GitLab 社区版二开建议书中的数据库设计原则。

Typical Usage:
    test_case = TestCase(title="验证登录", test_steps=[{"step": "输入密码", "expected": "显示星号"}])
    session.add(test_case)
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, JSON, DateTime, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from devops_collector.models.base_models import Base, TimestampMixin, User

class TestCase(Base, TimestampMixin):
    """测试用例模型。
    
    存储测试用例的结构化信息，包括标题、描述（预置条件）和详细的执行步骤。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 归属项目的 ID（关联 projects 表）。
        author_id (UUID): 创建者的用户 ID（关联 mdm_identities 表）。
        iid (int): 项目内自增 ID（类似 Issue #123）。
        title (str): 测试用例标题。
        priority (str): 优先级 (P0, P1, P2, P3)。
        test_type (str): 用例类型 (功能测试, 性能测试, 安全测试等)。
        pre_conditions (str): 执行前的预置条件。
        description (str): 详细描述。
        test_steps (list): 结构化步骤列表，存储为 JSON。
            格式: [{"action": "动作", "expected": "预期结果"}]
        author (User): 关联的作者对象。
        project (Project): 关联的项目对象。
        linked_issues (List[Issue]): 该用例关联的 Issue 列表。
        associated_requirements (List[Requirement]): 该用例关联的需求列表。
    """
    __tablename__ = 'test_cases'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False)
    iid = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    priority = Column(String(20))
    test_type = Column(String(50))
    pre_conditions = Column(Text)
    description = Column(Text)
    test_steps = Column(JSON, default=[])
    author = relationship('User', primaryjoin='and_(User.global_user_id==TestCase.author_id, User.is_current==True)', back_populates='test_cases')
    project = relationship('Project', back_populates='test_cases')
    linked_issues = relationship('Issue', secondary='test_case_issue_links', back_populates='associated_test_cases')
    associated_requirements = relationship('Requirement', secondary='requirement_test_case_links', back_populates='test_cases')

    @hybrid_property
    def execution_count(self):
        """用例被执行的总次数。"""
        return len(self.execution_records)

    @execution_count.expression
    def execution_count(cls):
        '''"""TODO: Add description.

Args:
    cls: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return func.count(TestExecutionRecord.id).label('execution_count')
    execution_records = relationship('TestExecutionRecord', primaryjoin='foreign(TestExecutionRecord.test_case_iid) == TestCase.iid', viewonly=True, overlaps='project')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<TestCase(iid={self.iid}, title='{self.title}')>"

class TestCaseIssueLink(Base, TimestampMixin):
    """测试用例与 Issue 的关联表。
    
    实现多对多关系。

    Attributes:
        id (int): 自增主键。
        test_case_id (int): 关联的测试用例 ID。
        issue_id (int): 关联的 Issue ID。
    """
    __tablename__ = 'test_case_issue_links'
    id = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False)
    issue_id = Column(Integer, ForeignKey('issues.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f'<TestCaseIssueLink(tc={self.test_case_id}, issue={self.issue_id})>'

class Requirement(Base, TimestampMixin):
    """需求模型。

    代表业务层面的功能需求，用于实现从需求到测试用例的端到端追溯。

    Attributes:
        id (int): 自增主键。
        project_id (int): 归属项目的 ID。
        author_id (UUID): 创建者的用户 ID。
        iid (int): 项目内自增 ID。
        title (str): 需求标题。
        description (str): 需求详细描述。
        state (str): 需求状态 (opened, satisfied, failed)。
        test_cases (List[TestCase]): 关联的测试用例列表。
        author (User): 关联的作者。
        project (Project): 关联的项目。
    """
    __tablename__ = 'requirements'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False)
    iid = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    state = Column(String(20), default='opened')
    author = relationship('User', primaryjoin='and_(User.global_user_id==Requirement.author_id, User.is_current==True)', back_populates='requirements')
    project = relationship('Project', back_populates='requirements')
    test_cases = relationship('TestCase', secondary='requirement_test_case_links', back_populates='associated_requirements')
    linked_bugs = association_proxy('test_cases', 'linked_issues')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<Requirement(iid={self.iid}, title='{self.title}', state='{self.state}')>"

class RequirementTestCaseLink(Base, TimestampMixin):
    """需求与测试用例的关联表。

    Attributes:
        id (int): 自增主键。
        requirement_id (int): 关联的需求 ID。
        test_case_id (int): 关联的测试用例 ID。
    """
    __tablename__ = 'requirement_test_case_links'
    id = Column(Integer, primary_key=True)
    requirement_id = Column(Integer, ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False)
    test_case_id = Column(Integer, ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f'<RequirementTestCaseLink(req={self.requirement_id}, tc={self.test_case_id})>'

class TestExecutionRecord(Base, TimestampMixin):
    """测试执行完整审计记录模型。
    
    用于记录每次测试执行的详细结果、执行人及环境信息。

    Attributes:
        id (int): 自增主键。
        project_id (int): 项目 ID。
        test_case_iid (int): 关联的用例 IID。
        result (str): 结果 (passed, failed, blocked)。
        executed_at (datetime): 执行时间。
        executor_name (str): 执行人名称。
        executor_uid (UUID): 执行人在系统中的唯一 ID。
        comment (str): 评论/备忘。
        pipeline_id (int): 关联的流水线 ID。
        environment (str): 执行环境。
        title (str): 冗余存放的用例标题。
    """
    __tablename__ = 'test_execution_records'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    test_case_iid = Column(Integer, nullable=False, index=True)
    result = Column(String(20), nullable=False)
    executed_at = Column(DateTime(timezone=True), default=func.now())
    executor_name = Column(String(100))
    executor_uid = Column(UUID(as_uuid=True))
    comment = Column(Text)
    pipeline_id = Column(Integer)
    environment = Column(String(50), default='Default')
    title = Column(String(255))
    project = relationship('Project', back_populates='test_execution_records')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f'<TestExecutionRecord(iid={self.test_case_iid}, result={self.result})>'