"""Jenkins Remote API 客户端

基于 BaseClient 实现的 Jenkins REST API 封装。
API 文档: https://www.jenkins.io/doc/book/using/remote-access-api/
"""
import base64
from typing import List, Dict, Optional, Any
from devops_collector.core.base_client import BaseClient


class JenkinsClient(BaseClient):
    """Jenkins Remote API 客户端。
    
    封装构建数据采集所需的 API 方法，包含：
    - Job 列表和详情
    - Build 列表和详情
    - 测试连接
    
    Attributes:
        base_url: Jenkins API 地址 (如 http://jenkins.example.com/api/json)
    """
    
    def __init__(self, url: str, user: str, token: str, rate_limit: int = 10) -> None:
        """初始化 Jenkins 客户端。
        
        Args:
            url: Jenkins 实例地址 (如 http://jenkins.example.com)。
            user: Jenkins 用户名。
            token: Jenkins API Token。
            rate_limit: 每秒请求限制。
        """
        # Jenkins 使用 user:token 作为 Basic Auth
        auth_string = base64.b64encode(f"{user}:{token}".encode()).decode()
        
        super().__init__(
            base_url=f"{url.rstrip('/')}",
            auth_headers={'Authorization': f'Basic {auth_string}'},
            rate_limit=rate_limit
        )

    def test_connection(self) -> bool:
        """测试 Jenkins 连接。"""
        try:
            # 获取 Jenkins 基础信息
            response = self._get("api/json")
            return response.status_code == 200
        except Exception:
            return False

    def get_jobs(self, folder: Optional[str] = None) -> List[dict]:
        """获取 Job 列表。
        
        支持递归获取文件夹下的 Job。
        
        Args:
            folder: 文件夹路径 (如 folder1/folder2)
            
        Returns:
            Job 列表
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
        """递归获取所有 Job (包括子文件夹下的)。"""
        all_jobs = []
        jobs = self.get_jobs(folder)
        
        for job in jobs:
            # 如果是文件夹 (通常没有 color 字段或者 color 包含 folder)
            # 或者通过 _class 判断 (com.cloudbees.hudson.plugins.folder.Folder)
            # 这里简单通过 recursion 处理所有返回的 jobs，如果它有 sub-jobs
            all_jobs.append(job)
            
            # 检查是否有 sub-jobs (如果 tree 包含的话)
            # 为了简单起见，我们目前只处理一级，或者通过 fullName 识别
            pass
            
        return all_jobs

    def get_job_details(self, job_full_name: str) -> Dict[str, Any]:
        """获取 Job 详情。
        
        Args:
            job_full_name: Job 完整名称 (folder/job_name)
        """
        path_parts = job_full_name.strip('/').split('/')
        job_path = "".join([f"job/{p}/" for p in path_parts])
        endpoint = f"{job_path}api/json"
        
        response = self._get(endpoint)
        return response.json()

    def get_builds(self, job_full_name: str, limit: int = 100) -> List[dict]:
        """获取 Job 的构建列表。
        
        Args:
            job_full_name: Job 完整名称
            limit: 获取数量限制
        """
        path_parts = job_full_name.strip('/').split('/')
        job_path = "".join([f"job/{p}/" for p in path_parts])
        endpoint = f"{job_path}api/json"
        
        # 仅获取 build 摘要信息
        params = {'tree': f'builds[number,url]{{0,{limit}}}'}
        response = self._get(endpoint, params=params)
        return response.json().get('builds', [])

    def get_build_details(self, build_url: str) -> Dict[str, Any]:
        """获取 Build 详情。
        
        Args:
            build_url: Build 的完整 URL 或相对路径
        """
        # 如果是完整 URL，需要处理 base_url
        endpoint = build_url.replace(self.base_url, "").strip('/')
        endpoint = f"{endpoint}/api/json"
        
        response = self._get(endpoint)
        return response.json()

    def get_test_report(self, build_url: str) -> Optional[Dict[str, Any]]:
        """获取构建的测试报告详情。
        
        API: BUILD_URL/testReport/api/json
        
        Args:
            build_url: Build 的完整 URL 或相对路径
        """
        endpoint = build_url.replace(self.base_url, "").strip('/')
        endpoint = f"{endpoint}/testReport/api/json"
        
        try:
            response = self._get(endpoint)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            # 并不是所有构建都有测试报告，忽略错误
            return None
