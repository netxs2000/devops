"""Nexus 数据采集 Worker"""
import logging
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from .client import NexusClient
from .models import NexusComponent, NexusAsset
logger = logging.getLogger(__name__)

class NexusWorker(BaseWorker):
    """Nexus 数据采集 Worker。"""
    SCHEMA_VERSION = '1.0'

    def process_task(self, task: dict) -> None:
        """处理 Nexus 同步任务。
        task 结构示例: {'repository': 'maven-releases', 'job_type': 'full'}
        """
        repository = task.get('repository')
        if not repository:
            raise ValueError("Nexus task missing 'repository'")
        logger.info(f'Syncing Nexus repository: {repository}')
        try:
            count = self._sync_components(repository)
            self.log_success(f'Nexus repository {repository} synced: {count} components')
        except Exception as e:
            self.log_failure(f'Failed to sync Nexus repository {repository}', e)
            raise

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

    def _save_batch(self, batch: List[dict]) -> None:
        """批量保存到数据库。"""
        for data in batch:
            comp_id = data['id']
            comp = self.session.query(NexusComponent).filter_by(id=comp_id).first()
            if not comp:
                comp = NexusComponent(id=comp_id)
                self.session.add(comp)
            self.save_to_staging(source='nexus', entity_type='component', external_id=comp_id, payload=data, schema_version=self.SCHEMA_VERSION)
            comp.repository = data['repository']
            comp.format = data['format']
            comp.group = data.get('group')
            comp.name = data['name']
            comp.version = data.get('version')
            comp.raw_data = data
            self._sync_assets(comp, data.get('assets', []))
        self.session.commit()

    def _sync_assets(self, component: NexusComponent, assets_data: List[dict]) -> None:
        """同步组件关联的资产。"""
        existing_ids = {a.id for a in component.assets}
        for asset_data in assets_data:
            a_id = asset_data['id']
            if a_id in existing_ids:
                continue
            self.save_to_staging(source='nexus', entity_type='asset', external_id=a_id, payload=asset_data, schema_version=self.SCHEMA_VERSION)
            asset = NexusAsset(id=a_id, component_id=component.id, path=asset_data['path'], download_url=asset_data.get('downloadUrl'), size_bytes=asset_data.get('fileSize'), raw_data=asset_data)
            checksums = asset_data.get('checksum', {})
            asset.checksum_sha1 = checksums.get('sha1')
            asset.checksum_sha256 = checksums.get('sha256')
            asset.checksum_md5 = checksums.get('md5')
            self.session.add(asset)
PluginRegistry.register_worker('nexus', NexusWorker)