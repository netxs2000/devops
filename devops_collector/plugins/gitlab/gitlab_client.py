"""GitLab API 客户端"""
from typing import List, Dict, Optional, Any, Generator
from devops_collector.core.base_client import BaseClient

class GitLabClient(BaseClient):
    """GitLab REST API 客户端。
    
    封装了 GitLab API v4 的常用接口调用，处理分页、认证及基础的错误重试。
    """

    def __init__(self, url: str, token: str, rate_limit: int=10, verify_ssl: bool=True):
        """初始化 GitLab 客户端。
        
        Args:
            url (str): GitLab 实例的 URL (如 https://gitlab.com)。
            token (str): 用户的 Private Token 或 Access Token。
            rate_limit (int): 每秒请求数限制。默认为 10。
            verify_ssl (bool): 是否验证 SSL 证书。
        """
        super().__init__(base_url=f"{url.rstrip('/')}/api/v4", auth_headers={'PRIVATE-TOKEN': token}, rate_limit=rate_limit, verify=verify_ssl)

    def test_connection(self) -> bool:
        """测试与 GitLab 的连接状态 (快速探测，不进行重试)。"""
        try:
            url = f"{self.base_url}/version"
            import requests
            response = requests.get(url, headers=self.headers, timeout=5, verify=self.verify)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def get_project(self, project_id: int) -> dict:
        """获取单个项目的详细信息。
        
        Args:
            project_id (int): GitLab 项目 ID。
            
        Returns:
            dict: 项目详情字典。
        """
        return self._get(f'projects/{project_id}', params={'statistics': True}).json()

    def get_group(self, group_id_or_path: str) -> dict:
        """获取单个群组的详细信息。

        Args:
            group_id_or_path (str): 群组 ID 或 URL 编码后的路径。

        Returns:
            dict: 群组详情字典。
        """
        return self._get(f'groups/{group_id_or_path}').json()

    def get_project_commits(self, project_id: int, since: Optional[str]=None, start_page: int=1, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的提交记录。

        Args:
            project_id (int): GitLab 项目 ID。
            since (Optional[str]): 仅获取该时间之后的提交 (ISO 8601 格式)。
            start_page (int): 起始页码。默认为 1。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个提交记录的字典数据。
        """
        page = start_page
        while True:
            params = {'per_page': per_page, 'page': page}
            if since:
                params['since'] = since
            response = self._get(f'projects/{project_id}/repository/commits', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_commit_diff(self, project_id: int, commit_sha: str) -> List[dict]:
        """获取指定提交的差异 (Diff) 信息。

        Args:
            project_id (int): GitLab 项目 ID。
            commit_sha (str): 提交的 SHA 哈希值。

        Returns:
            List[dict]: 包含文件变更差异列表。
        """
        return self._get(f'projects/{project_id}/repository/commits/{commit_sha}/diff').json()

    def get_project_issues(self, project_id: int, since: Optional[str]=None, start_page: int=1, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的 Issue 列表。

        Args:
            project_id (int): GitLab 项目 ID。
            since (Optional[str]): 仅获取该时间之后更新的 Issue (ISO 8601 格式)。
            start_page (int): 起始页码。默认为 1。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个 Issue 的字典数据。
        """
        page = start_page
        while True:
            params = {'per_page': per_page, 'page': page}
            if since:
                params['updated_after'] = since
            response = self._get(f'projects/{project_id}/issues', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_project_merge_requests(self, project_id: int, since: Optional[str]=None, start_page: int=1, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的合并请求 (MR) 列表。

        Args:
            project_id (int): GitLab 项目 ID。
            since (Optional[str]): 仅获取该时间之后更新的 MR (ISO 8601 格式)。
            start_page (int): 起始页码。默认为 1。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个 MR 的字典数据。
        """
        page = start_page
        while True:
            params = {'per_page': per_page, 'page': page}
            if since:
                params['updated_after'] = since
            response = self._get(f'projects/{project_id}/merge_requests', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_project_pipelines(self, project_id: int, start_page: int=1, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的流水线列表。

        Args:
            project_id (int): GitLab 项目 ID。
            start_page (int): 起始页码。默认为 1。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个流水线的字典数据。
        """
        page = start_page
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/pipelines', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_project_deployments(self, project_id: int, start_page: int=1, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的部署记录列表。

        Args:
            project_id (int): GitLab 项目 ID。
            start_page (int): 起始页码。默认为 1。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个部署记录的字典数据。
        """
        page = start_page
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/deployments', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_issue_notes(self, project_id: int, issue_iid: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取 Issue 的评论 (Notes)。

        Args:
            project_id (int): GitLab 项目 ID。
            issue_iid (int): Issue 的 IID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个评论的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/issues/{issue_iid}/notes', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_mr_notes(self, project_id: int, mr_iid: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取合并请求的评论 (Notes)。

        Args:
            project_id (int): GitLab 项目 ID。
            mr_iid (int): MR 的 IID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个评论的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/merge_requests/{mr_iid}/notes', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_mr_approvals(self, project_id: int, mr_iid: int) -> dict:
        """获取合并请求的审批详情。
        
        Args:
            project_id (int): GitLab 项目 ID。
            mr_iid (int): MR 的 IID。

        Returns:
            dict: 包含审批人信息的字典。
        """
        return self._get(f'projects/{project_id}/merge_requests/{mr_iid}/approvals').json()

    def get_mr_pipelines(self, project_id: int, mr_iid: int) -> List[dict]:
        """获取合并请求关联的流水线。
        
        Args:
            project_id (int): GitLab 项目 ID。
            mr_iid (int): MR 的 IID。

        Returns:
            List[dict]: 流水线记录列表。
        """
        return self._get(f'projects/{project_id}/merge_requests/{mr_iid}/pipelines').json()

    def get_project_tags(self, project_id: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的标签 (Tag) 列表。

        Args:
            project_id (int): GitLab 项目 ID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个标签的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/repository/tags', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_project_branches(self, project_id: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的分支 (Branch) 列表。

        Args:
            project_id (int): GitLab 项目 ID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个分支的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/repository/branches', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_project_members(self, project_id: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的成员列表。

        Args:
            project_id (int): GitLab 项目 ID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个成员的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/members/all', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_project_milestones(self, project_id: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目的里程碑列表。

        Args:
            project_id (int): GitLab 项目 ID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个里程碑的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/milestones', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_user(self, user_id: int) -> dict:
        """获取单个用户的详细信息。

        Args:
            user_id (int): 用户 ID。

        Returns:
            dict: 用户详情字典。
        """
        return self._get(f'users/{user_id}').json()

    def get_count(self, endpoint: str, params: Optional[Dict]=None) -> int:
        """获取指定资源的数量 (通过 x-total 头)。

        Args:
            endpoint (str): API 端点。
            params (Optional[Dict]): 查询参数。

        Returns:
            int: 资源总数。
        """
        response = self._get(endpoint, params={**(params or {}), 'per_page': 1})
        return int(response.headers.get('x-total', 0))

    def get_group_members(self, group_id: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取群组的成员列表。

        Args:
            group_id (int): 群组 ID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个成员的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'groups/{group_id}/members', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_packages(self, project_id: int, per_page: int=100) -> Generator[Dict, None, None]:
        """获取项目制品库下的包列表。

        Args:
            project_id (int): GitLab 项目 ID。
            per_page (int): 每页数量。默认为 100。

        Yields:
            dict: 单个包的字典数据。
        """
        page = 1
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f'projects/{project_id}/packages', params=params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def get_package_files(self, project_id: int, package_id: int) -> List[dict]:
        """获取包关联的文件列表。

        Args:
            project_id (int): GitLab 项目 ID。
            package_id (int): 包 ID。

        Returns:
            List[dict]: 文件列表。
        """
        return self._get(f'projects/{project_id}/packages/{package_id}/package_files').json()

    def create_group_label(self, group_id: int, label_data: Dict) -> dict:
        """创建群组标签。

        Args:
            group_id (int): 群组 ID。
            label_data (Dict): 标签数据 (name, color, description)。

        Returns:
            dict: 创建后的标签详情。
        """
        return self._post(f'groups/{group_id}/labels', data=label_data).json()

    def create_project_label(self, project_id: int, label_data: Dict) -> dict:
        """创建项目标签。

        Args:
            project_id (int): 项目 ID。
            label_data (Dict): 标签数据 (name, color, description)。

        Returns:
            dict: 创建后的标签详情。
        """
        return self._post(f'projects/{project_id}/labels', data=label_data).json()

    def add_issue_label(self, project_id: int, issue_iid: int, labels: List[str]) -> dict:
        """为 Issue 添加标签。

        Args:
            project_id (int): 项目 ID。
            issue_iid (int): Issue 的 IID。
            labels (List[str]): 要添加的标签名称列表。

        Returns:
            dict: 更新后的 Issue 详情。
        """
        return self._put(f'projects/{project_id}/issues/{issue_iid}', data={'add_labels': ','.join(labels)}).json()

    def add_issue_note(self, project_id: int, issue_iid: int, body: str) -> dict:
        """为 Issue 添加评论。

        Args:
            project_id (int): 项目 ID。
            issue_iid (int): Issue 的 IID。
            body (str): 评论内容。

        Returns:
            dict: 创建后的 Note 详情。
        """
        return self._post(f'projects/{project_id}/issues/{issue_iid}/notes', data={'body': body}).json()

    def get_issue_state_events(self, project_id: int, issue_iid: int) -> Generator[Dict, None, None]:
        """获取 Issue 的状态变更事件。

        Args:
            project_id (int): 项目 ID。
            issue_iid (int): Issue 的 IID。

        Yields:
            dict: 单个状态变更事件字典。
        """
        return self._get_paged_data(f'projects/{project_id}/issues/{issue_iid}/resource_state_events')

    def get_issue_label_events(self, project_id: int, issue_iid: int) -> Generator[Dict, None, None]:
        """获取 Issue 的标签变更事件。

        Args:
            project_id (int): 项目 ID。
            issue_iid (int): Issue 的 IID。

        Yields:
            dict: 单个标签变更事件字典。
        """
        return self._get_paged_data(f'projects/{project_id}/issues/{issue_iid}/resource_label_events')

    def get_issue_milestone_events(self, project_id: int, issue_iid: int) -> Generator[Dict, None, None]:
        """获取 Issue 的里程碑变更事件。

        Args:
            project_id (int): 项目 ID。
            issue_iid (int): Issue 的 IID。

        Yields:
            dict: 单个里程碑变更事件字典。
        """
        return self._get_paged_data(f'projects/{project_id}/issues/{issue_iid}/resource_milestone_events')

    def get_project_wiki_events(self, project_id: int) -> Generator[Dict, None, None]:
        """获取项目的 Wiki 事件。

        Args:
            project_id (int): 项目 ID。

        Yields:
            dict: 单个 Wiki 事件字典。
        """
        return self._get_paged_data(f'projects/{project_id}/events', params={'target_type': 'wiki_page'})

    def get_project_dependencies(self, project_id: int) -> Generator[Dict, None, None]:
        """获取项目依赖列表 (需开启 Dependency Scanning)。

        Args:
            project_id (int): 项目 ID。

        Yields:
            dict: 单个依赖项字典。
        """
        return self._get_paged_data(f'projects/{project_id}/dependencies')

    def _get_paged_data(self, endpoint: str, params: Optional[Dict]=None) -> Generator[Dict, None, None]:
        """(内部方法) 处理分页数据获取。

        Args:
            endpoint (str): API 端点。
            params (Optional[Dict]): 附加的查询参数。

        Yields:
            dict: 每一项数据。
        """
        page = 1
        per_page = 100
        while True:
            _params = {'per_page': per_page, 'page': page}
            if params:
                _params.update(params)
            response = self._get(endpoint, params=_params)
            data = response.json()
            if not data:
                break
            for item in data:
                yield item
            page += 1

    def update_issue(self, project_id: int, issue_iid: int, data: Dict) -> dict:
        """更新 Issue 属性 (如里程碑、标题等)。

        Args:
            project_id (int): 项目 ID。
            issue_iid (int): Issue 的 IID。
            data (Dict): 要更新的字段字典。

        Returns:
            dict: 更新后的 Issue 详情。
        """
        return self._put(f'projects/{project_id}/issues/{issue_iid}', data=data).json()

    def create_project_tag(self, project_id: int, tag_name: str, ref: str, message: str=None) -> dict:
        """创建项目标签 (Tag)。

        Args:
            project_id (int): 项目 ID。
            tag_name (str): 标签名 (如 v1.0.0)。
            ref (str): 基于的分支或 SHA (如 main)。
            message (str): 标签消息。

        Returns:
            dict: 创建后的 Tag 详情。
        """
        data = {'tag_name': tag_name, 'ref': ref}
        if message:
            data['message'] = message
        return self._post(f'projects/{project_id}/repository/tags', data=data).json()

    def create_project_release(self, project_id: int, tag_name: str, description: str, milestones: List[str]=None) -> dict:
        """创建项目发布 (Release)。

        Args:
            project_id (int): 项目 ID。
            tag_name (str): 标签名 (必须已存在或同时创建)。
            description (str): 发布说明 (Release Notes)。
            milestones (List[str]): 关联的里程碑标题列表。

        Returns:
            dict: 创建后的 Release 详情。
        """
        data = {'tag_name': tag_name, 'description': description}
        if milestones:
            data['milestones'] = milestones
        return self._post(f'projects/{project_id}/releases', data=data).json()

    def update_project_milestone(self, project_id: int, milestone_id: int, data: Dict) -> dict:
        """更新项目里程碑 (如关闭里程碑)。

        Args:
            project_id (int): 项目 ID。
            milestone_id (int): 里程碑 ID。
            data (Dict): 要更新的字段 (如 {'state_event': 'close'})。

        Returns:
            dict: 更新后的里程碑详情。
        """
        return self._put(f'projects/{project_id}/milestones/{milestone_id}', data=data).json()

    def create_project_milestone(self, project_id: int, title: str, start_date: str=None, due_date: str=None, description: str=None) -> dict:
        """创建项目里程碑。

        Args:
            project_id (int): 项目 ID。
            title (str): 里程碑标题。
            start_date (str): 开始日期 (YYYY-MM-DD)。
            due_date (str): 截止日期 (YYYY-MM-DD)。
            description (str): 描述。

        Returns:
            dict: 创建后的里程碑详情。
        """
        data = {'title': title}
        if start_date:
            data['start_date'] = start_date
        if due_date:
            data['due_date'] = due_date
        if description:
            data['description'] = description
        return self._post(f'projects/{project_id}/milestones', data=data).json()

    def create_issue(self, project_id: int, data: Dict) -> dict:
        """创建 Issue。

        Args:
            project_id (int): 项目 ID。
            data (Dict): Issue 数据 (title, description, labels 等)。

        Returns:
            dict: 创建后的 Issue 详情。
        """
        return self._post(f'projects/{project_id}/issues', data=data).json()

    def get_file_last_commit(self, project_id: int, file_path: str, ref: str) -> Optional[dict]:
        """获取指定文件在特定 ref 之前的最后一次提交信息。

        用于判断文件变更时间间隔，支持 Churn (短期重写) 和 Legacy (老代码) 判定。

        Args:
            project_id (int): GitLab 项目 ID。
            file_path (str): 文件路径。
            ref (str): 当前提交的 SHA 或分支名 (将作为 until 参数或排除当前提交)。

        Returns:
            Optional[dict]: 最后一次提交的详情 (包含 committed_date)，若无历史则返回 None。
        """
        # 获取该文件的提交历史，取第2条 (跳过当前 ref 本身，或者基于业务逻辑调整)
        # 注意: GitLab API 并没有直接的 "last modified before SHA" 参数
        # 这里的策略是获取 ref 所在的历史列表，然后看该文件最近的变更
        params = {
            'path': file_path,
            'ref_name': ref, # 使用 ref_name 限定分支/提交点
            'per_page': 2    # 取最近两条: 第1条通常是当前提交(如果是基于HEAD)，第2条是上次
        }
        try:
            commits = self._get(f'projects/{project_id}/repository/commits', params=params).json()
            if len(commits) >= 2:
                return commits[1] # 返回上一次提交
            # 如果只有1条记录，说明是该文件首次创建，没有"上一次"
            return None
        except Exception:
            return None