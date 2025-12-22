"""Jenkins Remote API 客户端

基于 BaseClient 实现的 Jenkins REST API 封装。
API 文档: https://www.jenkins.io/doc/book/using/remote-access-api/
"""
import base64
from typing import List, Dict, Optional, Any
from devops_collector.core.base_client import BaseClient


class JenkinsClient(BaseClient):
    """Jenkins Remote API 客户端。
    
    封装构建数据采集所需的 API 方法，支持 Folder 递归结构，
    提供 Job 与 Build 的元数据及测试报告获取功能。
    
    Attributes:
        base_url (str): Jenkins 实例的基础地址。
        headers (dict): 包含 Basic Auth 的认证头。
    """
    
    def __init__(self, url: str, user: str, token: str, rate_limit: int = 10) -> None:
        """初始化 Jenkins 客户端。
        
        Args:
            url (str): Jenkins 实例地址 (如 http://jenkins.example.com)。
            user (str): Jenkins 用户名。
            token (str): Jenkins API Token (建议使用 Token 而非密码)。
            rate_limit (int): 每秒请求限制。默认为 10。
        """
        # Jenkins 使用 user:token 作为 Basic Auth
        auth_string = base64.b64encode(f"{user}:{token}".encode()).decode()
        
        super().__init__(
            base_url=f"{url.rstrip('/')}",
            auth_headers={'Authorization': f'Basic {auth_string}'},
            rate_limit=rate_limit
        )

    def test_connection(self) -> bool:
        """测试与 Jenkins 实例的连接状态。
        
        通过访问基础信息接口来验证认证是否通过。
        
        Returns:
            bool: 如果连接成功返回 True，否则返回 False。
        """
        try:
            # 获取 Jenkins 基础信息
            response = self._get("api/json")
            return response.status_code == 200
        except Exception:
            return False

    def get_jobs(self, folder: Optional[str] = None) -> List[dict]:
        """获取指定文件夹下的 Job 列表。
        
        Args:
            folder (Optional[str]): 文件夹路径 (如 'folder1/folder2')。如果为 None，则获取根目录 Job。
            
        Returns:
            List[dict]: Job 信息列表，每个元素包含 name, url, color, description, fullName 等字段。
        """
        endpoint = "api/json"
        if folder:
            # Jenkins 文件夹路径 API 格式: job/folder1/job/folder2/api/json
            path_parts = folder.strip('/').split('/')
            folder_path = "".join([f"job/{p}/" for p in path_parts])
            endpoint = f"{folder_path}api/json"
            
        params = {'tree': 'jobs[name,url,color,description,fullName]'}
        response = self._get(endpoint, params=params)
        return response.json().get('jobs', [])

    def get_all_jobs_recursive(self, folder: Optional[str] = None) -> List[dict]:
        """递归获取所有 Job (包括子文件夹下的)。
        
        注意：当前实现主要依赖 `get_jobs`，对于深层嵌套可能需要进一步完善递归逻辑。
        
        Args:
            folder (Optional[str]): 起始文件夹路径。
            
        Returns:
            List[dict]: 扁平化的所有 Job 列表。
        """
        all_jobs = []
        jobs = self.get_jobs(folder)
        
        for job in jobs:
            # TODO(Optimization): 完善递归逻辑，根据 _class 类型准确判断是否为 Folder
            # 目前简单将所有返回项视为 Job 返回
            all_jobs.append(job)
            
        return all_jobs

    def get_job_details(self, job_full_name: str) -> Dict[str, Any]:
        """获取单个 Job 的详细配置信息。
        
        Args:
            job_full_name (str): Job 的完整路径名称 (例如 'folder/job_name')。
            
        Returns:
            Dict[str, Any]: 包含 Job 完整配置的字典。
        """
        path_parts = job_full_name.strip('/').split('/')
        job_path = "".join([f"job/{p}/" for p in path_parts])
        endpoint = f"{job_path}api/json"
        
        response = self._get(endpoint)
        return response.json()

    def get_builds(self, job_full_name: str, limit: int = 100) -> List[dict]:
        """获取指定 Job 的构建历史列表。
        
        Args:
            job_full_name (str): Job 的完整路径名称。
            limit (int): 获取最近构建的数量限制。默认为 100。
            
        Returns:
            List[dict]: 构建记录列表，仅包含摘要信息 (number, url)。
        """
        path_parts = job_full_name.strip('/').split('/')
        job_path = "".join([f"job/{p}/" for p in path_parts])
        endpoint = f"{job_path}api/json"
        
        # 仅获取 build 摘要信息，减少数据传输
        params = {'tree': f'builds[number,url]{{0,{limit}}}'}
        response = self._get(endpoint, params=params)
        return response.json().get('builds', [])

    def get_build_details(self, build_url: str) -> Dict[str, Any]:
        """获取单次构建的详细信息。
        
        Args:
            build_url (str): 构建的完整 URL 或相对路径。
            
        Returns:
            Dict[str, Any]: 包含构建结果、耗时、触发原因等详细信息的字典。
        """
        # 如果是完整 URL，需要移除 base_url 部分以适配 _get 方法
        endpoint = build_url.replace(self.base_url, "").strip('/')
        endpoint = f"{endpoint}/api/json"
        
        response = self._get(endpoint)
        return response.json()

    def get_test_report(self, build_url: str) -> Optional[Dict[str, Any]]:
        """获取构建的自动化测试报告详情。
        
        对应 API: BUILD_URL/testReport/api/json
        
        Args:
            build_url (str): 构建的完整 URL 或相对路径。
            
        Returns:
            Optional[Dict[str, Any]]: 测试报告字典。如果该构建无测试报告或请求失败，返回 None。
        """
        endpoint = build_url.replace(self.base_url, "").strip('/')
        endpoint = f"{endpoint}/testReport/api/json"
        
        try:
            response = self._get(endpoint)
            # 404 表示无测试报告，属于正常情况不应抛出异常
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            # 忽略所有获取报告过程中的错误，避免中断主流程
            return None
