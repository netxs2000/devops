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
        logger.info(f"[SUCCESS] {message}")
    
    def log_failure(self, message: str, error: Optional[Exception] = None) -> None:
        """记录失败日志。
        
        Args:
            message: 日志消息
            error: 异常对象 (可选)
        """
        if error:
            logger.error(f"[FAILURE] {message}: {error}")
        else:
            logger.error(f"[FAILURE] {message}")
    
    def log_progress(self, message: str, current: int, total: int) -> None:
        """记录进度日志。
        
        Args:
            message: 进度描述
            current: 当前进度
            total: 总数
        """
        percent = (current / total * 100) if total > 0 else 0
        logger.info(f"[PROGRESS] {message}: {current}/{total} ({percent:.1f}%)")
