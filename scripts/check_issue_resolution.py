"""GitLab Issue 关闭原因检查工具

用于扫描已关闭但未标记关闭原因 (resolution::*) 的 Issue，并自动提醒负责人补充。
支持针对 type::bug 和 type::requirement 类型的议题进行检查。

使用方式:
    python scripts/check_issue_resolution.py --project-id 123 --auto-comment
"""
import argparse
import sys
from typing import List, Dict, Optional
import requests
from devops_collector.core.config import Config
from devops_collector.core.logger import logger

class IssueResolutionChecker:
    """Issue 关闭原因检查器。

    Attributes:
        gitlab_url: GitLab 实例 URL
        private_token: GitLab Private Token
        session: requests Session 对象
    """
    RESOLUTION_PREFIX = 'resolution::'

    def __init__(self, gitlab_url: str, private_token: str):
        """初始化检查器。

        Args:
            gitlab_url: GitLab 实例 URL
            private_token: GitLab Private Token
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        self.session = requests.Session()
        self.session.headers.update({'PRIVATE-TOKEN': private_token, 'Content-Type': 'application/json'})

    def get_closed_issues_without_resolution(self, project_id: int) -> List[Dict]:
        """获取已关闭但没有 resolution 标签的 Issues。

        Args:
            project_id: 项目 ID

        Returns:
            符合要求的 Issue 列表
        """
        url = f'{self.gitlab_url}/api/v4/projects/{project_id}/issues'
        params = {'state': 'closed', 'per_page': 100, 'page': 1}
        target_issues = []
        while True:
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                issues = response.json()
                if not issues:
                    break
                for issue in issues:
                    labels = issue.get('labels', [])
                    if 'type::bug' in labels or 'type::requirement' in labels:
                        has_resolution = any((l.startswith(self.RESOLUTION_PREFIX) for l in labels))
                        if not has_resolution:
                            target_issues.append(issue)
                if 'x-next-page' not in response.headers or not response.headers['x-next-page']:
                    break
                params['page'] += 1
            except Exception as e:
                logger.error(f'获取 Issues 失败: {e}')
                break
        return target_issues

    def has_already_commented(self, project_id: int, issue_iid: int) -> bool:
        """检查脚本是否已经在该 Issue 下发表过提醒。

        Args:
            project_id: 项目 ID
            issue_iid: Issue IID

        Returns:
            是否已评论
        """
        url = f'{self.gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}/notes'
        try:
            response = self.session.get(url)
            response.raise_for_status()
            notes = response.json()
            return any(('⚠️ **关闭原因缺失提醒**' in note.get('body', '') for note in notes))
        except Exception as e:
            logger.error(f'获取 Issue #{issue_iid} 评论失败: {e}')
            return False

    def add_resolution_reminder(self, project_id: int, issue: Dict) -> bool:
        """为 Issue 添加关闭原因提醒评论。

        Args:
            project_id: 项目 ID
            issue: Issue 对象

        Returns:
            是否添加成功
        """
        issue_iid = issue['iid']
        assignee = issue.get('assignee')
        mention = f"@{assignee['username']}" if assignee else '负责人'
        url = f'{self.gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}/notes'
        comment = f'⚠️ **关闭原因缺失提醒**\n\n{mention} 您好，此议题已关闭，但尚未标记**关闭原因 (Resolution)**。\n\n为了便于质量统计和复盘，请通过以下方式补充原因：\n1. 在右侧标签栏手动选择 `resolution::*` 标签。\n2. 或在评论区回复 Quick Action 指令，例如：`/label ~"resolution::done"`。\n\n**可选原因说明**:\n- `resolution::done` - 已完成\n- `resolution::duplicate` - 重复\n- `resolution::postponed` - 延期\n- `resolution::wontfix` - 不做\n- `resolution::by_design` - 设计如此\n\n---\n*此评论由自动化巡检工具生成*\n'
        try:
            response = self.session.post(url, json={'body': comment})
            response.raise_for_status()
            logger.info(f'✓ 已为 Issue #{issue_iid} 添加提醒评论')
            return True
        except Exception as e:
            logger.error(f'为 Issue #{issue_iid} 添加评论失败: {e}')
            return False

def main():
    """主逻辑。"""
    parser = argparse.ArgumentParser(description='GitLab Issue 关闭原因检查工具')
    parser.add_argument('--project-id', type=int, required=True, help='GitLab 项目 ID')
    parser.add_argument('--auto-comment', action='store_true', help='是否自动添加提醒评论')
    parser.add_argument('--url', help='GitLab URL')
    parser.add_argument('--token', help='GitLab Private Token')
    args = parser.parse_args()
    gitlab_url = args.url or Config.GITLAB_URL
    private_token = args.token or Config.GITLAB_PRIVATE_TOKEN
    if not gitlab_url or not private_token:
        logger.error('错误: 未配置 GitLab URL 或 Token')
        sys.exit(1)
    checker = IssueResolutionChecker(gitlab_url, private_token)
    logger.info(f'正在扫描项目 {args.project_id} 中缺失关闭原因的 Issue...')
    issues = checker.get_closed_issues_without_resolution(args.project_id)
    if not issues:
        logger.info('✓ 未发现异常 Issue，所有已关闭需求和缺陷均已标记原因。')
        return
    logger.info(f'发现 {len(issues)} 个 Issue 缺失关闭原因。')
    for issue in issues:
        logger.info(f"异常 Issue: #{issue['iid']} - {issue['title']}")
        if args.auto_comment:
            if not checker.has_already_commented(args.project_id, issue['iid']):
                checker.add_resolution_reminder(args.project_id, issue)
            else:
                logger.info(f"- Issue #{issue['iid']} 已存在提醒评论，跳过。")
if __name__ == '__main__':
    main()