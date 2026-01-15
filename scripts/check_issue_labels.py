"""GitLab Issue 标签完整性检查工具 (重构版)

使用统一的标签定义库和 API 客户端，自动识别不符合规范的 Issue。
"""

import argparse
import sys
import csv
from typing import List, Dict

from devops_collector.config import Config
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.gitlab.labels import LABEL_DEFINITIONS
try:
    from devops_collector.core.logger import logger
except ImportError:
    logger = None

if not logger:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('LabelChecker')


class IssueLabelChecker:
    """Issue 标签完整性检查器。"""
    
    # 基于统一标签库映射必要性规则
    CHECK_RULES = {
        "bug": ["type", "severity", "priority", "bug_category", "bug_source", "province"],
        "feature": ["type", "priority"],
        "test": ["type", "priority"]
    }
    
    def __init__(self, client: GitLabClient):
        self.client = client
        # 将 LABEL_DEFINITIONS 转换为按前缀索引的字典，方便检查
        self.label_pools = {}
        for category, items in LABEL_DEFINITIONS.items():
            self.label_pools[category] = {item['name'] for item in items}

    def check_issue(self, issue: Dict) -> Dict:
        """检查单个 Issue。"""
        labels = issue.get('labels', [])
        
        # 识别类型
        issue_type = None
        if "type::bug" in labels: issue_type = "bug"
        elif "type::feature" in labels: issue_type = "feature"
        elif "type::test" in labels: issue_type = "test"
        
        result = {
            "iid": issue['iid'],
            "title": issue['title'],
            "type": issue_type or "Unknown",
            "missing": [],
            "url": issue['web_url']
        }
        
        if not issue_type:
            result["missing"].append("type (Missing or Unknown)")
            return result
            
        # 根据规则检查
        required_categories = self.CHECK_RULES.get(issue_type, [])
        for cat in required_categories:
            pool = self.label_pools.get(cat, set())
            if not any(label in pool for label in labels):
                result["missing"].append(cat)
                
        return result


def main():
    parser = argparse.ArgumentParser(description="GitLab Issue 标签检查工具")
    parser.add_argument("--project-id", type=int, required=True, help="项目 ID")
    parser.add_argument("--auto-fix", action="store_true", help="自动添加 needs-labels 标签和评论")
    parser.add_argument("--report", help="保存 CSV 报告路径")
    
    args = parser.parse_args()
    
    client = GitLabClient(Config.GITLAB_URL, Config.GITLAB_PRIVATE_TOKEN)
    checker = IssueLabelChecker(client)
    
    logger.info(f"正在获取项目 {args.project_id} 的打开状态 Issue...")
    issues = list(client.get_project_issues(args.project_id))
    
    results = []
    incomplete = []
    
    for issue in issues:
        res = checker.check_issue(issue)
        results.append(res)
        if res["missing"]:
            incomplete.append(res)
            
    logger.info(f"检查完成。总数: {len(results)}, 不完整: {len(incomplete)}")
    
    for item in incomplete:
        logger.warning(f"Issue #{item['iid']} 缺少: {', '.join(item['missing'])}")
        
        if args.auto_fix:
            client.add_issue_label(args.project_id, item['iid'], ["needs-labels"])
            msg = f"⚠️ 标签不完整。缺少类别: {', '.join(item['missing'])}。请根据规范补充。"
            client.add_issue_note(args.project_id, item['iid'], msg)
            
    if args.report and incomplete:
        with open(args.report, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["iid", "title", "type", "missing", "url"])
            writer.writeheader()
            for item in incomplete:
                row = item.copy()
                row['missing'] = ",".join(item['missing'])
                writer.writerow(row)
        logger.info(f"报告已保存至: {args.report}")


if __name__ == "__main__":
    main()
