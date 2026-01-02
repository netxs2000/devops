"""数据清理脚本
用于手动或定时执行原始采集数据的清理任务。
"""
import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.core.retention_manager import RetentionManager
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CleanupScript')

def main():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    logger.info('Starting stale data cleanup...')
    try:
        manager = RetentionManager()
        deleted_count = manager.cleanup_raw_data()
        logger.info(f'Cleanup finished. Total records removed: {deleted_count}')
    except Exception as e:
        logger.error(f'Cleanup failed: {e}')
        sys.exit(1)
if __name__ == '__main__':
    main()