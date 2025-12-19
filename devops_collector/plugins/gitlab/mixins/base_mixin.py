"""GitLab Worker Base Mixin.

提供通用的批处理辅助方法。
"""
import logging
from typing import List, Callable, Any

logger = logging.getLogger(__name__)


class BaseMixin:
    """提供通用的生成器处理逻辑。
    
    必须混入到拥有 session 属性的类中使用。
    """
    
    def _process_generator(self, generator, processor_func: Callable[[List[Any]], None], batch_size: int = 500) -> int:
        """通用的生成器批处理助手。
        
        Args:
            generator: GitLab API 返回的生成器对象。
            processor_func: 用于处理单批次数据的回调函数。
            batch_size (int): 每批次处理的数据量，默认 500。
            
        Returns:
            int: 总处理记录数。
        """
        count = 0
        batch = []
        for item in generator:
            batch.append(item)
            if len(batch) >= batch_size:
                try:
                    processor_func(batch)
                    self.session.commit()
                    count += len(batch)
                except Exception as e:
                    self.session.rollback()
                    logger.error(f"Batch processing failed: {e}")
                    raise
                finally:
                    batch = []
        
        if batch:
            try:
                processor_func(batch)
                self.session.commit()
                count += len(batch)
            except Exception as e:
                self.session.rollback()
                logger.error(f"Final batch processing failed: {e}")
                raise
                
        return count
