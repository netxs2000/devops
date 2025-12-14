"""SonarQube Web API 客户端

基于 BaseClient 实现的 SonarQube REST API 封装。
API 文档: https://docs.sonarqube.org/latest/extension-guide/web-api/
"""
import base64
from typing import List, Dict, Optional, Any
from devops_collector.core.base_client import BaseClient


class SonarQubeClient(BaseClient):
    """SonarQube Web API 客户端。
    
    封装代码质量数据采集所需的 API 方法，包含：
    - 项目列表和详情
    - 代码质量指标 (覆盖率、Bug、漏洞等)
    - 问题列表 (可选)
    - 分析历史
    
    Attributes:
        base_url: SonarQube API 地址 (如 https://sonarqube.example.com/api)
    
    Example:
        client = SonarQubeClient(url="https://sonarqube.example.com", token="squ_xxx")
        measures = client.get_measures("my-project-key")
        print(measures['coverage'])  # 85.5
    """
    
    # 默认采集的核心指标
    DEFAULT_METRICS = [
        'coverage',                    # 代码覆盖率 (%)
        'bugs',                        # Bug 数
        'vulnerabilities',             # 漏洞数
        'code_smells',                 # 代码异味
        'duplicated_lines_density',    # 重复率 (%)
        'sqale_index',                 # 技术债务 (分钟)
        'reliability_rating',          # 可靠性评级 (1-5 = A-E)
        'security_rating',             # 安全性评级
        'sqale_rating',                # 可维护性评级
        'ncloc',                       # 代码行数 (Non-Comment Lines of Code)
        'complexity',                  # 圈复杂度
        'cognitive_complexity',        # 认知复杂度
    ]
    
    def __init__(self, url: str, token: str, rate_limit: int = 5) -> None:
        """初始化 SonarQube 客户端。
        
        Args:
            url: SonarQube 实例地址 (不含 /api)。
            token: SonarQube User Token (格式: squ_xxx 或旧版 token)。
            rate_limit: 每秒请求限制 (SonarQube 默认较低)。
        """
        # SonarQube 使用 token: 作为 Basic Auth
        auth_string = base64.b64encode(f"{token}:".encode()).decode()
        
        super().__init__(
            base_url=f"{url.rstrip('/')}/api",
            auth_headers={'Authorization': f'Basic {auth_string}'},
            rate_limit=rate_limit
        )
    
    def test_connection(self) -> bool:
        """测试 SonarQube 连接。"""
        try:
            response = self._get("system/status")
            return response.json().get('status') == 'UP'
        except Exception:
            return False
    
    def get_projects(
        self, 
        page: int = 1, 
        page_size: int = 100,
        organization: Optional[str] = None
    ) -> List[dict]:
        """获取所有项目列表。
        
        Args:
            page: 页码
            page_size: 每页数量
            organization: 组织 Key (SonarQube >= 7.0)
            
        Returns:
            项目列表
        """
        params = {'p': page, 'ps': page_size}
        if organization:
            params['organization'] = organization
            
        response = self._get("projects/search", params=params)
        return response.json().get('components', [])
    
    def get_all_projects(self, organization: Optional[str] = None) -> List[dict]:
        """获取所有项目 (自动分页)。"""
        projects = []
        page = 1
        
        while True:
            batch = self.get_projects(page=page, organization=organization)
            if not batch:
                break
            projects.extend(batch)
            page += 1
            
        return projects
    
    def get_project(self, key: str) -> Optional[dict]:
        """获取单个项目详情。
        
        Args:
            key: 项目 Key (如 com.example:my-project)
            
        Returns:
            项目信息字典，未找到返回 None
        """
        response = self._get("projects/search", params={'projects': key})
        components = response.json().get('components', [])
        return components[0] if components else None
    
    def get_measures(
        self, 
        project_key: str, 
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """获取项目代码质量指标。
        
        Args:
            project_key: 项目 Key
            metrics: 指标列表，默认使用 DEFAULT_METRICS
            
        Returns:
            {"metric_name": value, ...}
            
        Example:
            measures = client.get_measures("my-project")
            print(measures['coverage'])      # 85.5
            print(measures['bugs'])          # 12
            print(measures['sqale_index'])   # 480 (分钟)
        """
        if metrics is None:
            metrics = self.DEFAULT_METRICS
        
        response = self._get("measures/component", params={
            'component': project_key,
            'metricKeys': ','.join(metrics)
        })
        
        result = {}
        component = response.json().get('component', {})
        for measure in component.get('measures', []):
            result[measure['metric']] = measure.get('value')
        
        return result
    
    def get_issues(
        self, 
        project_key: str,
        page: int = 1,
        page_size: int = 100,
        resolved: bool = False,
        severities: Optional[List[str]] = None,
        types: Optional[List[str]] = None
    ) -> List[dict]:
        """获取项目问题列表。
        
        Args:
            project_key: 项目 Key
            page: 页码
            page_size: 每页数量
            resolved: 是否包含已解决的问题
            severities: 严重级别过滤 ['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR', 'INFO']
            types: 问题类型过滤 ['BUG', 'VULNERABILITY', 'CODE_SMELL']
            
        Returns:
            问题列表
        """
        params = {
            'componentKeys': project_key,
            'p': page,
            'ps': page_size,
            'resolved': 'true' if resolved else 'false'
        }
        
        if severities:
            params['severities'] = ','.join(severities)
        if types:
            params['types'] = ','.join(types)
        
        response = self._get("issues/search", params=params)
        return response.json().get('issues', [])
    
    def get_all_issues(
        self, 
        project_key: str,
        resolved: bool = False,
        **kwargs
    ) -> List[dict]:
        """获取项目所有问题 (自动分页)。
        
        警告: 问题数量可能很大，请谨慎使用。
        """
        issues = []
        page = 1
        
        while True:
            batch = self.get_issues(
                project_key, 
                page=page, 
                resolved=resolved,
                **kwargs
            )
            if not batch:
                break
            issues.extend(batch)
            page += 1
            
        return issues
    
    def get_analysis_history(
        self, 
        project_key: str,
        page: int = 1,
        page_size: int = 100
    ) -> List[dict]:
        """获取项目分析历史。
        
        Returns:
            分析记录列表，每条包含 key, date, events 等
        """
        response = self._get("project_analyses/search", params={
            'project': project_key,
            'p': page,
            'ps': page_size
        })
        return response.json().get('analyses', [])
    
    def get_quality_gate_status(self, project_key: str) -> dict:
        """获取项目质量门禁状态。
        
        Returns:
            {'status': 'OK|WARN|ERROR', 'conditions': [...]}
        """
        response = self._get("qualitygates/project_status", params={
            'projectKey': project_key
        })
        return response.json().get('projectStatus', {})
    
    @staticmethod
    def rating_to_letter(value: Any) -> str:
        """将数字评级转为字母 (1.0=A, 2.0=B, ...)。
        
        SonarQube 返回的 rating 是数字字符串，此方法转换为字母。
        """
        rating_map = {'1.0': 'A', '2.0': 'B', '3.0': 'C', '4.0': 'D', '5.0': 'E'}
        return rating_map.get(str(value), 'E')
