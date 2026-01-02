"""Worker 抽象基类模块

提供所有数据采集 Worker 的通用功能：
- 数据库会话管理
- 客户端实例管理
- 日志记录

Typical usage:
    class MyWorker(BaseWorker):
        def process_task(self, task: dict) -> None:
            data = self.client.get_data()
            self.session.add(Model(**data))
            self.session.commit()
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    """所有数据采集 Worker 的抽象基类。
    
    提供统一的任务处理接口和通用工具方法。
    
    Attributes:
        session: SQLAlchemy 数据库会话
        client: 数据源客户端实例
    
    Example:
        class GitLabWorker(BaseWorker):
            def process_task(self, task: dict) -> None:
                project_id = task['project_id']
                data = self.client.get_project(project_id)
                self.session.add(Project(**data))
                self.session.commit()
    """
    SCHEMA_VERSION = '1.0'

    def __init__(self, session: Session, client):
        """初始化 Worker。
        
        Args:
            session: SQLAlchemy 数据库会话
            client: 实现了 BaseClient 协议的客户端
        """
        self.session = session
        self.client = client

    @abstractmethod
    def process_task(self, task: dict) -> None:
        """处理同步任务。
        
        子类必须实现此方法来处理具体的数据同步逻辑。
        
        Args:
            task: 任务字典，包含任务类型和参数
                - source: 数据源类型 (如 'gitlab', 'sonarqube')
                - job_type: 任务类型 (如 'full', 'incremental')
                - 其他特定于数据源的参数
        
        Raises:
            Exception: 同步失败时抛出异常
        """
        pass

    def log_success(self, message: str) -> None:
        """记录成功日志。
        
        Args:
            message: 日志消息
        """
        logger.info(f'[SUCCESS] {message}')

    def log_failure(self, message: str, error: Optional[Exception]=None) -> None:
        """记录失败日志。
        
        Args:
            message: 日志消息
            error: 异常对象 (可选)
        """
        if error:
            logger.error(f'[FAILURE] {message}: {error}')
        else:
            logger.error(f'[FAILURE] {message}')

    def log_progress(self, message: str, current: int, total: int) -> None:
        """记录进度日志。
        
        Args:
            message: 进度描述
            current: 当前进度
            total: 总数
        """
        percent = current / total * 100 if total > 0 else 0
        logger.info(f'[PROGRESS] {message}: {current}/{total} ({percent:.1f}%)')

    def save_to_staging(self, source: str, entity_type: str, external_id: str, payload: dict, schema_version: str='1.0') -> None:
        """将原始数据保存到 Staging 层。
        
        采用 Upsert 逻辑：如果存在则更新内容，不存在则创建。
        
        Args:
            source: 数据源 (如 'gitlab')
            entity_type: 实体类型 (如 'merge_request')
            external_id: 外部唯一 ID
            payload: JSON 载荷
            schema_version: Schema 版本 (如 '1.0', 'v2')
        """
        from devops_collector.models.base_models import RawDataStaging
        from sqlalchemy.dialects.postgresql import insert
        try:
            stmt = insert(RawDataStaging).values(source=source, entity_type=entity_type, external_id=str(external_id), payload=payload, schema_version=schema_version, collected_at=datetime.now(timezone.utc)).on_conflict_do_update(index_elements=['source', 'entity_type', 'external_id'], set_={'payload': payload, 'schema_version': schema_version, 'collected_at': datetime.now(timezone.utc)})
            self.session.execute(stmt)
        except Exception as e:
            self.log_failure(f'Failed to save {entity_type} {external_id} to staging', e)
            existing = self.session.query(RawDataStaging).filter_by(source=source, entity_type=entity_type, external_id=str(external_id)).first()
            if existing:
                existing.payload = payload
                existing.schema_version = schema_version
                existing.collected_at = datetime.now(timezone.utc)
            else:
                new_raw = RawDataStaging(source=source, entity_type=entity_type, external_id=str(external_id), payload=payload, schema_version=schema_version)
                self.session.add(new_raw)