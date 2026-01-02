"""数据补偿同步 (Reprocess) 脚本

作用：
1. 读取 raw_data_staging 表中的原始 JSON。
2. 调用对应插件的业务转换逻辑。
3. 在无需请求外部 API 的情况下，刷新业务表数据。
"""
import logging
from typing import List, Dict, Any, Type
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.config import Config
from devops_collector.models.base_models import RawDataStaging
from devops_collector.core.registry import PluginRegistry
from devops_collector.core.base_worker import BaseWorker
import devops_collector.plugins.gitlab.worker
import devops_collector.plugins.sonarqube.worker
import devops_collector.plugins.zentao.worker
try:
    import devops_collector.plugins.jenkins.worker
except ImportError:
    pass
try:
    import devops_collector.plugins.jira.worker
except ImportError:
    pass
try:
    import devops_collector.plugins.nexus.worker
except ImportError:
    pass
try:
    import devops_collector.plugins.jfrog.worker
except ImportError:
    pass
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CompensationSync')
HANDLER_MAPPING = {'gitlab': {'merge_request': '_transform_mrs_batch', 'issue': '_transform_issues_batch', 'pipeline': '_transform_pipelines_batch', 'deployment': '_transform_deployments_batch'}, 'sonarqube': {'measure': '_transform_measures_snapshot', 'issue': '_transform_issue'}, 'zentao': {'issue_feature': '_transform_issue', 'issue_bug': '_transform_issue', 'build': '_transform_build', 'release': '_transform_release'}}

class MockClient:
    """Mock Client 用于 Worker 实例化，防止触发网络请求。"""

    def __init__(self, *args, **kwargs):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        pass

def reprocess_by_source(source_name: str, entity_type: str=None):
    """根据来源重新处理 Staging 数据。

    Args:
        source_name: 数据源名称 (如 'gitlab', 'sonarqube')。
        entity_type: 实体类型 (如 'merge_request')，可选。
    """
    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        worker_cls: Type[BaseWorker] = PluginRegistry.get_worker(source_name)
        if not worker_cls:
            raise ValueError(f'No worker found for source: {source_name}')
        worker = worker_cls(session, client=MockClient())
        query = session.query(RawDataStaging).filter(RawDataStaging.source == source_name)
        if entity_type:
            query = query.filter(RawDataStaging.entity_type == entity_type)
        if hasattr(query, 'execution_options'):
            query = query.execution_options(stream_results=True)
        batch_buffer: Dict[str, List[dict]] = {}
        buffer_size = 50
        processed_count = 0
        source_handlers = HANDLER_MAPPING.get(source_name, {})
        for rec in query.yield_per(100):
            method_name = source_handlers.get(rec.entity_type)
            if not method_name:
                logger.debug(f'No handler for {rec.entity_type}, skipping.')
                continue
            handler = getattr(worker, method_name, None)
            if not handler:
                logger.warning(f'Handler method {method_name} not found in {worker_cls.__name__}')
                continue
            context_obj = _resolve_context(session, source_name, rec.payload)
            if not context_obj:
                logger.warning(f'Could not resolve context for record {rec.id}')
                continue
            try:
                if source_name == 'gitlab':
                    key = f'{rec.entity_type}:{context_obj.id}'
                    if key not in batch_buffer:
                        batch_buffer[key] = []
                    batch_buffer[key].append(rec.payload)
                    if len(batch_buffer[key]) >= buffer_size:
                        handler(context_obj, batch_buffer[key])
                        batch_buffer[key] = []
                elif source_name == 'sonarqube':
                    if rec.entity_type == 'measure':
                        handler(context_obj, rec.payload)
                    else:
                        handler(context_obj, rec.payload)
                elif source_name == 'zentao':
                    if rec.entity_type == 'build':
                        exec_id = rec.payload.get('execution')
                        handler(context_obj.id, exec_id, rec.payload)
                    elif rec.entity_type == 'release':
                        handler(context_obj.id, rec.payload)
                    elif rec.entity_type.startswith('issue_'):
                        issue_type = rec.entity_type.split('_')[1]
                        handler(context_obj.id, rec.payload, issue_type)
            except Exception as e:
                logger.error(f'Error processing record {rec.id}: {e}')
                continue
            processed_count += 1
            if processed_count % 100 == 0:
                session.commit()
                logger.info(f'Reprocessed {processed_count} records...')
        for key, payloads in batch_buffer.items():
            if payloads:
                entity_type, pid = key.split(':')
                method_name = source_handlers.get(entity_type)
                handler = getattr(worker, method_name)
                from devops_collector.plugins.gitlab.models import Project
                proj = session.query(Project).get(int(pid))
                if proj:
                    handler(proj, payloads)
        session.commit()
        logger.info(f'Completed! Total reprocessed: {processed_count}')
    except Exception as e:
        logger.error(f'Fatal error: {e}', exc_info=True)
    finally:
        session.close()

def _resolve_context(session, source, payload):
    """根据 Payload 恢复上下文对象 (Project/Product)。"""
    if source == 'gitlab':
        from devops_collector.plugins.gitlab.models import Project
        pid = payload.get('project_id')
        if not pid:
            return None
        return session.query(Project).get(pid)
    elif source == 'sonarqube':
        from devops_collector.plugins.sonarqube.models import SonarProject
        pkey = payload.get('project')
        return session.query(SonarProject).filter_by(key=pkey).first() if pkey else None
    elif source == 'zentao':
        from devops_collector.plugins.zentao.models import ZenTaoProduct
        pid = payload.get('product')
        if pid:
            return session.query(ZenTaoProduct).get(pid)
    return None
if __name__ == '__main__':
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else 'gitlab'
    etype = sys.argv[2] if len(sys.argv) > 2 else None
    reprocess_by_source(source, etype)