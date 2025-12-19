"""数据生命周期管理器
- 自动清理超过保留期限的原始 Staging 数据。
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from devops_collector.config import Config
from devops_collector.models.base_models import RawDataStaging

logger = logging.getLogger(__name__)

class RetentionManager:
    """管理数据的保留和清理策略。"""

    def __init__(self, session=None):
        self._session = session
        self._external_session = session is not None

    def _get_session(self):
        if self._session:
            return self._session
        engine = create_engine(Config.DB_URI)
        Session = sessionmaker(bind=engine)
        self._session = Session()
        return self._session

    def cleanup_raw_data(self) -> int:
        """清理过期的原始采集数据。
        
        根据 Config.RAW_DATA_RETENTION_DAYS 执行清理。
        
        Returns:
            int: 被删除的记录总数。
        """
        retention_days = Config.RAW_DATA_RETENTION_DAYS
        if retention_days <= 0:
            logger.info("Retention days is set to 0 or less, skipping cleanup.")
            return 0
            
        threshold_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        session = self._get_session()
        
        try:
            # 执行删除操作
            stmt = delete(RawDataStaging).where(RawDataStaging.collected_at < threshold_date)
            result = session.execute(stmt)
            deleted_count = result.rowcount
            session.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} stale raw data records older than {threshold_date}")
            else:
                logger.info("No stale raw data records found to clean up.")
                
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup stale raw data: {e}")
            session.rollback()
            raise
        finally:
            if not self._external_session:
                session.close()
                self._session = None

if __name__ == "__main__":
    # 支持脚本直接运行
    logging.basicConfig(level=logging.INFO)
    manager = RetentionManager()
    manager.cleanup_raw_data()
