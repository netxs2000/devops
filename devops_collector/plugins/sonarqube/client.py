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
        'files',                       # 文件数
        'lines',                       # 总行数
        'classes',                     # 类
        'functions',                   # 方法
        'statements',                  # 语句
        'security_hotspots',           # 安全热点
        'comment_lines_density',       # 注释行密度
        'sqale_debt_ratio',            # 技术债务率
        'bugs',
        'vulnerabilities',
        'blocker_violations',          # 阻塞 (Bug + Vul + CodeSmell) - 需要单独处理或联合查询
        'critical_violations',
        'major_violations',
        'minor_violations',
        'info_violations',
        # 注意: SonarQube API 不直接提供 bugs_blocker 这样的组合指标，通常需要通过 issues/search faceted search 获取
        # 或者使用 new_violations 指标 (如果是增量)
        # 这里为了保持简单，我们先不通过 measures/component 获取细分，而是通过单独的 issue 聚合逻辑
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
        """将数字评级转为字母 (1.0=A, 2.0=B, ...)。"""
        from devops_collector.core.algorithms import QualityMetrics
        return QualityMetrics.rating_to_letter(value)

    def get_issue_severity_distribution(self, project_key: str) -> Dict[str, Dict[str, int]]:
        """获取项目问题类型和严重程度的分布统计。
        
        Uses facets to avoid fetching all issues.
        
        Returns:
            {
                'BUG': {'BLOCKER': 1, 'CRITICAL': 2, ...},
                'VULNERABILITY': {'...'},
                ...
            }
        """
        # 我们需要同时按 severities 和 types 进行 facet，但 SonarQube API 的 facets 是一维的。
        # 为了获取准确的 (Type, Severity) 组合，我们需要对每种 Type 分别查询 Severity 分布。
        
        distribution = {
            'BUG': {},
            'VULNERABILITY': {},
            'CODE_SMELL': {}
        }
        
        for issue_type in distribution.keys():
            response = self._get("issues/search", params={
                'componentKeys': project_key,
                'types': issue_type,
                'resolved': 'false',
                'ps': 1,       # 我们只关心 facet，不需要 issue 列表
                'facets': 'severities'
            })
            
            data = response.json()
            facets = data.get('facets', [])
            
            for facet in facets:
                if facet['property'] == 'severities':
                    for value in facet.get('values', []):
                        severity = value['val']
                        count = value['count']
                        distribution[issue_type][severity] = count
                        
        return distribution

    def get_hotspot_distribution(self, project_key: str) -> Dict[str, int]:
        """获取项目安全热点风险程度分布。
        
        API: api/hotspots/search (SonarQube >= 8.x)
        注意: Hotspots search API 并不是标准的 facet API，通常需要直接 search 并聚合
        或者如果支持 facets 参数则使用 facets。
        
        对于较新版本 SonarQube，推荐使用 api/hotspots/search?projectKey=...
        然而，为了通用性，我们模拟分布统计。
        如果 API 不直接支持聚合，我们可能需要拉取列表 (通常热点数量远少于 issues)。
        这里我们尝试使用 facets (如果支持) 或者 fallback 到分页拉取。
        
        SonarQube 8.2+ 引入了 Dedicated Hotspots API。
        """
        distribution = {
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        }
        
        # 尝试拉取所有 open 的热点 (通常数量也就是几十到几百个)
        try:
            page = 1
            while True:
                response = self._get("hotspots/search", params={
                    'projectKey': project_key,
                    'status': 'TO_REVIEW', # 只统计待处理的 (OPEN)
                    'p': page,
                    'ps': 500
                })
                data = response.json()
                hotspots = data.get('hotspots', [])
                
                if not hotspots:
                    break
                    
                for h in hotspots:
                    # probability: HIGH, MEDIUM, LOW
                    prob = h.get('vulnerabilityProbability', 'LOW')
                    if prob in distribution:
                        distribution[prob] += 1
                
                # 如果返回数量少于页大小，说明是最后一页
                paging = data.get('paging', {})
                total = paging.get('total', 0)
                if (page * 500) >= total:
                    break
                    
                page += 1
                
        except Exception:
            # 兼容旧版本或 API 不存在的情况
            pass
            
        return distribution
