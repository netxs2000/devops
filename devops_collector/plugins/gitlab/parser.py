"""GitLab 测试用例 Markdown 解析器。

本模块负责将 GitLab Issue 的 Markdown 描述内容解析为结构化的测试用例数据。
支持解析：优先级、测试类型、关联需求 ID、预置条件以及测试步骤。
"""

import re
from typing import Dict, List, Any, Optional


class GitLabTestParser:
    """GitLab 测试用例内容解析器。
    
    用于处理标记为 type::test 的 GitLab Issue 内容，提取结构化的测试元数据。
    """

    @staticmethod
    def parse_description(description: str) -> Dict[str, Any]:
        """解析 Issue 描述中的结构化 Markdown 内容。
        
        Args:
            description: GitLab Issue 的原始 Markdown 描述字符串。
            
        Returns:
            Dict[str, Any]: 包含解析后字段的字典：
                - priority: 优先级
                - test_type: 测试类型
                - pre_conditions: 预置条件
                - test_steps: 结构化步骤列表
        """
        if not description:
            return {
                "priority": "P2",
                "test_type": "功能测试",
                "pre_conditions": "",
                "test_steps": []
            }

        # 1. 提取优先级
        priority_match = re.search(r"用例优先级\]: \[(P\d)\]", description)
        priority = priority_match.group(1) if priority_match else "P2"

        # 2. 提取测试类型
        type_match = re.search(r"测试类型\]: \[(.*?)\]", description)
        test_type = type_match.group(1) if type_match else "功能测试"

        # 3. 提取预置条件
        pre_conditions = ""
        if "## 🛠️ 前置条件" in description:
            try:
                # 提取前置条件区域内容
                parts = description.split("## 🛠️ 前置条件")
                if len(parts) > 1:
                    pre_content = parts[1].split("---")[0].strip()
                    # 去掉 Markdown 列表符号
                    lines = [line.strip("- [ ] ").strip() for line in pre_content.split("\n") if line.strip()]
                    pre_conditions = "\n".join(lines)
            except Exception:
                pass

        # 4. 提取测试步骤
        test_steps = []
        try:
            # 使用正则表达式匹配结构化的操作描述和反馈结果
            # 格式示例: 1. **操作描述**: 动作内容 \n 2. **反馈**: 期待结果
            step_actions = re.findall(r"\d+\. \*\*操作描述\*\*: (.*)", description)
            expected_results = re.findall(r"\d+\. \*\*反馈\*\*: (.*)", description)

            for i, action in enumerate(step_actions):
                test_steps.append({
                    "step_number": i + 1,
                    "action": action.strip(),
                    "expected": expected_results[i].strip() if i < len(expected_results) else "无"
                })
        except Exception:
            pass

        return {
            "priority": priority,
            "test_type": test_type,
            "pre_conditions": pre_conditions,
            "test_steps": test_steps
        }

    @staticmethod
    def extract_requirement_id(description: str) -> Optional[int]:
        """从描述中提取关联的 Issue ID (需求 ID)。
        
        Args:
            description: 描述内容。
            
        Returns:
            Optional[int]: 关联的 Issue IID，若未找到则返回 None。
        """
        match = re.search(r"关联需求\]: # (\d+)", description)
        return int(match.group(1)) if match else None
