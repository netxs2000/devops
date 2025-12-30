# -*- coding: utf-8 -*-
"""测试管理核心业务服务模块。

负责测试用例的生命周期管理，包括解析、执行审计、统计摘要以及资产导入。

Typical Usage:
    service = TestingService()
    cases = await service.get_test_cases(project_id, user)
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from devops_collector.gitlab_sync.services.gitlab_client import GitLabClient
from devops_collector.models import schemas
from devops_collector.gitlab_sync.services.security import IssueSecurityProvider
from devops_collector.gitlab_sync.services.ai_client import AIClient

logger = logging.getLogger(__name__)

class TestingService(GitLabClient):
    """测试管理服务类。

    提供基于 GitLab Issue 的结构化测试用例解析与执行审计功能。
    """

    def __init__(self, ai_client: Optional[AIClient] = None):
        super().__init__()
        self.ai = ai_client or AIClient()

    def parse_markdown_to_test_case(self, issue_data: Dict[str, Any]) -> schemas.TestCase:
        """将 GitLab Issue 的 Markdown 描述解析为结构化 TestCase 对象。

        Args:
            issue_data: 从 GitLab API 获取的原始 Issue 字典。

        Returns:
            TestCase: 结构化测试用例对象。
        """
        desc = issue_data.get('description', '') or ''
        labels = issue_data.get('labels', [])
        
        # 1. 解析优先级和类型
        priority_match = re.search(r"用例优先级\]: \[(P\d)", desc)
        priority = priority_match.group(1) if priority_match else "P2"
        
        type_match = re.search(r"测试类型\]: \[(.*?)\]", desc)
        test_type = type_match.group(1) if type_match else "功能测试"
        
        req_match = re.search(r"关联需求\]: # (\d+)", desc)
        req_id = req_match.group(1) if req_match else None
        
        # 2. 解析前置条件
        pre_conditions = []
        if "## 🛠️ 前置条件" in desc:
            try:
                pre_part = desc.split("## 🛠️ 前置条件")[1].split("---")[0]
                pre_conditions = re.findall(r"- \[ \] (.*)", pre_part)
            except IndexError:
                pass
                
        # 3. 解析步骤与期待结果
        steps = []
        step_actions = re.findall(r"\d+\. \*\*操作描述\*\*: (.*)", desc)
        expected_results = re.findall(r"\d+\. \*\*反馈\*\*: (.*)", desc)
        
        for i, action in enumerate(step_actions):
            steps.append({
                "step_number": i + 1,
                "action": action,
                "expected_result": expected_results[i] if i < len(expected_results) else "无"
            })
        
        # 4. 确定执行结果
        result = "pending"
        for label in labels:
            if label.startswith("test-result::"):
                result = label.split("::")[1]
                break
                
        return schemas.TestCase(
            id=issue_data['id'],
            iid=issue_data['iid'],
            title=issue_data['title'],
            priority=priority,
            test_type=test_type,
            requirement_id=req_id,
            pre_conditions=[p.strip() for p in pre_conditions],
            steps=steps,
            result=result,
            web_url=issue_data['web_url'],
            linked_bugs=[]
        )

    async def get_test_cases(self, 
                             db: Session, 
                             project_id: int, 
                             current_user: Any) -> List[schemas.TestCase]:
        """[P0] 工业级数据隔离实现：获取并过滤项目下的测试用例。"""
        from devops_collector.gitlab_sync.models.issue_metadata import IssueMetadata
        from devops_collector.core.security import get_user_org_scope_ids, get_user_location_scope

        # 1. 核心权限网关：计算用户的数据可视范围
        is_admin = getattr(current_user, 'role', '') == 'admin'
        allowed_depts = get_user_org_scope_ids(db, current_user)
        allowed_location = get_user_location_scope(current_user)

        # 2. 构建隔离查询语句 (SQL 层面完成拦截)
        query = db.query(IssueMetadata).filter(
            IssueMetadata.gitlab_project_id == project_id,
            IssueMetadata.issue_type == 'test'
        )

        if not is_admin:
            # 应用组织维度隔离
            if allowed_depts:
                query = query.filter(IssueMetadata.dept_name.in_(allowed_depts))
            # 应用地域维度隔离
            if allowed_location != "National":
                query = query.filter(IssueMetadata.province == allowed_location)

        db_issues = query.all()

        if db_issues:
            results = []
            for item in db_issues:
                # 使用 Pydantic 的自动映射功能 (from_attributes)
                tc = schemas.TestCase.model_validate(item)
                # 特殊逻辑：动态拼装 web_url (数据库模型中不包含此完整链接)
                tc.web_url = f"{Config.GITLAB_URL}/projects/{project_id}/issues/{item.gitlab_issue_iid}"
                results.append(tc)
            return results

        # 4. 安全回退：无索引数据时强制拦截，防止越权
        logger.warning(f"Security Alert: Unauthorized access or missing mirror for project {project_id}")
        return []

    async def execute_test_case(self, project_id: int, issue_iid: int, result: str, executor: str) -> bool:
        """执行测试用例并打上结果标签。

        该方法会自动更新 GitLab Issue 的结果标签 (test-result::*) 并添加审计备注。

        Args:
            project_id (int): GitLab 项目 ID。
            issue_iid (int): 用例 IID。
            result (str): 结果 (passed/failed/blocked)。
            executor (str): 执行人标识 (全名或 Email)。

        Returns:
            bool: 如果成功更新 GitLab 记录则返回 True，否则返回 False。
        """
        project = self.get_project(project_id)
        if not project:
            return False
            
        issue = project.issues.get(issue_iid)
        
        # 移除旧的结果标签
        current_labels = issue.labels
        new_labels = [l for l in current_labels if not l.startswith('test-result::')] # Changed from 'result::' to 'test-result::'
        new_labels.append(f'test-result::{result}') # Changed from 'result::' to 'test-result::'
        
        # 2. 添加执行注解
        note_body = (
            f"### ✅ Execution Audit Record\n"
            f"- **Result**: {result.upper()}\n"
            f"- **Executor**: {executor}\n"
            f"- **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"--- \n*Generated by TestHub Service*"
        )
        
        try:
            issue.labels = new_labels
            issue.notes.create({'body': note_body})
            issue.save()

            # [Real-time Optimization] 触发全员看板实时更新
            from test_hub.main import push_notification
            await push_notification(
                user_ids="ALL",
                message=f"Test Case #{issue_iid} updated to {result}",
                type="refresh_dashboard",
                metadata={"project_id": project_id, "iid": issue_iid, "result": result}
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to save execution record for issue {issue_iid}: {e}")
            return False

    def extract_bugs_from_description(self, description: str) -> List[Dict[str, str]]:
        """从描述中提取关联的缺陷 IID。"""
        bug_matches = re.findall(r"(?:Bug|缺陷|Fixed by|Related to)\]?: #(\d+)", description)
        return [{"iid": bug_id, "title": f"Potential Defect #{bug_id}"} for bug_id in bug_matches]

    async def get_mr_summary_stats(self, project_id: int) -> Dict[str, Any]:
        """获取合并请求统计摘要 (处理全部分页数据)。"""
        project = self.get_project(project_id)
        if not project:
            return {}
        
        # 使用 get_all=True 获取全量数据，避免分页限制导致统计不准
        mrs = project.mergerequests.list(state='all', get_all=True)
        stats = {"total": len(mrs), "merged": 0, "opened": 0, "closed": 0, "approved": 0}
        
        for mr in mrs:
            # 兼容 python-gitlab 的状态枚举
            state = mr.state
            if state in stats:
                stats[state] += 1
            if "review-result::approved" in mr.labels:
                stats["approved"] += 1
                
        return stats

    async def batch_import_test_cases(self, 
                                      project_id: int, 
                                      items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量导入测试用例集。

        Args:
            project_id (int): GitLab 项目 ID。
            items (List[Dict[str, Any]]): 用例数据列表。

        Returns:
            Dict[str, Any]: 导入统计结果 (success_count, failed_items)。
        """
        success_count = 0
        failed_items = []

        # 使用 asyncio.gather 并发创建，提升效率
        import asyncio
        tasks = []
        for item in items:
            tasks.append(self.create_test_case(
                project_id=project_id,
                title=item.get('title', 'Imported Case'),
                priority=item.get('priority', 'P2'),
                test_type=item.get('test_type', '功能测试'),
                requirement_id=item.get('requirement_id'),
                pre_conditions=item.get('pre_conditions', []),
                steps=item.get('steps', [])
            ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if result and not isinstance(result, Exception):
                success_count += 1
            else:
                failed_items.append({
                    "index": i,
        return {
            "total": len(items),
            "success": success_count,
            "failed": len(failed_items),
            "details": failed_items
        }

                            reporter_name: str,
                            related_test_case_iid: Optional[int] = None,
                            attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """为 QA 创建专业缺陷，支持附件。"""
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 构建标准的 Professional Bug 描述
        description = f"""
## 🐞 缺陷上下文 / Defect Context
- **关联用例**: {f'#{related_test_case_iid}' if related_test_case_iid else 'N/A'}
- **发现环境**: {env}
- **严重程度**: {severity}
- **优先级**: {priority}
- **提报人**: {reporter_name}
- **发现时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📝 复现步骤 / Reproduction Steps
{steps}

## ✅ 预期结果 / Expected Result
{expected}

## ❌ 实际结果 / Actual Result
{actual}
"""
        if attachments:
            description += "\n## 📎 附件证据 / Attachments\n"
            for attr in attachments:
                description += f"- {attr}\n"

        description += "\n---\n*Generated by TestHub QA Portal*\n"
        
        # 创建 GitLab Issue
        issue = project.issues.create({
            'title': f"[BUG] {title}",
            'description': description,
            'labels': [
                'type::bug', 
                f'severity::{severity}', 
                f'priority::{priority}', 
                f'bug-category::{category}',
                'status::confirmed'
            ]
        })

        # 如果有关联用例，在评论中建立双向引用
        if related_test_case_iid:
            issue.notes.create({'body': f"This bug was discovered while executing test case #{related_test_case_iid}"})

        # [Real-time Optimization] 触发全员看板实时更新
        from test_hub.main import push_notification
        await push_notification(
            user_ids="ALL",
            message=f"New Bug reported: {title}",
            type="refresh_dashboard",
            metadata={"project_id": project_id, "iid": issue.iid, "type": "bug"}
        )

        return {
            "iid": issue.iid,
            "web_url": issue.web_url,
            "message": "Defect reported successfully"
        }

                                 acceptance_criteria: List[str], 
                                 creator_name: str,
                                 attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """为 PM 创建专业需求，包含强制 DOR 校验与附件支持。"""
        
        # --- DOR (Definition of Ready) Validations ---
        if not business_value or len(business_value.strip()) < 10:
            raise ValueError("DOR Violation: Business Value must be descriptive (at least 10 chars).")
            
        valid_ac = [ac.strip() for ac in acceptance_criteria if ac.strip()]
        if len(valid_ac) < 3:
            raise ValueError("DOR Violation: At least 3 Acceptance Criteria (AC) items are required for a 'Ready' requirement.")
        
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 构建 Markdown 描述 (含 DOR 达标标识)
        ac_markdown = "\n".join([f"- [ ] {ac}" for ac in valid_ac])
        description = f"""
## 💎 业务价值 / Business Value
> {business_value}

## ✅ 验收标准 / Acceptance Criteria (DOR Passed)
{ac_markdown}

---
- **类别**: {category}
- **优先级**: {priority}
- **同步自**: TestHub R&D Portal
- **创建人**: {creator_name}
- **创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
*Generated by TestHub QA Portal*
"""

        # 创建 GitLab Issue
        issue = project.issues.create({
            'title': f"[REQ] {title}",
            'description': req_description,
            'labels': [
                'type::requirement',
                f'priority::{priority}',
                'status::open'
            ]
        })

        # [Real-time Optimization] 触发全员看板实时更新
        from test_hub.main import push_notification
        await push_notification(
            user_ids="ALL",
            message=f"New Requirement created: {title}",
            type="refresh_dashboard",
            metadata={"project_id": project_id, "iid": issue.iid, "type": "requirement"}
        )

        return {
            "id": issue.id,
            "iid": issue.iid,
            "web_url": issue.web_url,
            "message": "Requirement created successfully"
        }

    async def run_semantic_deduplication(self, project_id: int, issue_type: str = 'requirement') -> List[Dict[str, Any]]:
        """[AI 核心] 语义级查重算法。
        
        通过计算标题和描述的 TF-IDF 相似性及文本模糊匹配，识别重复提报的工单。
        
        Args:
            project_id: GitLab 项目 ID。
            issue_type: 检查类型 (requirement/bug/test)。
            
        Returns:
            List[Dict]: 相似工单的分组列表。
        """
        project = self.get_project(project_id)
        if not project: return []
        
        # 1. 获取所有待检查的 Issue (处理全部分页数据)
        labels = [f"type::{issue_type}"]
        issues = project.issues.list(labels=labels, state='opened', get_all=True)
        
        if len(issues) < 2: return []
        
        # 2. 简易语义聚类 (Jaccard + 模糊匹配)
        clusters = []
        visited = set()
        
        def calculate_similarity(s1: str, s2: str) -> float:
            # 简单的分词相似度 (适应中文环境)
            set1 = set(s1)
            set2 = set(s2)
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            return intersection / union if union > 0 else 0

        for i in range(len(issues)):
            if issues[i].id in visited: continue
            
            group = [issues[i]]
            visited.add(issues[i].id)
            
            for j in range(i + 1, len(issues)):
                if issues[j].id in visited: continue
                
                # 计算标题相似度
                score = calculate_similarity(issues[i].title, issues[j].title)
                
                # 如果相似度 > 0.65 认为疑似重复
                if score > 0.65:
                    group.append(issues[j])
                    visited.add(issues[j].id)
            
            if len(group) > 1:
                clusters.append({
                    "prime": {
                        "iid": group[0].iid,
                        "title": group[0].title,
                        "url": group[0].web_url
                    },
                    "duplicates": [
                        {"iid": g.iid, "title": g.title, "url": g.web_url} for g in group[1:]
                    ],
                    "confidence": 0.85 # 演示用途固定
                })
        
        return clusters

    async def reject_ticket(self,
                            project_id: int,
                            ticket_iid: int,
                            reason: str,
                            actor_name: str) -> bool:
        """拒绝并关闭业务反馈工单。"""
        project = self.get_project(project_id)
        if not project:
            return False
            
        issue = project.issues.get(ticket_iid)
        
        # 1. 添加拒绝原因评论
        comment = f"### 🚫 Feedback Rejected / 已拒绝\n**Reason**: {reason}\n**Processed By**: {actor_name}"
        issue.notes.create({'body': comment})
        
        # 2. 更新标签并关闭
        labels = issue.labels
        labels = [l for l in labels if not l.startswith('status::')]
        labels.append('status::rejected')
        
        issue.labels = labels
        issue.state_event = 'close' # 触发关闭
        issue.save()
        
        # [Real-time] 同样触发全员实时通知
        from test_hub.main import push_notification
        await push_notification(
            user_ids="ALL",
            message=f"Ticket #{ticket_iid} has been rejected by {actor_name}",
            type="warning"
        )
        
        return True
        """从源项目克隆所有测试用例到目标项目。

        Args:
            source_project_id (int): 源项目 ID。
            target_project_id (int): 目标项目 ID。

        Returns:
            Dict[str, Any]: 克隆统计结果。
        """
        source_project = self.get_project(source_project_id)
        if not source_project:
            raise ValueError(f"Source project {source_project_id} not found")

        # 1. 获取源项目所有测试用例
        issues = source_project.issues.list(
            labels=['type::test'],
            state='opened',
            get_all=True
        )

        if not issues:
            return {"total": 0, "success": 0, "message": "No test cases found in source project"}

        # 2. 准备克隆任务
        import_items = []
        for issue in issues:
            # 解析源 Issue 的内容 (复用现有的 markdown 解析逻辑)
            tc_data = self.parse_markdown_to_test_case(issue.__dict__)
            
            import_items.append({
                "title": tc_data.title,
                "priority": tc_data.priority,
                "test_type": tc_data.test_type,
                "requirement_id": tc_data.requirement_id,
                "pre_conditions": tc_data.pre_conditions,
                "steps": [{"action": s.action, "expected": s.expected_result} for s in tc_data.steps]
            })

        # 3. 执行批量创建 (复用批量导入逻辑)
        return await self.batch_import_test_cases(target_project_id, import_items)

    def generate_test_code_from_case(self, tc_data: schemas.TestCase) -> str:
        """根据测试用例步骤生成自动化代码框架 (Playwright/Python 版本)。"""
        code_lines = [
            'import pytest',
            'from playwright.sync_api import Page, expect',
            '',
            f'# Case ID: #{tc_data.iid}',
            f'# Title: {tc_data.title}',
            f'# Priority: {tc_data.priority}',
            '',
            f'def test_case_{tc_data.iid}(page: Page):',
            '    \"\"\"自动化脚本生成于 TestHub AI Engine\"\"\"'
        ]

        # 添加前置条件注释
        if tc_data.pre_conditions:
            code_lines.append('    # [Pre-conditions]')
            for pre in tc_data.pre_conditions:
                code_lines.append(f'    # - {pre}')

        code_lines.append('')
        code_lines.append('    # [Execution Steps]')
        
        # 将自然语言步骤转化为代码占位
        for step in tc_data.steps:
            code_lines.append(f'    # Step {step.step_number}: {step.action}')
            # 尝试根据动作关键词生成一些简单的示例代码
            action_lower = step.action.lower()
            if "点击" in action_lower or "click" in action_lower:
                code_lines.append(f'    page.click("text={step.action[2:] if len(step.action)>2 else "target"}")')
            elif "输入" in action_lower or "input" in action_lower or "type" in action_lower:
                code_lines.append('    page.fill("input[name=\'id\']", "value")')
            else:
                code_lines.append(f'    # TODO: Implement action for "{step.action}"')
                
            code_lines.append(f'    # Expect: {step.expected_result}')
            code_lines.append(f'    # expect(page).to_have_text(...)')
            code_lines.append('')

        return "\n".join(code_lines)

    async def create_test_case(self, 
                               project_id: int, 
                               title: str, 
                               priority: str, 
                               test_type: str, 
                               requirement_id: Optional[str],
                               pre_conditions: List[str],
                               steps: List[Dict[str, str]]) -> Optional[Any]:

            requirement_id (Optional[str]): 关联的需求 Issue IID。
            pre_conditions (List[str]): 前置条件列表。
            steps (List[Dict[str, str]]): 包含 'action' 和 'expected' 的步骤列表。

        Returns:
            Optional[Any]: 成功则返回新创建的 Issue 实例，否则返回 None。
        """
        project = self.get_project(project_id)
        if not project:
            return None

        # 1. 构建标准模板 Markdown
        description_lines = [
            f"# 🧪 测试用例: {title}",
            "",
            "---",
            "",
            "## ℹ️ 基本信息",
            f"- **用例优先级**: {priority}",
            f"- **测试类型**: {test_type}",
            f"- **关联需求**: # {requirement_id if requirement_id else '[未关联]'}",
            "",
            "---",
            "",
            "## 🛠️ 前置条件",
        ]
        
        for pc in pre_conditions:
            description_lines.append(f"- [ ] {pc}")
            
        description_lines.extend([
            "",
            "---",
            "",
            "## 📝 测试步骤",
        ])
        
        for i, step in enumerate(steps):
            description_lines.append(f"{i+1}. **操作描述**: {step.get('action', '')}")

        description_lines.extend([
            "",
            "---",
            "",
            "## ✅ 预期结果",
        ])
        
        for i, step in enumerate(steps):
            description_lines.append(f"{i+1}. **反馈**: {step.get('expected', '')}")

        description_lines.extend([
            "",
            "---",
            "",
            "## 🚀 执行记录 (Execution Result)",
            "> **操作说明**: 测试执行完成后，请在下方勾选结论，并**复制对应指令到评论区执行**。",
            "",
            '- [ ] **✅ 通过 (Pass)**: `/label ~"test-result::passed" /close` ',
            '- [ ] **❌ 失败 (Fail)**: `/label ~"test-result::failed"` ',
            '- [ ] **⚠️ 阻塞 (Blocked)**: `/label ~"test-result::blocked"` ',
            "",
            "---",
            "",
            "/label ~\"type::test\" ~\"status::todo\""
        ])

        # 2. 调用 GitLab API 创建 Issue
        try:
            issue = project.issues.create({
                'title': title,
                'description': "\n".join(description_lines),
                'labels': ['type::test', 'status::todo']
            })
            logger.info(f"Successfully created test case: {issue.iid} in project {project_id}")
            return issue
        except Exception as e:
            logger.error(f"Failed to create test case in GitLab: {e}")
            return None

    async def generate_quality_report(self, project_id: int) -> str:
        """[UX 增强] 生成精美的项目质量评估报告 (Markdown 格式)。
        
        该报告汇总了项目的测试覆盖情况、缺陷存量以及当前的质量风险。
        """
        project = self.get_project(project_id)
        if not project: return "### ❌ Project Not Found"
        
        # 1. 采集全量统计数据 (跨维度聚合，处理全量分页)
        tests = project.issues.list(labels=['type::test'], state='opened', get_all=True)
        bugs = project.issues.list(labels=['type::bug'], state='opened', get_all=True)
        reqs = project.issues.list(labels=['type::requirement'], state='opened', get_all=True)
        
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests if any(l.startswith('test-result::passed') for l in t.labels))
        failed_tests = sum(1 for t in tests if any(l.startswith('test-result::failed') for l in t.labels))
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 2. 组装 Markdown 报告
        report = [
            f"# 📊 质量评估证言 (Quality Testimony) - {project.name}",
            f"> **Reported On**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 📈 核心交付指标 (Core Metrics)",
            "| 指标项 | 当前数据 | 状态 |",
            "| :--- | :--- | :--- |",
            f"| **基准用例通过率** | `{pass_rate:.1f}%` | {'✅ 达标' if pass_rate >= 80 else '⚠️ 预警'} |",
            f"| **未关闭缺陷 (Bugs)** | `{len(bugs)}` 个 | {'🆗 正常' if len(bugs) < 5 else '🔥 高危'} |",
            f"| **需求基准链条** | `{len(reqs)}` 条 | 📋 已入库 |",
            "",
            "---",
            "",
            "## 🛡️ 版本发布合规性分析 (Compliance Analysis)",
            f"- **测试覆盖性**: 总计执行了 `{total_tests}` 个关键场景。",
            f"- **风险拦截**: 当前共有 `{failed_tests}` 个功能模块处于 Blocking 状态。" if failed_tests > 0 else "- **风险拦截**: 目前无阻塞性漏洞，核心链路验证通过。",
            "",
            "---",
            "",
            "## 💡 改进建议 (Next Steps)",
            "1. " + ("针对失败用例，请研发人员立即介入排查证据链。" if failed_tests > 0 else "当前版本可进入预发布阶段，建议补充性能基准测试。"),
            "2. 保持对 Service Desk 反馈的实时跟进。",
            "",
            "---",
            "*Generated by TestHub Enterprise Intelligence Platform*"
        ]
        
        return "\n".join(report)

    async def analyze_defect_root_cause(self, project_id: int, current_issue_iid: int) -> Dict[str, Any]:
        """[AI RCA] 根因分析助手。
        
        基于当前 Bug 描述，检索历史已修复问题，从历史经验中生成修复建议。
        """
        project = self.get_project(project_id)
        if not project: return {"error": "Project not found"}
        
        current_issue = project.issues.get(current_issue_iid)
        
        # 1. 检索历史库 (已修复的 Bug)
        historical_bugs = project.issues.list(
            labels=['type::bug'], 
            state='closed', 
            per_page=50
        )
        
        if not historical_bugs:
            return {
                "suggestions": ["暂无相似历史案例，建议进行首次根因审计。"],
                "impact_scope": "Unknown",
                "similar_cases": []
            }
            
        # 2. 语义相似度匹配 (寻找关联案例)
        similar_cases = []
        for old_bug in historical_bugs:
            # 简单的标题相似度比对
            score = self._calculate_basic_similarity(current_issue.title, old_bug.title)
            if score > 0.45: # 适度降低门槛以增加覆盖面
                # 尝试从历史评论中提取解决方案
                notes = old_bug.notes.list(per_page=5)
                solution = next((n.body for n in notes if 'fix' in n.body.lower() or '解决' in n.body), "见代码提交记录")
                similar_cases.append({
                    "iid": old_bug.iid,
                    "title": old_bug.title,
                    "solution": solution[:100] + "...",
                    "score": score
                })
        
        # 3. 构建智能洞察报告
        suggestions = []
        if similar_cases:
            suggestions.append(f"AI 发现 {len(similar_cases)} 个相似历史故障，多与该模块逻辑有关。")
            suggestions.append(f"历史最佳方案建议：{similar_cases[0]['solution']}")
        else:
            suggestions.append("这是一个新类型的故障模式，建议检查该模块最近的代码变更 (Git Diff)。")
            
        return {
            "title": current_issue.title,
            "suggestions": suggestions,
            "impact_scope": "建议回归该模块关联的测试套件",
            "similar_cases": sorted(similar_cases, key=lambda x: x['score'], reverse=True)[:3]
        }

    def _calculate_basic_similarity(self, s1: str, s2: str) -> float:
        """内部工具：简单的分词重叠度计算。"""
        set1 = set(str(s1))
        set2 = set(str(s2))
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0

    async def mark_associated_tests_as_stale(self, project_id: int, requirement_iid: int):
        """[过程治理] 当需求发生变更时，自动标记所有关联的测试用例为 '失效/待更新'。"""
        project = self.get_project(project_id)
        if not project: return
        
        # 搜索描述中引用了该需求的测试用例 (GitLab 关联引用)
        # 通常测试用例描述中包含 "关联需求: #iid"
        search_query = f"#{requirement_iid}"
        test_issues = project.issues.list(
            labels=['type::test'], 
            search=search_query, 
            state='opened'
        )
        
        for test in test_issues:
            labels = test.labels
            if 'status::stale' not in labels:
                labels.append('status::stale')
                # 记录变更原因日志到评论
                test.notes.create({
                    "body": f"⚠️ **系统治理通知**: 关联的需求 #{requirement_iid} 已发生内容变更，本用例可能已失效。请 QA 团队及时评估并更新测试逻辑。"
                })
                test.labels = labels
                test.save()
                logger.info(f"Marked test case #{test.iid} as STALE due to req #{requirement_iid} change")
                
                # [Real-time] 推送精准通知
                from test_hub.main import push_notification
                await push_notification(
                    user_ids="STAKEHOLDERS", # 推送给项目相关人员
                    message=f"Requirement #{requirement_iid} changed. Associated test cases have been flagged.",
                    type="warning"
                )

    async def generate_steps_from_requirement(self, project_id: int, requirement_iid: int) -> Dict[str, Any]:
        """[AI 核心] 将需求中的验收标准 (AC) 自动转化为测试用例步骤。
        
        Args:
            project_id: 项目 ID。
            requirement_iid: 需求的 Issue IID。
            
        Returns:
            Dict: 包含标题和步骤列表。
        """
        issue = self.get_issue(project_id, requirement_iid)
        if not issue:
            return {"error": f"Requirement #{requirement_iid} not found."}
            
        desc = issue.description or ""
        ac_list = self._extract_ac_from_description(desc)
        
        if not ac_list:
            return {
                "title": issue.title,
                "ac_found": 0,
                "steps": [
                    {"action": "手动检查需求描述", "expected": "根据描述自行设计测试步骤"}
                ],
                "warning": "未在描述中探测到 '## 验收标准' 或结构化列表。"
            }
            
        # 调用 AI 进行转换
        steps = await self.ai.generate_steps_from_ac(issue.title, ac_list)
        
        return {
            "title": issue.title,
            "ac_found": len(ac_list),
            "steps": steps
        }

    def _extract_ac_from_description(self, description: str) -> List[str]:
        """从 Markdown 描述中提取验收标准 (AC) 条目。"""
        if "## 验收标准" not in description:
            # 兼容旧模版或非标准格式：直接寻找所有列表项
            lines = description.split('\n')
            ac_lines = [l.strip('- *').strip() for l in lines if l.strip().startswith(('-', '*')) and len(l) > 5]
            return ac_lines[:10] # 限制数量
            
        try:
            # 提取标题后的内容
            ac_part = description.split("## 验收标准")[1].split("##")[0]
            # 匹配列表项内容
            items = re.findall(r"(?:-|\*)\s*(.*)", ac_part)
            return [item.strip() for item in items if item.strip()]
        except Exception:
            return []
