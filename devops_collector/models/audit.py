"""
系统核心审计模型定义 (Audit Logging Core).

按照等保三级 (MLPS L3) 标准设计，用于全量追踪 Portal 及 Worker 的操作痕迹。
包含 Who (操作者), When (时间), Where (IP/请求ID), What (变更清单), Result (状态)。
"""

from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, UUID as UUID_TYPE
from devops_collector.models.base_models import Base

class AuditLog(Base):
    """系统合规审计日志表。"""
    __tablename__ = "sys_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="审计记录ID")
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True, comment="物理操作发生时间")
    
    # 1. 身份维度 (Who)
    actor_id = Column(UUID_TYPE(as_uuid=True), index=True, nullable=True, comment="操作者全局唯一标识 (Global User ID)")
    actor_name = Column(String(200), nullable=True, comment="操作者姓名快照")
    client_ip = Column(String(50), nullable=True, comment="来源 IP 地址")
    
    # 2. 动作维度 (What)
    # 核心动作: CREATE, UPDATE, DELETE, LOGIN, EXPORT, DOWNLOAD, SYNC
    action = Column(String(50), index=True, nullable=False, comment="动作类型")
    
    # 3. 资源维度 (Where)
    resource_type = Column(String(50), index=True, comment="操作对象类型 (一般为表名)")
    resource_id = Column(String(100), index=True, comment="操作对象实例 ID")
    
    # 4. 变更细节 (Context)
    # 存储格式: {"field_name": {"old": "value1", "new": "value2"}}
    changes = Column(JSON, nullable=True, comment="字段级变更增量 Diff (JSON)")
    
    # 5. 追踪维度 (Traceability)
    request_id = Column(String(100), index=True, nullable=True, comment="关联请求追踪 ID (全链路对齐)")
    correlation_id = Column(String(100), index=True, nullable=True, comment="业务关联 ID (如同步任务ID)")
    
    # 6. 辅助信息
    status = Column(String(20), default="SUCCESS", index=True, comment="操作执行状态 (SUCCESS/FAILURE)")
    remark = Column(Text, nullable=True, comment="详细备注或报错信息堆栈")

    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action}', target='{self.resource_type}:{self.resource_id}')>"

    @classmethod
    def create_log(cls, db_session, **kwargs):
        """同步创建一条审计日志的便捷方法。"""
        new_log = cls(**kwargs)
        db_session.add(new_log)
        # 注意: 审计日志写入通常建议 flush 而非 commit，随业务事务一同落盘
        db_session.flush()
