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

# 必须导入插件模块以注册 Worker
#由于 __init__ 中通常不导入 worker 以避免循环依赖，这里需要显式导入 worker 模块
import devops_collector.plugins.gitlab.worker
import devops_collector.plugins.sonarqube.worker
import devops_collector.plugins.zentao.worker
try:
    import devops_collector.plugins.jenkins.worker
except ImportError: pass
try:
    import devops_collector.plugins.jira.worker
except ImportError: pass
try:
    import devops_collector.plugins.nexus.worker
except ImportError: pass
try:
    import devops_collector.plugins.jfrog.worker
except ImportError: pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CompensationSync')

# 实体处理映射 (Entity Handler Mapping)
# 定义每个 (source, entity_type) 对应的 Worker 处理方法
HANDLER_MAPPING = {
    'gitlab': {
        'merge_request': '_transform_mrs_batch',   # 批量接口 (List)
        'issue': '_transform_issues_batch',        # 批量接口 (List)
        'pipeline': '_transform_pipelines_batch',  # 批量接口 (List)
        'deployment': '_transform_deployments_batch' # 批量接口 (List)
    },
    'sonarqube': {
        'measure': '_transform_measures_snapshot', # 单条接口 (Dict)
        'issue': '_transform_issue'                # 单条接口 (Dict)
    },
    'zentao': {
        'issue_feature': '_transform_issue',       # 单条 (需特殊处理参数)
        'issue_bug': '_transform_issue',           # 单条
        'build': '_transform_build',               # 单条
        'release': '_transform_release'            # 单条
    }
}

class MockClient:
    """Mock Client 用于 Worker 实例化，防止触发网络请求。"""
    def __init__(self, *args, **kwargs):
        pass

def reprocess_by_source(source_name: str, entity_type: str = None):
    """根据来源重新处理 Staging 数据。

    Args:
        source_name: 数据源名称 (如 'gitlab', 'sonarqube')。
        entity_type: 实体类型 (如 'merge_request')，可选。
    """
    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 验证 Worker 是否存在
        worker_cls: Type[BaseWorker] = PluginRegistry.get_worker(source_name)
        if not worker_cls:
            raise ValueError(f"No worker found for source: {source_name}")

        # 实例化 Worker (传入 MockClient)
        worker = worker_cls(session, client=MockClient())
        # 对于 GitLab，可能需要 project 上下文，这里我们尝试让 Worker 自动处理
        # 或者在 iterate 时动态 fetch project。
        # 注意：大部分 Transform 方法接收 `project` 实体作为第一个参数。
        # 因此，我们需要先从 payload 或 external_id 中反查出 project_id，
        # 或者在 Staging 表中建立 project_id 索引（当前 Staging 表没有 project_id 字段）。
        
        # 策略：
        # 对于 GitLab/Sonar 等依赖 Project 上下文的 Worker，我们需要先从数据库获取 Project。
        # 既然是重放，说明 Project 已经存在于 DB 中。
        # 我们需要解析 Staging 记录关联的 Project。

        # 2. 查询 Staging 数据
        query = session.query(RawDataStaging).filter(RawDataStaging.source == source_name)
        if entity_type:
            query = query.filter(RawDataStaging.entity_type == entity_type)
        
        # 使用 yield per 避免内存溢出
        if hasattr(query, 'execution_options'):
             query = query.execution_options(stream_results=True)

        batch_buffer: Dict[str, List[dict]] = {} # type: grouping_key -> list of payloads
        buffer_size = 50 # 批处理大小

        processed_count = 0
        
        # 获取该源下的所有处理器配置
        source_handlers = HANDLER_MAPPING.get(source_name, {})

        for rec in query.yield_per(100):
            method_name = source_handlers.get(rec.entity_type)
            if not method_name:
                logger.debug(f"No handler for {rec.entity_type}, skipping.")
                continue

            handler = getattr(worker, method_name, None)
            if not handler:
                logger.warning(f"Handler method {method_name} not found in {worker_cls.__name__}")
                continue

            # 上下文恢复 (Context Recovery)
            # 大多数 transform 方法需要 Project 对象。
            # 我们需要从 rec.payload 中提取 project_id (GitLab) 或 project_key (Sonar)。
            context_obj = _resolve_context(session, source_name, rec.payload)
            if not context_obj:
                logger.warning(f"Could not resolve context for record {rec.id}")
                continue

            # 执行分发
            try:
                if source_name == 'gitlab':
                    # GitLab 大多支持批量，我们按 Project 分组批量处理
                    key = f"{rec.entity_type}:{context_obj.id}"
                    if key not in batch_buffer:
                        batch_buffer[key] = []
                    batch_buffer[key].append(rec.payload)

                    if len(batch_buffer[key]) >= buffer_size:
                        handler(context_obj, batch_buffer[key])
                        batch_buffer[key] = []
                        
                elif source_name == 'sonarqube':
                    # Sonar 方法通常接收单条数据，且参数不一致，需个别适配
                    # Measure: (project, measures_data, gate_status, ...)
                    # Issue: (project, issue_data)
                    if rec.entity_type == 'measure':
                        # Measure 只存了 payload (measures_data)，无法恢复 gate_status/dist
                        # 这是一个限制。目前脚本只能恢复核心 measures。
                        handler(context_obj, rec.payload)
                    else:
                        handler(context_obj, rec.payload)

                elif source_name == 'zentao':
                    # Zentao 参数复杂，如 _transform_build(product_id, execution_id, data)
                    # 需从 payload 提取 IDs
                    if rec.entity_type == 'build':
                        exec_id = rec.payload.get('execution')
                        handler(context_obj.id, exec_id, rec.payload)
                    elif rec.entity_type == 'release':
                        handler(context_obj.id, rec.payload)
                    elif rec.entity_type.startswith('issue_'):
                         # entity_type='issue_bug' -> issue_type='bug'
                         issue_type = rec.entity_type.split('_')[1]
                         handler(context_obj.id, rec.payload, issue_type)

            except Exception as e:
                logger.error(f"Error processing record {rec.id}: {e}")
                continue
            
            processed_count += 1
            if processed_count % 100 == 0:
                session.commit()
                logger.info(f"Reprocessed {processed_count} records...")

        # 处理剩余的 buffer (GitLab)
        for key, payloads in batch_buffer.items():
            if payloads:
                # key format: entity_type:project_id
                entity_type, pid = key.split(':')
                method_name = source_handlers.get(entity_type)
                handler = getattr(worker, method_name)
                
                # 重新获取 Project 对象 (因为 session 可能已变化或需要 detached 处理)
                from devops_collector.plugins.gitlab.models import Project
                proj = session.query(Project).get(int(pid))
                if proj:
                    handler(proj, payloads)

        session.commit()
        logger.info(f"Completed! Total reprocessed: {processed_count}")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        session.close()

