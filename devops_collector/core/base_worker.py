"""Worker 抽象基类模块

提供所有数据采集 Worker 的通用功能：
- 数据库会话管理
- 客户端实例管理
- 日志记录及状态持久化抽象
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Any, Callable
from sqlalchemy.orm import Session
logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    """所有数据采集 Worker 的抽象基类。"""
    SCHEMA_VERSION = '1.0'

    def __init__(self, session: Session, client: Any):
        """初始化 Worker。
        
        Args:
            session: SQLAlchemy 数据库会话
            client: API 客户端实例
        """
        self.session = session
        self.client = client

    @abstractmethod
    def process_task(self, task: dict) -> Any:
        """子类需实现此核心同步逻辑。"""
        pass

    def run_sync(self, task: dict, model_cls: Optional[Any]=None, pk_field: str='id', pk_value: Optional[Any]=None) -> Any:
        """通用同步包装器，处理事务、日志和异常。
        
        该方法封装了标准的“开始-处理-成功提交-失败回退”流程。
        
        Args:
            task: 任务字典
            model_cls: 关联的状态模型类(可选)
            pk_field: 查找实例的主键字段名
            pk_value: 主键值(若未提供则从task中尝试获取)
            
        Returns:
            process_task 的返回值
        """
        source = task.get('source', 'unknown')
        self.log_progress(f'Starting {source} sync task', 0, 1)
        try:
            if model_cls and pk_value:
                instance = self.session.query(model_cls).filter_by(**{pk_field: pk_value}).first()
                if instance and hasattr(instance, 'sync_status'):
                    instance.sync_status = 'SYNCING'
                    self.session.commit()
            result = self.process_task(task)
            if model_cls and pk_value:
                instance = self.session.query(model_cls).filter_by(**{pk_field: pk_value}).first()
                if instance:
                    if hasattr(instance, 'sync_status'):
                        instance.sync_status = 'SUCCESS'
                    if hasattr(instance, 'last_synced_at'):
                        instance.last_synced_at = datetime.now(timezone.utc)
            self.session.commit()
            self.log_success(f'{source} sync completed')
            return result
        except Exception as e:
            self.session.rollback()
            self.log_failure(f'{source} sync failed', e)
            if model_cls and pk_value:
                try:
                    instance = self.session.query(model_cls).filter_by(**{pk_field: pk_value}).first()
                    if instance and hasattr(instance, 'sync_status'):
                        instance.sync_status = 'FAILED'
                        self.session.commit()
                except:
                    pass
            raise e

    def log_success(self, message: str) -> None:
        '''"""TODO: Add description.

Args:
    self: TODO
    message: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        logger.info(f'[SUCCESS] {message}')

    def log_failure(self, message: str, error: Optional[Exception]=None) -> None:
        '''"""TODO: Add description.

Args:
    self: TODO
    message: TODO
    error: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        if error:
            logger.error(f'[FAILURE] {message}: {error}')
        else:
            logger.error(f'[FAILURE] {message}')

    def log_progress(self, message: str, current: int, total: int) -> None:
        '''"""TODO: Add description.

Args:
    self: TODO
    message: TODO
    current: TODO
    total: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        percent = current / total * 100 if total > 0 else 0
        logger.info(f'[PROGRESS] {message}: {current}/{total} ({percent:.1f}%)')

    def save_to_staging(self, source: str, entity_type: str, external_id: str, payload: dict, schema_version: str='1.0') -> None:
        """将原始数据保存到 Staging 层，消除重复的 Upsert 逻辑。"""
        from devops_collector.models.base_models import RawDataStaging
        from sqlalchemy.dialects.postgresql import insert
        data = {'source': source, 'entity_type': entity_type, 'external_id': str(external_id), 'payload': payload, 'schema_version': schema_version, 'collected_at': datetime.now(timezone.utc)}
        try:
            stmt = insert(RawDataStaging).values(**data)
            stmt = stmt.on_conflict_do_update(index_elements=['source', 'entity_type', 'external_id'], set_={'payload': data['payload'], 'schema_version': data['schema_version'], 'collected_at': data['collected_at']})
            self.session.execute(stmt)
        except Exception:
            existing = self.session.query(RawDataStaging).filter_by(source=source, entity_type=entity_type, external_id=str(external_id)).first()
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                self.session.add(RawDataStaging(**data))