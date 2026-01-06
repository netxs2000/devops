"""禅道 (ZenTao) 全量数据模型

定义禅道相关的 SQLAlchemy ORM 模型，支持产品、执行、需求、缺陷、用例、构建和发布。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from devops_collector.models.base_models import Base

class ZenTaoProduct(Base):
    """禅道产品模型 (zentao_products)。

    Attributes:
        id (int): 禅道原始 Product ID。
        name (str): 产品名称。
        code (str): 产品代号。
        description (str): 产品描述。
        status (str): 状态 (normal, closed 等)。
        gitlab_project_id (int): 关联的 GitLab 项目 ID。
        last_synced_at (datetime): 最近同步时间。
        sync_status (str): 同步状态 (PENDING, SUCCESS, FAILED)。
        executions (List[ZenTaoExecution]): 关联的执行/迭代列表。
        plans (List[ZenTaoProductPlan]): 关联的产品计划。
        issues (List[ZenTaoIssue]): 关联的问题 (需求/Bug)。
        test_cases (List[ZenTaoTestCase]): 关联的用例。
        builds (List[ZenTaoBuild]): 关联的构建版本。
        releases (List[ZenTaoRelease]): 关联的发布记录。
    """
    __tablename__ = 'zentao_products'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100))
    description = Column(Text)
    status = Column(String(20))
    gitlab_project_id = Column(Integer, ForeignKey('gitlab_projects.id'), nullable=True)
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    raw_data = Column(JSON)
    executions = relationship('ZenTaoExecution', back_populates='product', cascade='all, delete-orphan')
    plans = relationship('ZenTaoProductPlan', back_populates='product', cascade='all, delete-orphan')
    issues = relationship('ZenTaoIssue', back_populates='product', cascade='all, delete-orphan')
    test_cases = relationship('ZenTaoTestCase', back_populates='product', cascade='all, delete-orphan')
    builds = relationship('ZenTaoBuild', back_populates='product', cascade='all, delete-orphan')
    releases = relationship('ZenTaoRelease', back_populates='product', cascade='all, delete-orphan')
    actions = relationship('ZenTaoAction', back_populates='product', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoProduct(id={self.id}, name='{self.name}')>"

class ZenTaoProductPlan(Base):
    """禅道产品计划模型 (zentao_product_plans)。
    
    用于规划产品的分阶段交付。需求和 Bug 通常关联到计划。

    Attributes:
        id (int): 禅道计划 ID。
        product_id (int): 所属产品 ID。
        title (str): 计划标题。
        begin (datetime): 开始日期。
        end (datetime): 结束日期。
        status (str): 计划状态 (wait, doing, done, closed)。
        opened_by_user_id (UUID): 创建人 OneID。
    """
    __tablename__ = 'zentao_product_plans'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    title = Column(String(255))
    begin = Column(DateTime)
    end = Column(DateTime)
    desc = Column(Text)
    status = Column(String(20))
    opened_by = Column(String(100))
    opened_by_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    opened_date = Column(DateTime)
    product = relationship('ZenTaoProduct', back_populates='plans')
    issues = relationship('ZenTaoIssue', back_populates='plan')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoProductPlan(id={self.id}, title='{self.title}')>"

class ZenTaoExecution(Base):
    """禅道执行模型 (zentao_executions)，即迭代/Sprint。

    Attributes:
        id (int): 禅道执行 ID。
        product_id (int): 所属产品 ID。
        name (str): 迭代名称。
        type (str): 类型 (sprint, stage)。
        status (str): 状态 (wait, doing, suspended, closed)。
        begin (datetime): 计划开始时间。
        end (datetime): 计划结束时间。
    """
    __tablename__ = 'zentao_executions'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    name = Column(String(255))
    code = Column(String(100))
    type = Column(String(20))
    status = Column(String(20))
    begin = Column(DateTime)
    end = Column(DateTime)
    real_began = Column(DateTime)
    real_end = Column(DateTime)
    product = relationship('ZenTaoProduct', back_populates='executions')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoExecution(id={self.id}, name='{self.name}')>"

class ZenTaoIssue(Base):
    """禅道 Issue 模型 (zentao_issues)，包含需求 (Story) 和 缺陷 (Bug)。

    Attributes:
        id (int): 禅道原始 ID。
        product_id (int): 所属产品 ID。
        execution_id (int): 所属执行 ID。
        plan_id (int): 关联计划 ID。
        title (str): 标题。
        type (str): 类型 (feature, bug)。
        status (str): 状态。
        priority (int): 优先级。
        opened_by_user_id (UUID): 创建人 OneID。
        assigned_to_user_id (UUID): 目前处理人 OneID。
        closed_at (datetime): 关闭时间。
        first_commit_sha (str): 关联的代码提交。
    """
    __tablename__ = 'zentao_issues'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    execution_id = Column(Integer, ForeignKey('zentao_executions.id'), nullable=True)
    plan_id = Column(Integer, ForeignKey('zentao_product_plans.id'), nullable=True)
    title = Column(String(500), nullable=False)
    type = Column(String(50))
    status = Column(String(50))
    priority = Column(Integer)
    opened_by = Column(String(100))
    assigned_to = Column(String(100))
    opened_by_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    raw_data = Column(JSON)
    first_commit_sha = Column(String(100))
    first_fix_date = Column(DateTime(timezone=True))
    product = relationship('ZenTaoProduct', back_populates='issues')
    plan = relationship('ZenTaoProductPlan', back_populates='issues')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoIssue(id={self.id}, title='{self.title[:20]}...', type='{self.type}')>"

class ZenTaoTestCase(Base):
    """禅道测试用例模型 (zentao_test_cases)。

    Attributes:
        id (int): 禅道用例 ID。
        product_id (int): 关联产品 ID。
        title (str): 用例标题。
        is_automated (bool): 是否已实现自动化。
        automation_type (str): 自动化工具类型。
        last_run_result (str): 最近执行结果。
    """
    __tablename__ = 'zentao_test_cases'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    title = Column(String(500))
    type = Column(String(50))
    status = Column(String(20))
    opened_by = Column(String(100))
    opened_by_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    opened_date = Column(DateTime)
    last_run_result = Column(String(20))
    is_automated = Column(Boolean, default=False)
    automation_type = Column(String(50))
    script_path = Column(String(500))
    product = relationship('ZenTaoProduct', back_populates='test_cases')
    results = relationship('ZenTaoTestResult', back_populates='test_case', cascade='all, delete-orphan')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoTestCase(id={self.id}, title='{self.title}')>"

class ZenTaoTestResult(Base):
    """禅道测试执行结果模型 (zentao_test_results)。

    Attributes:
        id (int): 结果 ID。
        case_id (int): 关联用例 ID。
        result (str): 执行结果 (pass, fail, blocked)。
        date (datetime): 执行时间。
    """
    __tablename__ = 'zentao_test_results'
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('zentao_test_cases.id'), nullable=False)
    build_id = Column(Integer, nullable=True)
    result = Column(String(20))
    date = Column(DateTime)
    last_run_by = Column(String(100))
    test_case = relationship('ZenTaoTestCase', back_populates='results')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoTestResult(case_id={self.case_id}, result='{self.result}')>"

class ZenTaoBuild(Base):
    """禅道版本/构建模型 (zentao_builds)。

    Attributes:
        id (int): 构建 ID。
        product_id (int): 所属产品 ID。
        execution_id (int): 关联执行 ID。
        name (str): 版本名称。
        builder_user_id (UUID): 构建人 OneID。
    """
    __tablename__ = 'zentao_builds'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    execution_id = Column(Integer, ForeignKey('zentao_executions.id'), nullable=True)
    name = Column(String(255))
    builder = Column(String(100))
    builder_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    date = Column(DateTime)
    product = relationship('ZenTaoProduct', back_populates='builds')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoBuild(id={self.id}, name='{self.name}')>"

class ZenTaoRelease(Base):
    """禅道发布记录模型 (zentao_releases)。

    Attributes:
        id (int): 发布 ID。
        product_id (int): 产品 ID。
        name (str): 发布名称。
        date (datetime): 发布时间。
        status (str): 状态。
    """
    __tablename__ = 'zentao_releases'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    build_id = Column(Integer, ForeignKey('zentao_builds.id'), nullable=True)
    name = Column(String(255))
    date = Column(DateTime)
    status = Column(String(50))
    opened_by = Column(String(100))
    opened_by_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    product = relationship('ZenTaoProduct', back_populates='releases')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoRelease(id={self.id}, name='{self.name}')>"

class ZenTaoAction(Base):
    """禅道操作日志模型 (zentao_actions)。

    Attributes:
        id (int): 日志 ID。
        object_type (str): 对象类型 (story, bug, project 等)。
        object_id (int): 关联对象 ID。
        actor_user_id (UUID): 操作人 OneID。
        action (str): 操作类型 (opened, finished, closed 等)。
        date (datetime): 操作时间。
    """
    __tablename__ = 'zentao_actions'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    object_type = Column(String(50))
    object_id = Column(Integer)
    actor = Column(String(100))
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    action = Column(String(100))
    date = Column(DateTime)
    comment = Column(Text)
    product = relationship('ZenTaoProduct', back_populates='actions')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<ZenTaoAction(obj_type='{self.object_type}', action='{self.action}')>"