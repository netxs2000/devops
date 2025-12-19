"""JFrog Artifactory 数据采集 Worker"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from devops_collector.core.identity_manager import IdentityManager
from .client import JFrogClient
from .models import JFrogArtifact, JFrogScan, JFrogVulnerabilityDetail

logger = logging.getLogger(__name__)

class JFrogWorker(BaseWorker):
    """JFrog Artifactory 数据采集 Worker。"""
    SCHEMA_VERSION = "1.0"
    
    def process_task(self, task: dict) -> None:
        """处理 JFrog 同步任务。
        task 结构示例: {'repo': 'docker-local', 'job_type': 'full'}
        """
        repo = task.get('repo')
        if not repo:
            raise ValueError("JFrog task missing 'repo'")
            
        logger.info(f"Syncing JFrog repository: {repo}")
        
        try:
            count = self._sync_artifacts(repo)
            self.log_success(f"JFrog repository {repo} synced: {count} artifacts")
        except Exception as e:
            self.log_failure(f"Failed to sync JFrog repository {repo}", e)
            raise

    def _sync_artifacts(self, repo: str) -> int:
        """从 JFrog 同步制品信息。"""
        generator = self.client.get_artifacts(repo)
        count = 0
        
        for item in generator:
            artifact = self._save_artifact(repo, item)
            
            # 同步统计信息
            stats = self.client.get_artifact_stats(repo, item['path'] + "/" + item['name'])
            artifact.download_count = stats.get('downloadCount', 0)
            if stats.get('lastDownloaded'):
                 artifact.last_downloaded_at = datetime.fromtimestamp(stats['lastDownloaded']/1000, tz=timezone.utc)
            
            # 同步安全扫描信息 (可选)
            scan_data = self.client.get_xray_summary(repo, item['path'] + "/" + item['name'])
            if scan_data:
                self._sync_xray_scan(artifact, scan_data)
                
            count += 1
            
        self.session.commit()
        return count

    def _save_artifact(self, repo: str, data: dict) -> JFrogArtifact:
        """保存或更新制品记录。"""
        # AQL 返回的数据结构
        path = data['path']
        name = data['name']
        
        artifact = self.session.query(JFrogArtifact).filter_by(repo=repo, path=path, name=name).first()
        if not artifact:
            artifact = JFrogArtifact(repo=repo, path=path, name=name)
            self.session.add(artifact)
            
        # 原始制品数据落盘
        self.save_to_staging(
            source='jfrog',
            entity_type='artifact',
            external_id=f"{repo}:{path}/{name}",
            payload=data,
            schema_version=self.SCHEMA_VERSION
        )
            
        artifact.size_bytes = data.get('size')
        artifact.sha256 = data.get('sha256')
        artifact.created_at = datetime.fromisoformat(data['created'].replace('Z', '+00:00'))
        artifact.updated_at = datetime.fromisoformat(data['modified'].replace('Z', '+00:00'))
        
        # 处理创建人
        created_by = data.get('created_by')
        if created_by:
            u = IdentityManager.get_or_create_user(self.session, 'jfrog', created_by)
            artifact.created_by_id = u.id
            artifact.created_by_name = u.name
            
        # 提取属性 (Properties)
        props = {}
        for p in data.get('properties', []):
            props[p['key']] = p.get('value')
        artifact.properties = props
        
        # 尝试从中提取构建信息
        artifact.build_name = props.get('build.name')
        artifact.build_number = props.get('build.number')
        
        artifact.raw_data = data
        self.session.flush()
        return artifact

    def _sync_xray_scan(self, artifact: JFrogArtifact, scan_data: dict) -> None:
        """处理 Xray 扫描结果。"""
        scan = self.session.query(JFrogScan).filter_by(artifact_id=artifact.id).first()
        if not scan:
            scan = JFrogScan(artifact_id=artifact.id)
            self.session.add(scan)
            
        # 原始扫描 summary 数据落盘
        self.save_to_staging(
            source='jfrog',
            entity_type='xray_scan',
            external_id=f"artifact_{artifact.id}",
            payload=scan_data,
            schema_version=self.SCHEMA_VERSION
        )
            
        summary = scan_data.get('summary', {})
        scan.critical_count = summary.get('critical', 0)
        scan.high_count = summary.get('high', 0)
        scan.medium_count = summary.get('medium', 0)
        scan.low_count = summary.get('low', 0)
        
        # 如果有具体的漏洞列表
        issues = scan_data.get('issues', [])
        for issue in issues:
            cve_id = issue.get('cve', 'N/A')
            vuln = self.session.query(JFrogVulnerabilityDetail).filter_by(
                artifact_id=artifact.id, cve_id=cve_id).first()
            if not vuln:
                vuln = JFrogVulnerabilityDetail(artifact_id=artifact.id, cve_id=cve_id)
                self.session.add(vuln)
            
            vuln.severity = issue.get('severity')
            vuln.component = issue.get('component')
            vuln.description = issue.get('description')
            
        scan.raw_data = scan_data
        self.session.flush()

# 注册 Worker
PluginRegistry.register_worker('jfrog', JFrogWorker)
