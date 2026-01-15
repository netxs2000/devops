"""GitLab 标签批量创建工具 (重构版)

使用统一的标签库和客户端接口，支持：
- 类型标签 (type::*)
- 优先级标签 (priority::*)
- 严重程度标签 (severity::*)
- 状态标签 (status::*)
"""

import argparse
import sys
from typing import List, Dict

from devops_collector.config import Config
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.gitlab.labels import LABEL_DEFINITIONS
try:
    from devops_collector.core.logger import logger
except ImportError:
    logger = None

# 如果核心包没有 logger，则回退到标准 logging
if not logger:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger('LabelTool')


def create_labels_batch(
    client: GitLabClient,
    target_type: str, 
    target_id: int, 
    label_types: List[str] = None
) -> Dict[str, int]:
    """批量创建标签。"""
    if label_types is None:
        label_types = list(LABEL_DEFINITIONS.keys())
    
    stats = {"success": 0, "failed": 0, "total": 0}
    
    for label_type in label_types:
        if label_type not in LABEL_DEFINITIONS:
            logger.warning(f"未知的标签类型: {label_type}")
            continue
        
        logger.info(f"\n开始创建 {label_type} 类型标签...")
        labels = LABEL_DEFINITIONS[label_type]
        
        for label in labels:
            stats["total"] += 1
            try:
                if target_type == "group":
                    client.create_group_label(target_id, label)
                else:
                    client.create_project_label(target_id, label)
                
                logger.info(f"✓ 创建成功: {label['name']}")
                stats["success"] += 1
            except Exception as e:
                # 兼容处理已存在的情况
                if hasattr(e, 'response') and e.response.status_code == 409:
                    logger.warning(f"- 已存在: {label['name']}")
                    stats["success"] += 1
                else:
                    logger.error(f"✗ 创建失败: {label['name']} - {str(e)}")
                    stats["failed"] += 1
    
    return stats


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="GitLab 标签批量创建工具")
    
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--group-id", type=int, help="GitLab 群组 ID")
    target_group.add_argument("--project-id", type=int, help="GitLab 项目 ID")
    
    parser.add_argument("--types", nargs="+", choices=list(LABEL_DEFINITIONS.keys()), help="标签类型")
    parser.add_argument("--url", help="GitLab URL")
    parser.add_argument("--token", help="GitLab Private Token")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    
    args = parser.parse_args()
    
    gitlab_url = args.url or Config.GITLAB_URL
    private_token = args.token or Config.GITLAB_PRIVATE_TOKEN
    
    if args.dry_run:
        logger.info("\n=== DRY-RUN 预览 ===")
        types = args.types or LABEL_DEFINITIONS.keys()
        for t in types:
            logger.info(f"\n{t}:")
            for l in LABEL_DEFINITIONS[t]:
                logger.info(f"  - {l['name']} ({l['color']})")
        return

    client = GitLabClient(gitlab_url, private_token)
    target_type = "group" if args.group_id else "project"
    target_id = args.group_id or args.project_id
    
    stats = create_labels_batch(client, target_type, target_id, args.types)
    
    logger.info(f"\n=== 完成 ===\n总计: {stats['total']}, 成功: {stats['success']}, 失败: {stats['failed']}")
    if stats['failed'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
