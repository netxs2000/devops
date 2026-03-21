"""DevOps Collector 核心算法与工具类

本模块提取了 Worker 中的复杂算法逻辑，以便进行独立测试和重用。
包含：
1. AgileMetrics: 敏捷效能指标计算 (Cycle Time, Lead Time)
2. CodeMetrics: 代码分析算法 (Diff 分析, 文件分类)
3. QualityMetrics: 质量指标转换逻辑
"""

import fnmatch
from datetime import datetime
from typing import Any


class AgileMetrics:
    """敏捷效能指标计算类。"""

    @staticmethod
    def calculate_cycle_time(histories: list[dict[str, Any]], start_status: str = "In Progress", end_status: str = "Done") -> float | None:
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
        sorted_histories = sorted(histories, key=lambda x: x["created_at"])
        for h in sorted_histories:
            if h.get("to_string") == start_status and start_time is None:
                start_time = h["created_at"]
            if h.get("to_string") == end_status:
                end_time = h["created_at"]
        if start_time and end_time and (end_time > start_time):
            duration = end_time - start_time
            return duration.total_seconds() / 3600.0
        return None

    @staticmethod
    def calculate_dora_lead_time(commit_times: list[datetime], deployment_time: datetime) -> float | None:
        """计算 DORA 标准的变更前置时间 (Lead Time for Changes)。

        计算逻辑：部署时间 - 最早一次代码提交时间。

        Args:
            commit_times: 属于该部署/MR 的所有提交时间列表。
            deployment_time: 成功部署到生产环境的时间。

        Returns:
            以小时为单位的时长。
        """
        if not commit_times or not deployment_time:
            return None

        first_commit = min(commit_times)
        if deployment_time > first_commit:
            duration = deployment_time - first_commit
            return duration.total_seconds() / 3600.0
        return 0.0

    @staticmethod
    def calculate_deployment_frequency(deployment_count: int, days: int) -> float:
        """计算部署频率。"""
        if days <= 0:
            return 0.0
        return deployment_count / days

    @staticmethod
    def calculate_change_failure_rate(total_deployments: int, failed_deployments: int) -> float:
        """计算变更失败率。

        Args:
            total_deployments: 总部署次数。
            failed_deployments: 失败的部署次数。

        Returns:
            失败率百分比 (0-100)。
        """
        if total_deployments == 0:
            return 0.0
        return (failed_deployments / total_deployments) * 100

    @staticmethod
    def calculate_mttr(incidents: list[Any]) -> float | None:
        """计算平均恢复时长 (MTTR)。

        Args:
            incidents: Incident 对象列表，需具有 occurred_at 和 resolved_at 属性。
        """
        durations = []
        for inc in incidents:
            if hasattr(inc, "resolved_at") and hasattr(inc, "occurred_at") and inc.resolved_at and inc.occurred_at:
                durations.append((inc.resolved_at - inc.occurred_at).total_seconds() / 3600.0)

        if not durations:
            return None
        return sum(durations) / len(durations)


class CodeMetrics:
    """代码分析与度量算法。"""

    COMMENT_SYMBOLS = {
        "py": "#",
        "rb": "#",
        "sh": "#",
        "yaml": "#",
        "yml": "#",
        "dockerfile": "#",
        "pl": "#",
        "r": "#",
        "java": "//",
        "js": "//",
        "ts": "//",
        "c": "//",
        "cpp": "//",
        "cs": "//",
        "go": "//",
        "rs": "//",
        "swift": "//",
        "kt": "//",
        "scala": "//",
        "php": "//",
        "html": "<!--",
        "xml": "<!--",
        "css": "/*",
        "scss": "/*",
        "less": "/*",
        "sql": "--",
    }
    IGNORED_PATTERNS = [
        "*.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "*.min.js",
        "*.min.css",
        "*.map",
        "node_modules/*",
        "dist/*",
        "build/*",
        "vendor/*",
        "*.svg",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.ico",
        "*.pdf",
        "*.exe",
        "*.dll",
        "*.so",
        "*.dylib",
    ]

    @classmethod
    def is_ignored(cls, file_path: str) -> bool:
        """检查文件是否应被忽略。"""
        for pattern in cls.IGNORED_PATTERNS:
            if fnmatch.fnmatch(file_path.lower(), pattern):
                return True
        return False

    @classmethod
    def analyze_diff(cls, diff_text: str, file_path: str) -> dict[str, int]:
        """分析 Git diff 文本，返回分类统计。"""
        stats = {
            "code_added": 0,
            "code_deleted": 0,
            "comment_added": 0,
            "comment_deleted": 0,
            "blank_added": 0,
            "blank_deleted": 0,
        }
        ext = file_path.rsplit(".", maxsplit=1)[-1].lower() if "." in file_path else ""
        symbol = cls.COMMENT_SYMBOLS.get(ext)
        for line in diff_text.split("\n"):
            if line.startswith("@@") or line.startswith("+++") or line.startswith("---"):
                continue
            if len(line) < 1:
                continue
            content = line[1:].strip()
            is_blank = content == ""
            is_comment = symbol and content.startswith(symbol)
            if line.startswith("+"):
                if is_blank:
                    stats["blank_added"] += 1
                elif is_comment:
                    stats["comment_added"] += 1
                else:
                    stats["code_added"] += 1
            elif line.startswith("-"):
                if is_blank:
                    stats["blank_deleted"] += 1
                elif is_comment:
                    stats["comment_deleted"] += 1
                else:
                    stats["code_deleted"] += 1
        return stats

    @staticmethod
    def get_file_category(file_path: str) -> str:
        path = file_path.lower()
        if any(p in path for p in ["/test/", "test/", "/tests/", "tests/", "test_", "_test.", "_spec."]):
            return "Test"
        iac_exts = {".tf", ".yaml", ".yml", ".json", ".sh"}
        iac_dirs = {"terraform/", "ansible/", "k8s/", "docker/", "ci-scripts/", "deploy/", "scripts/"}
        if any(dir_path in path for dir_path in iac_dirs) and path.endswith(tuple(iac_exts)):
            return "IaC"
        if "dockerfile" in path or "jenkinsfile" in path or ".gitlab-ci" in path:
            return "IaC"
        config_exts = {".conf", ".config", ".ini", ".env", ".properties", ".xml"}
        if path.endswith(tuple(config_exts)) or "config/" in path:
            return "Config"
        return "Code"


class QualityMetrics:
    """质量指标处理逻辑。"""

    @staticmethod
    def rating_to_letter(value: Any) -> str:
        """将数字评级转为字母 (1.0=A, 2.0=B, ...)。"""
        rating_map = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}
        return rating_map.get(str(value), "E")
