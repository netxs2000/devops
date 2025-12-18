"""GitLab Issue 标签完整性检查工具

用于检查 GitLab Issue 的标签是否完整，识别缺少必要标签的 Issue。

必要标签定义：
- Bug 类型 Issue 必须包含：
  - type::bug
  - severity::S1/S2/S3/S4
  - priority::P0/P1/P2/P3
  - bug-category::*

使用方式:
    python scripts/check_issue_labels.py --help
    
典型用法示例:
    # 检查所有打开的 Issue
    python scripts/check_issue_labels.py --project-id 123
    
    # 检查所有 Issue（包括已关闭）
    python scripts/check_issue_labels.py --project-id 123 --state all
    
    # 自动添加 needs-labels 标签
    python scripts/check_issue_labels.py --project-id 123 --auto-label
    
    # 生成 CSV 报告
    python scripts/check_issue_labels.py --project-id 123 --output report.csv
"""

import argparse
import sys
import csv
from typing import List, Dict, Set
from datetime import datetime
import requests
from devops_collector.core.config import Config
from devops_collector.core.logger import logger


class IssueLabelChecker:
    """Issue 标签完整性检查器。
    
    Attributes:
        gitlab_url: GitLab 实例 URL
        private_token: GitLab Private Token
        session: requests Session 对象
        required_labels: 必要标签定义
    """
    
    # 必要标签定义
    REQUIRED_LABELS = {
        "bug": {
            "type": ["type::bug"],
            "severity": ["severity::S1", "severity::S2", "severity::S3", "severity::S4"],
            "priority": ["priority::P0", "priority::P1", "priority::P2", "priority::P3"],
            "bug_category": [
                "bug-category::test-script",
                "bug-category::code-error",
                "bug-category::configuration",
                "bug-category::design-defect",
                "bug-category::deployment",
                "bug-category::performance",
                "bug-category::security",
                "bug-category::standard",
                "bug-category::other"
            ],
            "bug_source": [
                "bug-source::production",
                "bug-source::non-production"
            ],
            "province": [
                # 直辖市
                "province::beijing", "province::shanghai", "province::tianjin", "province::chongqing",
                # 省份
                "province::anhui", "province::fujian", "province::gansu", "province::guangdong",
                "province::guizhou", "province::hainan", "province::hebei", "province::henan",
                "province::heilongjiang", "province::hubei", "province::hunan", "province::jilin",
                "province::jiangsu", "province::jiangxi", "province::liaoning", "province::qinghai",
                "province::shaanxi", "province::shandong", "province::shanxi", "province::sichuan",
                "province::yunnan", "province::zhejiang",
                # 自治区
                "province::guangxi", "province::neimenggu", "province::ningxia", 
                "province::xinjiang", "province::xizang",
                # 全国
                "province::nationwide"
            ]
        },
        "feature": {
            "type": ["type::feature"],
            "priority": ["priority::P0", "priority::P1", "priority::P2", "priority::P3"]
        },
        "test": {
            "type": ["type::test"],
            "priority": ["priority::P0", "priority::P1", "priority::P2", "priority::P3"]
        }
    }
    
    def __init__(self, gitlab_url: str, private_token: str):
        """初始化检查器。
        
        Args:
            gitlab_url: GitLab 实例 URL
            private_token: GitLab Private Token
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        self.session = requests.Session()
        self.session.headers.update({
            "PRIVATE-TOKEN": private_token,
            "Content-Type": "application/json"
        })
    
    def get_issues(self, project_id: int, state: str = "opened") -> List[Dict]:
        """获取项目的 Issues。
        
        Args:
            project_id: 项目 ID
            state: Issue 状态 (opened/closed/all)
            
        Returns:
            Issue 列表
        """
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues"
        params = {
            "state": state,
            "per_page": 100,
            "page": 1
        }
        
        all_issues = []
        
        while True:
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                issues = response.json()
                if not issues:
                    break
                
                all_issues.extend(issues)
                
                # 检查是否还有下一页
                if 'x-next-page' not in response.headers or not response.headers['x-next-page']:
                    break
                
                params['page'] += 1
                
            except Exception as e:
                logger.error(f"获取 Issues 失败: {e}")
                break
        
        return all_issues
    
    def check_issue_labels(self, issue: Dict) -> Dict:
        """检查单个 Issue 的标签完整性。
        
        Args:
            issue: Issue 对象
            
        Returns:
            检查结果字典
        """
        labels = issue.get('labels', [])
        issue_type = self._detect_issue_type(labels)
        
        result = {
            "issue_id": issue['id'],
            "issue_iid": issue['iid'],
            "title": issue['title'],
            "state": issue['state'],
            "labels": labels,
            "issue_type": issue_type,
            "missing_labels": [],
            "is_complete": True,
            "web_url": issue['web_url']
        }
        
        if not issue_type:
            result["missing_labels"].append("type (未识别类型)")
            result["is_complete"] = False
            return result
        
        # 检查必要标签
        required = self.REQUIRED_LABELS.get(issue_type, {})
        
        for category, valid_labels in required.items():
            has_label = any(label in labels for label in valid_labels)
            if not has_label:
                result["missing_labels"].append(category)
                result["is_complete"] = False
        
        return result
    
    def _detect_issue_type(self, labels: List[str]) -> str:
        """检测 Issue 类型。
        
        Args:
            labels: 标签列表
            
        Returns:
            Issue 类型 (bug/feature/None)
        """
        if "type::bug" in labels:
            return "bug"
        elif "type::feature" in labels:
            return "feature"
        elif "type::test" in labels:
            return "test"
        return None
    
    def add_needs_labels_tag(self, project_id: int, issue_iid: int) -> bool:
        """为 Issue 添加 needs-labels 标签。
        
        Args:
            project_id: 项目 ID
            issue_iid: Issue IID
            
        Returns:
            是否添加成功
        """
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}"
        data = {
            "add_labels": "needs-labels"
        }
        
        try:
            response = self.session.put(url, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"添加 needs-labels 标签失败 (Issue #{issue_iid}): {e}")
            return False
    
    def add_comment(self, project_id: int, issue_iid: int, missing_labels: List[str]) -> bool:
        """为 Issue 添加提醒评论。
        
        Args:
            project_id: 项目 ID
            issue_iid: Issue IID
            missing_labels: 缺少的标签类别
            
        Returns:
            是否添加成功
        """
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}/notes"
        
        comment = f"""⚠️ **标签不完整提醒**

