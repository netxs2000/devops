"""GitLab 标签批量创建工具

用于批量创建 GitLab 项目或群组的标准化标签体系，包括：
- 类型标签 (type::*)
- 优先级标签 (priority::*)
- 严重程度标签 (severity::*)
- 状态标签 (status::*)

使用方式:
    python scripts/create_gitlab_labels.py --help
    
典型用法示例:
    # 为群组创建标签
    python scripts/create_gitlab_labels.py --group-id 123
    
    # 为项目创建标签
    python scripts/create_gitlab_labels.py --project-id 456
    
    # 只创建特定类型的标签
    python scripts/create_gitlab_labels.py --group-id 123 --types type priority severity
"""

import argparse
import sys
from typing import List, Dict
import requests
from devops_collector.core.config import Config
from devops_collector.core.logger import logger


# 标签定义
LABEL_DEFINITIONS = {
    "type": [
        {
            "name": "type::feature",
            "color": "#428BCA",
            "description": "功能需求 - 新功能开发",
            "priority": 1
        },
        {
            "name": "type::bug",
            "color": "#D9534F",
            "description": "缺陷/Bug - 软件缺陷修复",
            "priority": 2
        },
        {
            "name": "type::test",
            "color": "#795548",
            "description": "测试用例 - 模拟 Test Case 管理",
            "priority": 3
        }
    ],
    
    "test_result": [
        {"name": "test-result::passed", "color": "#2ECC71", "description": "通过 - 测试用例验证成功", "priority": 1},
        {"name": "test-result::failed", "color": "#E74C3C", "description": "失败 - 发现缺陷或功能异常", "priority": 2},
        {"name": "test-result::blocked", "color": "#F39C12", "description": "阻塞 - 由于依赖或环境问题无法执行", "priority": 3}
    ],
    
    "priority": [
        {
            "name": "priority::P0",
            "color": "#FF0000",
            "description": "紧急 - 立即处理 (4小时内)",
            "priority": 1
        },
        {
            "name": "priority::P1",
            "color": "#FF6600",
            "description": "高 - 1-2天内处理",
            "priority": 2
        },
        {
            "name": "priority::P2",
            "color": "#FFCC00",
            "description": "中 - 1周内处理",
            "priority": 3
        },
        {
            "name": "priority::P3",
            "color": "#00CC00",
            "description": "低 - 下个迭代处理",
            "priority": 4
        }
    ],
    
    "severity": [
        {
            "name": "severity::S1",
            "color": "#000000",
            "description": "致命 - 系统崩溃、数据丢失、安全漏洞",
            "priority": 1
        },
        {
            "name": "severity::S2",
            "color": "#CC0000",
            "description": "严重 - 核心功能不可用，无替代方案",
            "priority": 2
        },
        {
            "name": "severity::S3",
            "color": "#FF9900",
            "description": "一般 - 功能异常，有替代方案",
            "priority": 3
        },
        {
            "name": "severity::S4",
            "color": "#FFDD00",
            "description": "轻微 - UI问题、文案错误、小瑕疵",
            "priority": 4
        }
    ],
    
    "status": [
        {
            "name": "status::draft",
            "color": "#BDC3C7",
            "description": "草稿 - 议题正在编写或准备中，尚未正式提交评审或排期",
            "priority": 1
        },
        {
            "name": "status::reviewing",
            "color": "#9B59B6",
            "description": "评审中 - 需求或方案正在进行技术/业务评审",
            "priority": 2
        },
        {
            "name": "status::feedback",
            "color": "#E67E22",
            "description": "修正中 - 评审未通过，需按反馈意见进行修改",
            "priority": 3
        },
        {
            "name": "status::todo",
            "color": "#CCCCCC",
            "description": "待处理 - 已通过入库评审，等待开发排期",
            "priority": 4
        },
        {
            "name": "status::in-progress",
            "color": "#3498DB",
            "description": "进行中 - 开发人员正在处理中",
            "priority": 5
        },
        {
            "name": "status::testing",
            "color": "#F39C12",
            "description": "测试中 - 开发完成，等待测试验证或正在测试",
            "priority": 6
        },
        {
            "name": "status::blocked",
            "color": "#E74C3C",
            "description": "阻塞 - 由于外部因素或依赖问题导致流程中断",
            "priority": 7
        },
        {
            "name": "status::done",
            "color": "#2ECC71",
            "description": "已完成 - 议题已处理完毕并验证通过",
            "priority": 8
        }
    ],
    
    
    "bug_category": [
        {
            "name": "bug-category::test-script",
            "color": "#3498DB",
            "description": "测试脚本",
            "priority": 1
        },
        {
            "name": "bug-category::code-error",
            "color": "#E74C3C",
            "description": "代码错误",
            "priority": 2
        },
        {
            "name": "bug-category::configuration",
            "color": "#F39C12",
            "description": "配置相关",
            "priority": 3
        },
        {
            "name": "bug-category::design-defect",
            "color": "#9B59B6",
            "description": "设计缺陷",
            "priority": 4
        },
        {
            "name": "bug-category::deployment",
            "color": "#E67E22",
            "description": "安装部署",
            "priority": 5
        },
        {
            "name": "bug-category::performance",
            "color": "#2ECC71",
            "description": "性能问题",
            "priority": 6
        },
        {
            "name": "bug-category::security",
            "color": "#34495E",
            "description": "安全相关",
            "priority": 7
        },
        {
            "name": "bug-category::standard",
            "color": "#795548",
            "description": "标准规范",
            "priority": 8
        },
        {
            "name": "bug-category::other",
            "color": "#95A5A6",
            "description": "其他",
            "priority": 9
        }
    ],
    
    "bug_source": [
        {
            "name": "bug-source::production",
            "color": "#E74C3C",
            "description": "生产环境发现",
            "priority": 1
        },
        {
            "name": "bug-source::non-production",
            "color": "#27AE60",
            "description": "非生产环境发现",
            "priority": 2
        }
    ],
    
    "province": [
        # 直辖市
        {"name": "province::beijing", "color": "#E74C3C", "description": "北京", "priority": 1},
        {"name": "province::shanghai", "color": "#3498DB", "description": "上海", "priority": 2},
        {"name": "province::tianjin", "color": "#9B59B6", "description": "天津", "priority": 3},
        {"name": "province::chongqing", "color": "#E67E22", "description": "重庆", "priority": 4},
        
        # 省份（按拼音排序）
        {"name": "province::anhui", "color": "#1ABC9C", "description": "安徽", "priority": 5},
        {"name": "province::fujian", "color": "#16A085", "description": "福建", "priority": 6},
        {"name": "province::gansu", "color": "#27AE60", "description": "甘肃", "priority": 7},
        {"name": "province::guangdong", "color": "#2ECC71", "description": "广东", "priority": 8},
        {"name": "province::guizhou", "color": "#F39C12", "description": "贵州", "priority": 9},
        {"name": "province::hainan", "color": "#F1C40F", "description": "海南", "priority": 10},
        {"name": "province::hebei", "color": "#E67E22", "description": "河北", "priority": 11},
        {"name": "province::henan", "color": "#D35400", "description": "河南", "priority": 12},
        {"name": "province::heilongjiang", "color": "#34495E", "description": "黑龙江", "priority": 13},
        {"name": "province::hubei", "color": "#2C3E50", "description": "湖北", "priority": 14},
        {"name": "province::hunan", "color": "#95A5A6", "description": "湖南", "priority": 15},
        {"name": "province::jilin", "color": "#7F8C8D", "description": "吉林", "priority": 16},
        {"name": "province::jiangsu", "color": "#BDC3C7", "description": "江苏", "priority": 17},
        {"name": "province::jiangxi", "color": "#ECF0F1", "description": "江西", "priority": 18},
        {"name": "province::liaoning", "color": "#8E44AD", "description": "辽宁", "priority": 19},
        {"name": "province::qinghai", "color": "#9B59B6", "description": "青海", "priority": 20},
        {"name": "province::shaanxi", "color": "#C0392B", "description": "陕西", "priority": 21},
        {"name": "province::shandong", "color": "#E74C3C", "description": "山东", "priority": 22},
        {"name": "province::shanxi", "color": "#D35400", "description": "山西", "priority": 23},
        {"name": "province::sichuan", "color": "#E67E22", "description": "四川", "priority": 24},
        {"name": "province::yunnan", "color": "#F1C40F", "description": "云南", "priority": 26},
        {"name": "province::zhejiang", "color": "#16A085", "description": "浙江", "priority": 27},
        
        # 自治区
        {"name": "province::guangxi", "color": "#27AE60", "description": "广西", "priority": 28},
        {"name": "province::neimenggu", "color": "#2ECC71", "description": "内蒙古", "priority": 29},
        {"name": "province::ningxia", "color": "#3498DB", "description": "宁夏", "priority": 30},
        {"name": "province::xinjiang", "color": "#2980B9", "description": "新疆", "priority": 31},
        {"name": "province::xizang", "color": "#1ABC9C", "description": "西藏", "priority": 32},
        
        # 全国
        {"name": "province::nationwide", "color": "#2C3E50", "description": "全国 - 全国性或无法确定省份", "priority": 33}
    ],
    
    "resolution": [
        {
            "name": "resolution::done",
            "color": "#2ECC71",
            "description": "已完成 - 需求/缺陷已按预期实现或修复",
            "priority": 1
        },
        {
            "name": "resolution::duplicate",
            "color": "#95A5A6",
            "description": "重复 - 该问题已在其他 Issue 中处理",
            "priority": 2
        },
        {
            "name": "resolution::postponed",
            "color": "#3498DB",
            "description": "延期 - 经过评估，决定推迟到后续版本处理",
            "priority": 3
        },
        {
            "name": "resolution::wontfix",
            "color": "#E67E22",
            "description": "不做 - 经过评审，决定不实施该需求或不修复该问题",
            "priority": 4
        },
        {
            "name": "resolution::by_design",
            "color": "#9B59B6",
            "description": "设计如此 - 经核实，该现象符合原始设计逻辑",
            "priority": 5
        },
        {
            "name": "resolution::cannot_reproduce",
            "color": "#F1C40F",
            "description": "无法重现 - 开发和测试环境均无法复现该 Bug",
            "priority": 6
        },
        {
            "name": "resolution::as_requirement",
            "color": "#34495E",
            "description": "转为需求 - 经评估该 Bug 实际为新的需求或功能改进",
            "priority": 7
        }
    ],
    
    "requirement_type": [
        {"name": "requirement-type::feature", "color": "#3498DB", "description": "功能 - 新业务功能需求", "priority": 1},
        {"name": "requirement-type::interface", "color": "#9B59B6", "description": "接口 - 接口定义或变更需求", "priority": 2},
        {"name": "requirement-type::performance", "color": "#E67E22", "description": "性能 - 系统性能提升需求", "priority": 3},
        {"name": "requirement-type::safe", "color": "#000000", "description": "安全 - 安全性加固及漏洞修复", "priority": 4},
        {"name": "requirement-type::experience", "color": "#1ABC9C", "description": "体验 - 用户交互体验优化", "priority": 5},
        {"name": "requirement-type::improve", "color": "#27AE60", "description": "改进 - 现有功能的完善与增强", "priority": 6},
        {"name": "requirement-type::other", "color": "#95A5A6", "description": "其他 - 无法归类的其他需求类型", "priority": 7}
    ],
    
    "review_result": [
        {
            "name": "review-result::approved",
            "color": "#2ECC71",
            "description": "评审通过 - 需求准入或代码合并允许",
            "priority": 1
        },
        {
            "name": "review-result::rework",
            "color": "#E67E22",
            "description": "需修正 - 需修改后重新评审",
            "priority": 2
        },
        {
            "name": "review-result::rejected",
            "color": "#D9534F",
            "description": "驳回 - 拒绝此需求或 MR",
            "priority": 3
        }
    ],

    "review_status": [
        {"name": "review::speed-up", "color": "#E74C3C", "description": "催审 - 此 MR 紧急，请优先评审", "priority": 1},
        {"name": "review::ping-pong", "color": "#F39C12", "description": "讨论中 - 评审互动轮次较多", "priority": 2},
        {"name": "review::on-hold", "color": "#95A5A6", "description": "挂起 - 待环境或依赖就绪后再审", "priority": 3}
    ]
}


