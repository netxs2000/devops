"""DevOps Collector 核心算法与工具类

本模块提取了 Worker 中的复杂算法逻辑，以便进行独立测试和重用。
包含：
1. AgileMetrics: 敏捷效能指标计算 (Cycle Time, Lead Time)
2. CodeMetrics: 代码分析算法 (Diff 分析, 文件分类)
3. QualityMetrics: 质量指标转换逻辑
"""
import fnmatch
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

class AgileMetrics:
    """敏捷效能指标计算类。"""

    @staticmethod
    def calculate_cycle_time(histories: List[Dict[str, Any]], start_status: str='In Progress', end_status: str='Done') -> Optional[float]:
        """计算 Cycle Time (周期时间)。
        
        Args:
            histories: Jira/ZenTao 的状态变更历史列表。
                       格式示例: [{'from_string': 'To Do', 'to_string': 'In Progress', 'created_at': datetime}]
            start_status: 开始统计的状态名。
            end_status: 结束统计的状态名。
            
        Returns:
            以小时为单位的时长，如果无法计算则返回 None。
        """
        start_time = None
        end_time = None
        sorted_histories = sorted(histories, key=lambda x: x['created_at'])
        for h in sorted_histories:
            if h.get('to_string') == start_status and start_time is None:
                start_time = h['created_at']
            if h.get('to_string') == end_status:
                end_time = h['created_at']
        if start_time and end_time and (end_time > start_time):
            duration = end_time - start_time
            return duration.total_seconds() / 3600.0
        return None

    @staticmethod
    def calculate_lead_time(created_at: datetime, resolved_at: Optional[datetime]) -> Optional[float]:
        """计算 Lead Time (前置时间/总耗时)。
        
        Args:
            created_at: 创建时间。
            resolved_at: 解决/完成时间。
            
        Returns:
            以小时为单位的时长。
        """
        if created_at and resolved_at and (resolved_at > created_at):
            duration = resolved_at - created_at
            return duration.total_seconds() / 3600.0
        return None

class CodeMetrics:
    """代码分析与度量算法。"""
    COMMENT_SYMBOLS = {'py': '#', 'rb': '#', 'sh': '#', 'yaml': '#', 'yml': '#', 'dockerfile': '#', 'pl': '#', 'r': '#', 'java': '//', 'js': '//', 'ts': '//', 'c': '//', 'cpp': '//', 'cs': '//', 'go': '//', 'rs': '//', 'swift': '//', 'kt': '//', 'scala': '//', 'php': '//', 'html': '<!--', 'xml': '<!--', 'css': '/*', 'scss': '/*', 'less': '/*', 'sql': '--'}
    IGNORED_PATTERNS = ['*.lock', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', '*.min.js', '*.min.css', '*.map', 'node_modules/*', 'dist/*', 'build/*', 'vendor/*', '*.svg', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.pdf', '*.exe', '*.dll', '*.so', '*.dylib']

    @classmethod
    def is_ignored(cls, file_path: str) -> bool:
        """检查文件是否应被忽略。"""
        for pattern in cls.IGNORED_PATTERNS:
            if fnmatch.fnmatch(file_path.lower(), pattern):
                return True
        return False

    @classmethod
    def analyze_diff(cls, diff_text: str, file_path: str) -> Dict[str, int]:
        """分析 Git diff 文本，返回分类统计。"""
        stats = {'code_added': 0, 'code_deleted': 0, 'comment_added': 0, 'comment_deleted': 0, 'blank_added': 0, 'blank_deleted': 0}
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        symbol = cls.COMMENT_SYMBOLS.get(ext)
        for line in diff_text.split('\n'):
            if line.startswith('@@') or line.startswith('+++') or line.startswith('---'):
                continue
            if len(line) < 1:
                continue
            content = line[1:].strip()
            is_blank = content == ''
            is_comment = symbol and content.startswith(symbol)
            if line.startswith('+'):
                if is_blank:
                    stats['blank_added'] += 1
                elif is_comment:
                    stats['comment_added'] += 1
                else:
                    stats['code_added'] += 1
            elif line.startswith('-'):
                if is_blank:
                    stats['blank_deleted'] += 1
                elif is_comment:
                    stats['comment_deleted'] += 1
                else:
                    stats['code_deleted'] += 1
        return stats

    @staticmethod
    def get_file_category(file_path: str) -> str:
        """根据文件路径和扩展名识别文件分类。"""
        path = file_path.lower()
        if any((p in path for p in ['/test/', '/tests/', 'test_', '_test.'])):
            return 'Test'
        iac_exts = {'.tf', '.yaml', '.yml', '.json', '.sh'}
        iac_dirs = {'terraform/', 'ansible/', 'k8s/', 'docker/', 'ci-scripts/', 'deploy/'}
        if any((dir_path in path for dir_path in iac_dirs)) or path.endswith(tuple(iac_exts)):
            if 'dockerfile' in path or 'jenkinsfile' in path or '.gitlab-ci' in path:
                return 'IaC'
        config_exts = {'.conf', '.config', '.ini', '.env', '.properties', '.xml'}
        if path.endswith(tuple(config_exts)) or 'config/' in path:
            return 'Config'
        return 'Code'

class QualityMetrics:
    """质量指标处理逻辑。"""

    @staticmethod
    def rating_to_letter(value: Any) -> str:
        """将数字评级转为字母 (1.0=A, 2.0=B, ...)。"""
        rating_map = {'1.0': 'A', '2.0': 'B', '3.0': 'C', '4.0': 'D', '5.0': 'E'}
        return rating_map.get(str(value), 'E')