此 Issue 缺少以下必要标签：
{chr(10).join(f'- ❌ **{label}**' for label in missing_labels)}

请及时补充标签，以便正确分类和处理。

**必要标签说明**:
- **severity**: 严重程度 (S1/S2/S3/S4) - 仅 Bug
- **priority**: 优先级 (P0/P1/P2/P3)
- **bug_category**: Bug 类别 (9 种分类) - 仅 Bug
- **bug_source**: Bug 来源 (production/non-production) - 仅 Bug，用于统计缺陷逃逸率
- **province**: 发现省份 (33 个省份选项) - 仅 Bug，用于按地域统计 Bug 分布

---
*此评论由标签检查工具自动生成*
"""
        
        data = {"body": comment}
        
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"添加评论失败 (Issue #{issue_iid}): {e}")
            return False
    
    def generate_report(
        self, 
        results: List[Dict], 
        output_file: str = None
    ) -> None:
        """生成检查报告。
        
        Args:
            results: 检查结果列表
            output_file: 输出文件路径（CSV 格式）
        """
        incomplete_issues = [r for r in results if not r["is_complete"]]
        
        # 控制台输出
        logger.info(f"\n{'='*80}")
        logger.info(f"标签完整性检查报告")
        logger.info(f"{'='*80}")
        logger.info(f"总 Issue 数: {len(results)}")
        logger.info(f"标签完整: {len(results) - len(incomplete_issues)}")
        logger.info(f"标签不完整: {len(incomplete_issues)}")
        logger.info(f"完整率: {(len(results) - len(incomplete_issues)) / len(results) * 100:.1f}%")
        logger.info(f"{'='*80}\n")
        
        if incomplete_issues:
            logger.info("标签不完整的 Issue 列表:\n")
            for issue in incomplete_issues:
                logger.info(f"Issue #{issue['issue_iid']}: {issue['title']}")
                logger.info(f"  类型: {issue['issue_type'] or '未识别'}")
                logger.info(f"  缺少标签: {', '.join(issue['missing_labels'])}")
                logger.info(f"  链接: {issue['web_url']}")
                logger.info("")
        
        # CSV 输出
        if output_file:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Issue ID', 'Issue IID', '标题', '状态', '类型', 
                    '缺少标签', '链接'
                ])
                
                for issue in incomplete_issues:
                    writer.writerow([
                        issue['issue_id'],
                        issue['issue_iid'],
                        issue['title'],
                        issue['state'],
                        issue['issue_type'] or '未识别',
                        ', '.join(issue['missing_labels']),
                        issue['web_url']
                    ])
            
            logger.info(f"CSV 报告已保存到: {output_file}")


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="GitLab Issue 标签完整性检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检查所有打开的 Issue
  python scripts/check_issue_labels.py --project-id 123
  
  # 检查所有 Issue（包括已关闭）
  python scripts/check_issue_labels.py --project-id 123 --state all
  
  # 自动添加 needs-labels 标签
  python scripts/check_issue_labels.py --project-id 123 --auto-label
  
  # 生成 CSV 报告
  python scripts/check_issue_labels.py --project-id 123 --output report.csv
        """
    )
    
    parser.add_argument(
        "--project-id",
        type=int,
        required=True,
        help="GitLab 项目 ID"
    )
    parser.add_argument(
        "--state",
        choices=["opened", "closed", "all"],
        default="opened",
        help="Issue 状态（默认: opened）"
    )
    parser.add_argument(
        "--auto-label",
        action="store_true",
        help="自动为标签不完整的 Issue 添加 needs-labels 标签"
    )
    parser.add_argument(
        "--auto-comment",
        action="store_true",
        help="自动为标签不完整的 Issue 添加提醒评论"
    )
    parser.add_argument(
        "--output",
        help="输出 CSV 报告文件路径"
    )
    parser.add_argument(
        "--url",
        help="GitLab URL（默认: 从 config.ini 读取）"
    )
    parser.add_argument(
        "--token",
        help="GitLab Private Token（默认: 从 config.ini 读取）"
    )
    
    args = parser.parse_args()
    
    # 获取配置
    gitlab_url = args.url or Config.GITLAB_URL
    private_token = args.token or Config.GITLAB_PRIVATE_TOKEN
    
    if not gitlab_url or not private_token:
        logger.error("错误: 未配置 GitLab URL 或 Token")
        logger.error("请在 config.ini 中配置，或使用 --url 和 --token 参数")
        sys.exit(1)
    
    # 创建检查器
    checker = IssueLabelChecker(gitlab_url, private_token)
    
    # 获取 Issues
    logger.info(f"正在获取项目 {args.project_id} 的 Issues (state={args.state})...")
    issues = checker.get_issues(args.project_id, args.state)
    logger.info(f"共获取 {len(issues)} 个 Issues")
    
    if not issues:
        logger.info("没有找到 Issues")
        return
    
    # 检查标签
    logger.info("正在检查标签完整性...")
    results = []
    for issue in issues:
        result = checker.check_issue_labels(issue)
        results.append(result)
    
    # 自动添加标签和评论
    if args.auto_label or args.auto_comment:
        incomplete_issues = [r for r in results if not r["is_complete"]]
        logger.info(f"\n发现 {len(incomplete_issues)} 个标签不完整的 Issues")
        
        for issue in incomplete_issues:
            if args.auto_label:
                logger.info(f"为 Issue #{issue['issue_iid']} 添加 needs-labels 标签...")
                checker.add_needs_labels_tag(args.project_id, issue['issue_iid'])
            
            if args.auto_comment:
                logger.info(f"为 Issue #{issue['issue_iid']} 添加提醒评论...")
                checker.add_comment(
                    args.project_id, 
                    issue['issue_iid'], 
                    issue['missing_labels']
                )
    
    # 生成报告
    checker.generate_report(results, args.output)


if __name__ == "__main__":
    main()