class GitLabLabelCreator:
    """GitLab 标签创建器。
    
    Attributes:
        gitlab_url: GitLab 实例 URL
        private_token: GitLab Private Token
        session: requests Session 对象
    """
    
    def __init__(self, gitlab_url: str, private_token: str):
        """初始化标签创建器。
        
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
    
    def create_group_label(self, group_id: int, label: Dict) -> bool:
        """为群组创建标签。
        
        Args:
            group_id: 群组 ID
            label: 标签定义字典
            
        Returns:
            是否创建成功
        """
        url = f"{self.gitlab_url}/api/v4/groups/{group_id}/labels"
        
        data = {
            "name": label["name"],
            "color": label["color"],
            "description": label.get("description", ""),
            "priority": label.get("priority")
        }
        
        try:
            response = self.session.post(url, json=data)
            
            if response.status_code == 201:
                logger.info(f"✓ 创建成功: {label['name']}")
                return True
            elif response.status_code == 409:
                logger.warning(f"- 已存在: {label['name']}")
                return True
            else:
                logger.error(f"✗ 创建失败: {label['name']} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 创建失败: {label['name']} - {str(e)}")
            return False
    
    def create_project_label(self, project_id: int, label: Dict) -> bool:
        """为项目创建标签。
        
        Args:
            project_id: 项目 ID
            label: 标签定义字典
            
        Returns:
            是否创建成功
        """
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/labels"
        
        data = {
            "name": label["name"],
            "color": label["color"],
            "description": label.get("description", ""),
            "priority": label.get("priority")
        }
        
        try:
            response = self.session.post(url, json=data)
            
            if response.status_code == 201:
                logger.info(f"✓ 创建成功: {label['name']}")
                return True
            elif response.status_code == 409:
                logger.warning(f"- 已存在: {label['name']}")
                return True
            else:
                logger.error(f"✗ 创建失败: {label['name']} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 创建失败: {label['name']} - {str(e)}")
            return False
    
    def create_labels_batch(
        self, 
        target_type: str, 
        target_id: int, 
        label_types: List[str] = None
    ) -> Dict[str, int]:
        """批量创建标签。
        
        Args:
            target_type: 目标类型 ('group' 或 'project')
            target_id: 目标 ID
            label_types: 要创建的标签类型列表，None 表示全部
            
        Returns:
            统计结果字典 {'success': 成功数, 'failed': 失败数, 'total': 总数}
        """
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
                
                if target_type == "group":
                    success = self.create_group_label(target_id, label)
                else:
                    success = self.create_project_label(target_id, label)
                
                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
        
        return stats


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="GitLab 标签批量创建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 为群组创建所有标签
  python scripts/create_gitlab_labels.py --group-id 123
  
  # 为项目创建所有标签
  python scripts/create_gitlab_labels.py --project-id 456
  
  # 只创建类型和优先级标签
  python scripts/create_gitlab_labels.py --group-id 123 --types type priority
  
  # 使用自定义 GitLab URL 和 Token
  python scripts/create_gitlab_labels.py --group-id 123 --url https://gitlab.example.com --token glpat-xxx
        """
    )
    
    # 目标参数（互斥）
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--group-id",
        type=int,
        help="GitLab 群组 ID（推荐，可跨项目共享标签）"
    )
    target_group.add_argument(
        "--project-id",
        type=int,
        help="GitLab 项目 ID"
    )
    
    # 可选参数
    parser.add_argument(
        "--types",
        nargs="+",
        choices=list(LABEL_DEFINITIONS.keys()),
        help="要创建的标签类型（默认: 全部）"
    )
    parser.add_argument(
        "--url",
        help="GitLab URL（默认: 从 config.ini 读取）"
    )
    parser.add_argument(
        "--token",
        help="GitLab Private Token（默认: 从 config.ini 读取）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将要创建的标签，不实际创建"
    )
    
    args = parser.parse_args()
    
    # 获取配置
    gitlab_url = args.url or Config.GITLAB_URL
    private_token = args.token or Config.GITLAB_PRIVATE_TOKEN
    
    if not gitlab_url or not private_token:
        logger.error("错误: 未配置 GitLab URL 或 Token")
        logger.error("请在 config.ini 中配置，或使用 --url 和 --token 参数")
        sys.exit(1)
    
    # 确定目标类型和 ID
    if args.group_id:
        target_type = "group"
        target_id = args.group_id
        logger.info(f"目标: 群组 ID {target_id}")
    else:
        target_type = "project"
        target_id = args.project_id
        logger.info(f"目标: 项目 ID {target_id}")
    
    # Dry-run 模式
    if args.dry_run:
        logger.info("\n=== DRY-RUN 模式 ===")
        label_types = args.types or list(LABEL_DEFINITIONS.keys())
        
        for label_type in label_types:
            logger.info(f"\n{label_type} 类型标签:")
            for label in LABEL_DEFINITIONS[label_type]:
                logger.info(f"  - {label['name']}: {label['description']}")
        
        logger.info("\n提示: 移除 --dry-run 参数以实际创建标签")
        return
    
    # 创建标签
    creator = GitLabLabelCreator(gitlab_url, private_token)
    
    logger.info(f"\n开始创建标签...")
    stats = creator.create_labels_batch(
        target_type=target_type,
        target_id=target_id,
        label_types=args.types
    )
    
    # 输出统计
    logger.info(f"\n=== 创建完成 ===")
    logger.info(f"总计: {stats['total']} 个标签")
    logger.info(f"成功: {stats['success']} 个")
    logger.info(f"失败: {stats['failed']} 个")
    
    if stats['failed'] > 0:
        logger.warning("\n部分标签创建失败，请检查日志")
        sys.exit(1)
    else:
        logger.info("\n✓ 所有标签创建成功！")


if __name__ == "__main__":
    main()
