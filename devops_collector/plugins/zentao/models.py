"""禅道 (ZenTao) 全量数据模型

定义禅道相关的 SQLAlchemy ORM 模型，支持产品、执行、需求、缺陷、用例、构建和发布。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

# 从公共基础模型导入 Base
from devops_collector.models.base_models import Base

class ZenTaoProduct(Base):
    """禅道产品模型。"""
    __tablename__ = 'zentao_products'
    
    id = Column(Integer, primary_key=True)  # 禅道原始 Product ID
    name = Column(String(255), nullable=False)
    code = Column(String(100))
    description = Column(Text)
    status = Column(String(20))
    
    # 关联 GitLab 项目
    gitlab_project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    
    # 同步状态
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    raw_data = Column(JSON)
    
    executions = relationship("ZenTaoExecution", back_populates="product", cascade="all, delete-orphan")
    plans = relationship("ZenTaoProductPlan", back_populates="product", cascade="all, delete-orphan")
    issues = relationship("ZenTaoIssue", back_populates="product", cascade="all, delete-orphan")
    test_cases = relationship("ZenTaoTestCase", back_populates="product", cascade="all, delete-orphan")
    builds = relationship("ZenTaoBuild", back_populates="product", cascade="all, delete-orphan")
    releases = relationship("ZenTaoRelease", back_populates="product", cascade="all, delete-orphan")
    actions = relationship("ZenTaoAction", back_populates="product", cascade="all, delete-orphan")


class ZenTaoProductPlan(Base):
    """禅道产品计划模型。
    
    用于规划产品的分阶段交付。需求和 Bug 通常关联到计划。
    """
    __tablename__ = 'zentao_product_plans'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    title = Column(String(255))
    begin = Column(DateTime)
    end = Column(DateTime)
    desc = Column(Text)
    status = Column(String(20)) # wait, doing, done, closed
    
    opened_by = Column(String(100))
    opened_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    opened_date = Column(DateTime)
    
    product = relationship("ZenTaoProduct", back_populates="plans")
    issues = relationship("ZenTaoIssue", back_populates="plan")
    raw_data = Column(JSON)


class ZenTaoExecution(Base):
    """禅道执行模型 (即迭代/Sprint)。"""
    __tablename__ = 'zentao_executions'
    
    id = Column(Integer, primary_key=True)  # 禅道原始 Execution ID
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    name = Column(String(255))
    code = Column(String(100))
    type = Column(String(20))  # sprint, stage, etc.
    status = Column(String(20))  # wait, doing, suspended, closed
    
    begin = Column(DateTime)
    end = Column(DateTime)
    real_began = Column(DateTime)
    real_end = Column(DateTime)
    
    product = relationship("ZenTaoProduct", back_populates="executions")
    raw_data = Column(JSON)


class ZenTaoIssue(Base):
    """禅道 Issue 模型 (需求 Story 和 缺陷 Bug)。"""
    __tablename__ = 'zentao_issues'
    
    id = Column(Integer, primary_key=True)  # 禅道原始 ID
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    execution_id = Column(Integer, ForeignKey('zentao_executions.id'), nullable=True)
    plan_id = Column(Integer, ForeignKey('zentao_product_plans.id'), nullable=True)
    
    title = Column(String(500), nullable=False)
    type = Column(String(50))  # feature (for Story), bug (for Bug)
    status = Column(String(50))
    priority = Column(Integer)
    
    opened_by = Column(String(100))
    assigned_to = Column(String(100))
    
    # 关联系统全局用户
    opened_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # 向后兼容
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    raw_data = Column(JSON)
    
    product = relationship("ZenTaoProduct", back_populates="issues")
    plan = relationship("ZenTaoProductPlan", back_populates="issues")


class ZenTaoTestCase(Base):
    """禅道测试用例模型。"""
    __tablename__ = 'zentao_test_cases'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    title = Column(String(500))
    type = Column(String(50))
    status = Column(String(20))
    
    opened_by = Column(String(100))
    opened_date = Column(DateTime)
    
    last_run_result = Column(String(20))  # pass, fail, blocked
    
    product = relationship("ZenTaoProduct", back_populates="test_cases")
    results = relationship("ZenTaoTestResult", back_populates="test_case", cascade="all, delete-orphan")
    raw_data = Column(JSON)


class ZenTaoTestResult(Base):
    """禅道测试结果模型。"""
    __tablename__ = 'zentao_test_results'
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('zentao_test_cases.id'), nullable=False)
    build_id = Column(Integer, nullable=True)
    
    result = Column(String(20))  # pass, fail, blocked
    date = Column(DateTime)
    last_run_by = Column(String(100))
    
    test_case = relationship("ZenTaoTestCase", back_populates="results")
    raw_data = Column(JSON)


class ZenTaoBuild(Base):
    """禅道版本 (构建) 模型。"""
    __tablename__ = 'zentao_builds'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    execution_id = Column(Integer, ForeignKey('zentao_executions.id'), nullable=True)
    
    name = Column(String(255))
    builder = Column(String(100))
    builder_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    date = Column(DateTime)
    
    product = relationship("ZenTaoProduct", back_populates="builds")
    raw_data = Column(JSON)


class ZenTaoRelease(Base):
    """禅道发布模型。"""
    __tablename__ = 'zentao_releases'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    build_id = Column(Integer, ForeignKey('zentao_builds.id'), nullable=True)
    
    name = Column(String(255))
    date = Column(DateTime)
    status = Column(String(50))
    opened_by = Column(String(100))
    
    product = relationship("ZenTaoProduct", back_populates="releases")
    raw_data = Column(JSON)


class ZenTaoAction(Base):
    """禅道操作日志模型。
    
    记录禅道中几乎所有对象（需求、任务、缺陷、项目等）的操作流水。
    """
    __tablename__ = 'zentao_actions'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('zentao_products.id'), nullable=False)
    object_type = Column(String(50)) # story, bug, project, execution, etc.
    object_id = Column(Integer)
    
    actor = Column(String(100))
    actor_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100)) # opened, assigned, finished, closed, etc.
    date = Column(DateTime)
    comment = Column(Text)
    
    product = relationship("ZenTaoProduct", back_populates="actions")
    raw_data = Column(JSON)
