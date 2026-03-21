"""Worker 抽象基类模块

提供所有数据采集 Worker 的通用功能：
- 数据库会话管理
- 客户端实例管理
- 日志记录及状态持久化抽象
"""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """所有数据采集 Worker 的抽象基类。"""

    SCHEMA_VERSION = "1.0"

    def __init__(self, session: Session, client: Any, correlation_id: str = "unknown-cid"):
        """初始化 Worker。

        Args:
            session: SQLAlchemy 数据库会话
            client: API 客户端实例
            correlation_id: 追踪 ID (用于日志对齐)
        """
        self.session = session
        self.client = client
        self.correlation_id = correlation_id
        # 使用特定业务域前缀及 CID 创建适配器
        self.logger = logging.LoggerAdapter(logger, {"correlation_id": self.correlation_id})

    @abstractmethod
    def process_task(self, task: dict) -> Any:
        """子类需实现此核心同步逻辑。"""
        pass

    def run_sync(self, task: dict, model_cls: Any | None = None, pk_field: str = "id", pk_value: Any | None = None) -> Any:
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
        source = task.get("source", "unknown")
        self.log_progress(f"Starting {source} sync task", 0, 1)
        try:
            if model_cls and pk_value:
                instance = self.session.query(model_cls).filter_by(**{pk_field: pk_value}).first()
                if instance and hasattr(instance, "sync_status"):
                    instance.sync_status = "SYNCING"
                    self.session.commit()
            result = self.process_task(task)
            if model_cls and pk_value:
                instance = self.session.query(model_cls).filter_by(**{pk_field: pk_value}).first()
                if instance:
                    if hasattr(instance, "sync_status"):
                        instance.sync_status = "SUCCESS"
                    if hasattr(instance, "last_synced_at"):
                        instance.last_synced_at = datetime.now(UTC)
            self.session.commit()
            self.log_success(f"{source} sync completed")
            return result
        except Exception as e:
            self.session.rollback()
            self.log_failure(f"{source} sync failed", e)
            if model_cls and pk_value:
                try:
                    instance = self.session.query(model_cls).filter_by(**{pk_field: pk_value}).first()
                    if instance and hasattr(instance, "sync_status"):
                        instance.sync_status = "FAILED"
                        self.session.commit()
                except Exception:
                    pass
            raise e

    def log_success(self, message: str) -> None:
        """记录成功日志。"""
        self.logger.info(f"[SUCCESS] {message}")

    def log_failure(self, message: str, error: Exception | None = None) -> None:
        """记录失败日志并记录异常信息。"""
        if error:
            self.logger.error(f"[FAILURE] {message}: {error}")
        else:
            self.logger.error(f"[FAILURE] {message}")

    def log_progress(self, message: str, current: int, total: int) -> None:
        """记录任务进度。"""
        percent = current / total * 100 if total > 0 else 0
        self.logger.info(f"[PROGRESS] {message}: {current}/{total} ({percent:.1f}%)")

    def save_to_staging(self, source: str, entity_type: str, external_id: str, payload: dict, schema_version: str = "1.0") -> None:
        """将原始数据保存到 Staging 层，消除重复的 Upsert 逻辑。"""
        from sqlalchemy.dialects.postgresql import insert

        from devops_collector.models.base_models import RawDataStaging

        data = {
            "source": source,
            "entity_type": entity_type,
            "external_id": str(external_id),
            "payload": payload,
            "schema_version": schema_version,
            "correlation_id": self.correlation_id,
            "collected_at": datetime.now(UTC),
        }
        try:
            # 使用嵌套事务 (Savepoint) 尝试 Upsert，防止事务中止
            with self.session.begin_nested():
                stmt = insert(RawDataStaging).values(**data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["source", "entity_type", "external_id"],
                    set_={
                        "payload": stmt.excluded.payload,
                        "schema_version": stmt.excluded.schema_version,
                        "collected_at": stmt.excluded.collected_at,
                    },
                )
                self.session.execute(stmt)
        except Exception as e:
            # 如果核心 Upsert 语法失败（例如某些不支持 upsert 的 PG 版本），则尝试回退到手动查询更新
            self.logger.debug(f"Upsert failed, falling back to manual merge for {entity_type}:{external_id}: {e}")
            existing = self.session.query(RawDataStaging).filter_by(source=source, entity_type=entity_type, external_id=str(external_id)).first()
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                self.session.add(RawDataStaging(**data))
                try:
                    self.session.flush()
                except Exception:
                    self.session.rollback()  # 真的没法救了再 rollback

    def bulk_save_to_staging(self, source: str, entity_type: str, items: list[dict], id_field: str = "id", schema_version: str = "1.0") -> None:
        """高性能批量存放原始数据到 Staging 层。

        针对大数据宽表（如 GitLab Commits），利用 PostgreSQL 原生的 COPY FROM
        将数据快速导入到临时表，再经 ON CONFLICT DO UPDATE 合并，
        性能比批量 ORM 插入提升 5-10 倍。
        """
        import csv
        import io
        import json

        # 判断数据库方言。非 PostgreSQL 环境（如集成测试中的 SQLite）不支持 COPY FROM 和特定的 JSONB 转换。
        # 此时降级到逐条 save_to_staging，虽然性能略低但能保证集成测试通过。
        dialect = self.session.bind.dialect.name
        if dialect != "postgresql":
            self.logger.debug(f"Non-PostgreSQL dialect ({dialect}) detected, using graceful fallback for bulk_save_to_staging")
            for item in items:
                ext_id = item.get(id_field, "")
                self.save_to_staging(source, entity_type, ext_id, item, schema_version)
            return

        # 获取底层 psycopg 的连接对象
        raw_conn = self.session.connection().connection
        if hasattr(raw_conn, "dbapi_connection"):
            raw_conn = raw_conn.dbapi_connection

        csv_file = io.StringIO()
        # 注意: 包含复杂的 JSON 数据，因此使用严格的引用策略
        writer = csv.writer(csv_file, quoting=csv.QUOTE_MINIMAL)

        for item in items:
            ext_id = str(item.get(id_field, ""))
            payload_str = json.dumps(item)
            writer.writerow([source, entity_type, ext_id, payload_str, schema_version, self.correlation_id])

        csv_file.seek(0)
        temp_table = f"tmp_stg_{source}_{entity_type}_{id(self)}"

        # 并不是所有 DBAPI cursor 都支持 context manager (如 SQLite)，因此在原始连接操作时建议显式关闭
        cursor = raw_conn.cursor()
        try:
            # 创建仅限于当前事务内的临时表
            cursor.execute(f"CREATE TEMP TABLE {temp_table} (LIKE stg_raw_data INCLUDING DEFAULTS) ON COMMIT DROP")

            # 使用原生的 copy_expert 进行高性能加载
            copy_sql = f"COPY {temp_table} (source, entity_type, external_id, payload, schema_version, correlation_id) FROM STDIN WITH CSV"
            cursor.copy_expert(copy_sql, csv_file)

            # 通过 Upsert 逻辑把临时表合并到主表
            upsert_sql = f"""
                INSERT INTO stg_raw_data (source, entity_type, external_id, payload, schema_version, correlation_id, collected_at)
                SELECT source, entity_type, external_id, cast(payload as jsonb), schema_version, correlation_id, CURRENT_TIMESTAMP
                FROM {temp_table}
                ON CONFLICT (source, entity_type, external_id)
                DO UPDATE SET
                    payload = EXCLUDED.payload,
                    schema_version = EXCLUDED.schema_version,
                    correlation_id = EXCLUDED.correlation_id,
                    collected_at = EXCLUDED.collected_at
            """
            cursor.execute(upsert_sql)

            # 删除临时表结束加载
            cursor.execute(f"DROP TABLE {temp_table}")
        finally:
            cursor.close()
