"""GitLab Worker Asset Mixin.

提供次要资产（Tag, Branch, Milestone, Package, Wiki, Dependency 等）的同步逻辑。
"""
import logging
from datetime import datetime, timezone
from typing import List

from devops_collector.core.utils import parse_iso8601
from devops_collector.plugins.gitlab.models import (
    Project, Tag, Branch, Milestone, GitLabPackage, GitLabPackageFile, 
    GitLabWikiLog, GitLabDependency
)

logger = logging.getLogger(__name__)


class AssetMixin:
    """提供 Tag, Branch, Milestone 等次要资产的同步逻辑。"""

    def _sync_tags(self, project: Project) -> int:
        """同步 Git 标签。"""
        count = self._process_generator(
            self.client.get_project_tags(project.id),
            lambda batch: self._save_tags_batch(project, batch)
        )
        project.tags_count = count
        return count

    def _save_tags_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存标签。"""
        names = [item['name'] for item in batch]
        existing = self.session.query(Tag).filter(
            Tag.project_id == project.id,
            Tag.name.in_(names)
        ).all()
        existing_map = {t.name: t for t in existing}
        
        for data in batch:
            tag = existing_map.get(data['name'])
            if not tag:
                tag = Tag(project_id=project.id, name=data['name'])
                self.session.add(tag)
            
            tag.message = data.get('message')
            tag.commit_sha = data.get('commit', {}).get('id')

    def _sync_branches(self, project: Project) -> int:
        """同步分支元数据。"""
        return self._process_generator(
            self.client.get_project_branches(project.id),
            lambda batch: self._save_branches_batch(project, batch)
        )

    def _save_branches_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存分支。"""
        names = [item['name'] for item in batch]
        existing = self.session.query(Branch).filter(
            Branch.project_id == project.id,
            Branch.name.in_(names)
        ).all()
        existing_map = {b.name: b for b in existing}
        
        for data in batch:
            branch = existing_map.get(data['name'])
            if not branch:
                branch = Branch(project_id=project.id, name=data['name'])
                self.session.add(branch)
            
            commit_info = data.get('commit', {})
            branch.last_commit_sha = commit_info.get('id')
            branch.last_committer_name = commit_info.get('committer_name')
            branch.is_merged = data.get('merged', False)
            branch.is_protected = data.get('protected', False)
            branch.is_default = data.get('default', False)
            
            if commit_info.get('committed_date'):
                branch.last_commit_date = parse_iso8601(commit_info['committed_date'])

    def _sync_milestones(self, project: Project) -> int:
        """同步里程碑 (支持流式处理)。"""
        return self._process_generator(
            self.client.get_project_milestones(project.id),
            lambda batch: self._save_milestones_batch(project, batch)
        )

    def _save_milestones_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存里程碑。"""
        ids = [item['id'] for item in batch]
        existing = self.session.query(Milestone).filter(Milestone.id.in_(ids)).all()
        existing_map = {m.id: m for m in existing}
        
        for data in batch:
            ms = existing_map.get(data['id'])
            if not ms:
                ms = Milestone(id=data['id'])
                self.session.add(ms)
            
            ms.project_id = project.id
            ms.iid = data.get('iid')
            ms.title = data.get('title')
            ms.description = data.get('description')
            ms.state = data.get('state')
            
            if data.get('due_date'):
                try:
                    ms.due_date = datetime.fromisoformat(data['due_date']).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            if data.get('start_date'):
                try:
                    ms.start_date = datetime.fromisoformat(data['start_date']).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
                    
            ms.created_at = parse_iso8601(data.get('created_at'))
            ms.updated_at = parse_iso8601(data.get('updated_at'))

    def _sync_packages(self, project: Project) -> int:
        """同步项目的制品包。"""
        return self._process_generator(
            self.client.get_packages(project.id),
            lambda batch: self._save_packages_batch(project, batch)
        )

    def _save_packages_batch(self, project: Project, batch: List[dict]) -> None:
        """保存包及其关联文件。"""
        ids = [item['id'] for item in batch]
        existing = self.session.query(GitLabPackage).filter(GitLabPackage.id.in_(ids)).all()
        existing_map = {p.id: p for p in existing}
        
        for data in batch:
            pkg = existing_map.get(data['id'])
            if not pkg:
                pkg = GitLabPackage(id=data['id'])
                self.session.add(pkg)
            
            pkg.project_id = project.id
            pkg.name = data['name']
            pkg.version = data.get('version')
            pkg.package_type = data.get('package_type')
            pkg.status = data.get('status')
            pkg.created_at = parse_iso8601(data.get('created_at'))
            pkg.web_url = data.get('_links', {}).get('web_path')
            pkg.raw_data = data
            
            # 同步包文件
            try:
                files_data = self.client.get_package_files(project.id, pkg.id)
                self._sync_package_files(pkg, files_data)
            except Exception as e:
                logger.warning(f"Failed to sync files for package {pkg.id}: {e}")

    def _sync_package_files(self, package: GitLabPackage, files_data: List[dict]) -> None:
        """同步特定包下的文件。"""
        ids = [f['id'] for f in files_data]
        existing = {f.id for f in package.files}
        
        for f_data in files_data:
            if f_data['id'] in existing:
                continue
            
            f_obj = GitLabPackageFile(
                id=f_data['id'],
                package_id=package.id,
                file_name=f_data['file_name'],
                size=f_data.get('size'),
                file_sha1=f_data.get('file_sha1'),
                file_sha256=f_data.get('file_sha256'),
                created_at=parse_iso8601(f_data.get('created_at')),
                raw_data=f_data
            )
            self.session.add(f_obj)

    def _sync_wiki_logs(self, project: Project) -> None:
        """同步 Wiki 事件日志。"""
        for event in self.client.get_project_wiki_events(project.id):
            created_at = parse_iso8601(event['created_at'])
            
            # 检查是否已存在
            existing = self.session.query(GitLabWikiLog).filter_by(
                project_id=project.id,
                created_at=created_at
            ).first()
            
            if existing:
                continue
                
            wiki_log = GitLabWikiLog(
                project_id=project.id,
                title=event.get('target_title'),
                slug=event.get('target_title'),
                action=event.get('action_name'),
                created_at=created_at,
                raw_data=event
            )
            
            if event.get('author_id') and self.user_resolver:
                wiki_log.user_id = self.user_resolver.resolve(event['author_id'])
                
            self.session.add(wiki_log)

    def _sync_dependencies(self, project: Project) -> None:
        """同步项目的第三方/内部依赖关系。"""
        for dep in self.client.get_project_dependencies(project.id):
            # 简单去重：按名称和版本
            existing = self.session.query(GitLabDependency).filter_by(
                project_id=project.id,
                name=dep['name'],
                version=dep['version']
            ).first()
            
            if existing:
                continue
                
            dependency = GitLabDependency(
                project_id=project.id,
                name=dep['name'],
                version=dep['version'],
                package_manager=dep.get('package_manager'),
                dependency_type=dep.get('dependency_type'),
                raw_data=dep
            )
            self.session.add(dependency)
