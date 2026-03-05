"""Nexus 数据采集 Worker"""

import logging
import re

from devops_collector.core.base_worker import BaseWorker

# from .client import NexusClient
from devops_collector.models.base_models import Product

from .models import NexusAsset, NexusComponent


logger = logging.getLogger(__name__)


class NexusWorker(BaseWorker):
    """Nexus 数据采集 Worker。"""

    SCHEMA_VERSION = "1.0"

    def process_task(self, task: dict) -> None:
        """处理 Nexus 同步任务。
        task 结构示例: {'repository': 'maven-releases', 'job_type': 'full'}
        """
        repository = task.get("repository")
        if not repository:
            raise ValueError("Nexus task missing 'repository'")
        logger.info(f"Syncing Nexus repository: {repository}")

        # 预加载产品缓存
        self._init_product_cache()

        try:
            count = self._sync_components(repository)
            self.log_success(f"Nexus repository {repository} synced: {count} components")
        except Exception as e:
            self.log_failure(f"Failed to sync Nexus repository {repository}", e)
            raise

    def _init_product_cache(self):
        """初始化产品代码缓存及匹配模式列表。"""
        # 查询产品 ID 和匹配模式
        products = (
            self.session.query(Product.product_id, Product.matching_patterns).filter(Product.is_current == True).all()
        )

        self._product_map = {p.product_id.lower(): p.product_id for p in products}

        # 编译所有产品的匹配正则
        self._pattern_rules = []
        for p in products:
            patterns = p.matching_patterns
            if not patterns:
                continue
            if isinstance(patterns, str):
                patterns = [patterns]

            for pat in patterns:
                try:
                    # 智能判断是正则还是简单通配符
                    if pat.startswith("^") or pat.endswith("$") or "\\" in pat:
                        regex_str = pat
                    else:
                        # 简单模式：将 . 替换为 \.，将 * 替换为 .*
                        p_norm = pat.replace('.', r'\.').replace('*', '.*')
                        regex_str = f"^{p_norm}$"

                    self._pattern_rules.append({"re": re.compile(regex_str, re.I), "pid": p.product_id})
                except Exception as e:
                    logger.warning(f"Invalid matching pattern '{pat}' for product {p.product_id}: {e}")

        logger.info(f"Loaded {len(self._product_map)} products and {len(self._pattern_rules)} patterns.")

    def _resolve_product_id(self, group: str | None, name: str) -> str | None:
        """根据 Group 或 Name 智能解析所属 Product ID (优先匹配显式模式)。"""
        target_str = f"{group or ''}:{name}"

        # 1. 优先使用显式定义的 matching_patterns (正则匹配)
        for rule in self._pattern_rules:
            if rule["re"].match(group or "") or rule["re"].match(name) or rule["re"].match(target_str):
                return rule["pid"]

        # 2. 降级策略: 尝试通过 group 拆分匹配 (Maven 风格)
        if group:
            parts = group.lower().split(".")
            for part in reversed(parts):
                if part in self._product_map:
                    return self._product_map[part]

        # 3. 降级策略: 尝试通过 name 精确匹配
        name_lower = name.lower()
        if name_lower in self._product_map:
            return self._product_map[name_lower]

        return None

    def _sync_components(self, repository: str) -> int:
        """拉取并保存组件及其资产。"""
        generator = self.client.list_components(repository)
        count = 0
        batch = []
        batch_size = 100
        for item in generator:
            batch.append(item)
            if len(batch) >= batch_size:
                self._save_batch(batch)
                count += len(batch)
                batch = []
        if batch:
            self._save_batch(batch)
            count += len(batch)
        return count

    def _save_batch(self, batch: list[dict]) -> None:
        """批量保存到数据库，并执行身份/产品识别。"""
        for data in batch:
            comp_id = data["id"]
            comp = self.session.query(NexusComponent).filter_by(id=comp_id).first()
            if not comp:
                comp = NexusComponent(id=comp_id)
                self.session.add(comp)

            self.save_to_staging(
                source="nexus",
                entity_type="component",
                external_id=comp_id,
                payload=data,
                schema_version=self.SCHEMA_VERSION,
            )

            comp.repository = data["repository"]
            comp.format = data["format"]
            comp.group = data.get("group")
            comp.name = data["name"]
            comp.version = data.get("version")

            # 深度集成：自动产品对齐
            resolved_pid = self._resolve_product_id(comp.group, comp.name)
            if resolved_pid:
                comp.product_id = resolved_pid

            comp.raw_data = data
            self._sync_assets(comp, data.get("assets", []))
        self.session.commit()

    def _sync_assets(self, component: NexusComponent, assets_data: list[dict]) -> None:
        """同步组件关联的资产。"""
        existing_ids = {a.id for a in component.assets}
        for asset_data in assets_data:
            a_id = asset_data["id"]
            if a_id in existing_ids:
                continue
            self.save_to_staging(
                source="nexus",
                entity_type="asset",
                external_id=a_id,
                payload=asset_data,
                schema_version=self.SCHEMA_VERSION,
            )
            asset = NexusAsset(
                id=a_id,
                component_id=component.id,
                path=asset_data["path"],
                download_url=asset_data.get("downloadUrl"),
                size_bytes=asset_data.get("fileSize"),
                raw_data=asset_data,
            )
            checksums = asset_data.get("checksum", {})
            asset.checksum_sha1 = checksums.get("sha1")
            asset.checksum_sha256 = checksums.get("sha256")
            asset.checksum_md5 = checksums.get("md5")
            self.session.add(asset)