def _resolve_context(session, source, payload):
    """根据 Payload 恢复上下文对象 (Project/Product)。"""
    if source == 'gitlab':
        from devops_collector.plugins.gitlab.models import Project
        pid = payload.get('project_id')
        if not pid:
             # 有些 payload 如 pipeline 只有 project_id，有些如 MR 也有
             # 如果 payload 自身没有 project_id (不常见)，则无法恢复
             return None
        return session.query(Project).get(pid)
        
    elif source == 'sonarqube':
        from devops_collector.plugins.sonarqube.models import SonarProject
        # Staging 记录的 payload 此处是 API 响应
        # 对于 sonarqube issue, payload 只有 key/project 等
        # 需要找到 project key。
        # payload['project'] 可能是 key
        pkey = payload.get('project') # for issue
        # for measure, we might not have project key in payload structure immediately?
        # Measure payload usually is a dict of metrics. It doesn't contain project key inside metrics list usually.
        # 但是！我们在 save_to_staging 时，external_id = f"{project.key}_current"
        # 我们可以尝试从 external_id 反解，或者必须依赖 payload。
        # 目前 Measure payload 看起来只是 metric data，没有 key。
        # 这是一个设计缺陷。应该在 Payload 包装一层 Metadata。
        # 临时方案：暂不支持 Measure 重放，除非我们在 save 时把 Project Key 塞进去。
        return session.query(SonarProject).filter_by(key=pkey).first() if pkey else None

    elif source == 'zentao':
        from devops_collector.plugins.zentao.models import ZenTaoProduct
        # ZenTao payload usually has 'product' field ID
        pid = payload.get('product')
        if pid:
            return session.query(ZenTaoProduct).get(pid)
    
    return None

if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else 'gitlab'
    etype = sys.argv[2] if len(sys.argv) > 2 else None
    
    reprocess_by_source(source, etype)
