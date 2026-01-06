"""GitLab 测试管理模块数据模型。

本模块定义了用于二开测试管理功能的核心模型，包括测试用例实体及其与 Issue 的关联关系。
遵循 GitLab 社区版二开建议书中的数据库设计原则。
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, JSON, DateTime, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from devops_collector.models.base_models import Base, TimestampMixin, User

class GTMTestCase(Base, TimestampMixin):
    """GitLab 测试用例模型。
    
    存储测试用例的结构化信息，包括标题、描述（预置条件）和详细的执行步骤。
    """
    __tablename__ = 'gtm_test_cases'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False)
    iid = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    priority = Column(String(20))
    test_type = Column(String(50))
    pre_conditions = Column(Text)
    description = Column(Text)
    test_steps = Column(JSON, default=[])
    
    author = relationship('User', primaryjoin='and_(User.global_user_id==GTMTestCase.author_id, User.is_current==True)', back_populates='test_cases')
    project = relationship('GitLabProject', back_populates='test_cases')
    linked_issues = relationship('GitLabIssue', secondary='gtm_test_case_issue_links', back_populates='associated_test_cases')
    associated_requirements = relationship('GTMRequirement', secondary='gtm_requirement_test_case_links', back_populates='test_cases')

    @hybrid_property
    def execution_count(self) -> int:
        """用例被执行的总次数。"""
        return len(self.execution_records)

    @execution_count.expression
    def execution_count(cls):
        """用例被执行的总次数的 SQL 表达式。"""
        return func.count(GTMTestExecutionRecord.id).label('execution_count')
    
    execution_records = relationship(
        'GTMTestExecutionRecord', 
        primaryjoin='foreign(GTMTestExecutionRecord.test_case_iid) == GTMTestCase.iid', 
        viewonly=True, 
        overlaps='project'
    )

    def __repr__(self) -> str:
        """返回测试用例的字符串表示。"""
        return f"<GTMTestCase(iid={self.iid}, title='{self.title}')>"

class GTMTestCaseIssueLink(Base, TimestampMixin):
    """测试用例与 Issue 的关联表 (gtm_test_case_issue_links)。"""
    __tablename__ = 'gtm_test_case_issue_links'
    id = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, ForeignKey('gtm_test_cases.id', ondelete='CASCADE'), nullable=False)
    issue_id = Column(Integer, ForeignKey('gitlab_issues.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self) -> str:
        """返回用例与 Issue 关联的字符串表示。"""
        return f'<GTMTestCaseIssueLink(tc={self.test_case_id}, issue={self.issue_id})>'

class GTMRequirement(Base, TimestampMixin):
    """GitLab 需求模型。"""
    __tablename__ = 'gtm_requirements'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False)
    iid = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    state = Column(String(20), default='opened')
    
    author = relationship('User', primaryjoin='and_(User.global_user_id==GTMRequirement.author_id, User.is_current==True)', back_populates='requirements')
    project = relationship('GitLabProject', back_populates='requirements')
    test_cases = relationship('GTMTestCase', secondary='gtm_requirement_test_case_links', back_populates='associated_requirements')
    linked_bugs = association_proxy('test_cases', 'linked_issues')

    def __repr__(self) -> str:
        """返回需求的字符串表示。"""
        return f"<GTMRequirement(iid={self.iid}, title='{self.title}', state='{self.state}')>"

class GTMRequirementTestCaseLink(Base, TimestampMixin):
    """需求与测试用例的关联表 (gtm_requirement_test_case_links)。"""
    __tablename__ = 'gtm_requirement_test_case_links'
    id = Column(Integer, primary_key=True)
    requirement_id = Column(Integer, ForeignKey('gtm_requirements.id', ondelete='CASCADE'), nullable=False)
    test_case_id = Column(Integer, ForeignKey('gtm_test_cases.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self) -> str:
        """返回需求与用例关联的字符串表示。"""
        return f'<GTMRequirementTestCaseLink(req={self.requirement_id}, tc={self.test_case_id})>'

class GTMTestExecutionRecord(Base, TimestampMixin):
    """测试执行完整审计记录模型 (gtm_test_execution_records)。"""
    __tablename__ = 'gtm_test_execution_records'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id', ondelete='CASCADE'), nullable=False)
    test_case_iid = Column(Integer, nullable=False, index=True)
    result = Column(String(20), nullable=False)
    executed_at = Column(DateTime(timezone=True), default=func.now())
    executor_name = Column(String(100))
    executor_uid = Column(UUID(as_uuid=True))
    comment = Column(Text)
    pipeline_id = Column(Integer)
    environment = Column(String(50), default='Default')
    title = Column(String(255))
    project = relationship('GitLabProject', back_populates='test_execution_records')

    def __repr__(self) -> str:
        """返回执行记录的字符串表示。"""
        return f'<GTMTestExecutionRecord(iid={self.test_case_iid}, result={self.result})>'