"""GitLab 测试管理核心业务服务层。

该模块封装了“测试管理模块”的所有核心业务逻辑，包括：
1. 测试用例管理 (CRUD, 导入/导出, 克隆)
2. 需求跟踪与覆盖率分析
3. 缺陷提报与根因分析
4. AI 驱动的测试用例生成

遵循“非侵入式二级开发”原则，底层完全依赖 GitLab Issues 进行存储。
"""
import logging
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.models import GitLabProject, GitLabIssue
from devops_collector.models.test_management import GTMTestCase
from devops_collector.plugins.gitlab.parser import GitLabTestParser
from devops_portal import schemas

logger = logging.getLogger(__name__)

class TestManagementService:
    """GitLab 测试管理业务逻辑服务。
    
    负责处理测试用例、需求和缺陷的生命周期管理，并提供高质量的质量看板数据。
    """

    def __init__(self, session: Session, client: GitLabClient):
        """初始化测试管理服务。

        Args:
            session (Session): 数据库会话。
            client (GitLabClient): GitLab API 客户端。
        """
        self.session = session
        self.client = client

    async def get_test_cases(self, db: Session, project_id: int, current_user: Any) -> List[schemas.TestCase]:
        """获取并解析 GitLab 项目中的所有测试用例。"""
        # 这里的实现逻辑是：先从数据库取缓存，如果没有或者需要实时的，从 GitLab 取。
        # 为了简单且符合当前路由逻辑，我们从 GitLab 获取带有 type::test 标签的 Issue。
        try:
            # 使用同步的 generator 转换为列表
            issues = list(self.client.get_project_issues(project_id))
            test_cases = []
            for issue_data in issues:
                labels = issue_data.get('labels', [])
                if 'type::test' in labels:
                    parsed = GitLabTestParser.parse_description(issue_data.get('description', ''))
                    # 转换结果
                    tc = schemas.TestCase(
                        id=issue_data['id'],
                        iid=issue_data['iid'],
                        title=issue_data['title'],
                        priority=parsed['priority'],
                        test_type=parsed['test_type'],
                        requirement_id=str(GitLabTestParser.extract_requirement_id(issue_data.get('description', '')) or ''),
                        pre_conditions=parsed['pre_conditions'].split('\n') if parsed['pre_conditions'] else [],
                        steps=[schemas.TestStep(step_number=s['step_number'], action=s['action'], expected_result=s['expected']) for s in parsed['test_steps']],
                        result=self._determine_result_from_labels(labels),
                        web_url=issue_data['web_url']
                    )
                    test_cases.append(tc)
            return test_cases
        except Exception as e:
            logger.error(f"Failed to get test cases for project {project_id}: {e}")
            raise e

    def _determine_result_from_labels(self, labels: List[str]) -> str:
        """根据标签确定执行结果。"""
        if 'status::passed' in labels: return 'passed'
        if 'status::failed' in labels: return 'failed'
        if 'status::blocked' in labels: return 'blocked'
        return 'pending'

    async def create_test_case(self, project_id: int, title: str, priority: str, test_type: str, 
                               pre_conditions: List[str], steps: List[Dict], 
                               requirement_id: Optional[str] = None, creator: str = "System") -> Dict:
        """在 GitLab 中创建结构化的测试用例 Issue。"""
        # 构建 Markdown 描述
        description = f"## 📝 测试用例详情\n\n"
        description += f"- **用例优先级**: [{priority}]\n"
        description += f"- **测试类型**: [{test_type}]\n"
        if requirement_id:
            description += f"- **关联需求**: # {requirement_id}\n"
        description += f"- **创建者**: {creator}\n\n"
        
        description += f"## 🛠️ 前置条件\n"
        for pre in pre_conditions:
            description += f"- [ ] {pre}\n"
        description += "\n---\n\n"
        
        description += f"## 🚀 执行步骤\n\n"
        for i, step in enumerate(steps):
            num = i + 1
            action = step.get('action', '无')
            expected = step.get('expected', '无')
            description += f"{num}. **操作描述**: {action}\n"
            description += f"   **反馈**: {expected}\n"
        
        data = {
            'title': title,
            'description': description,
            'labels': 'type::test,status::pending'
        }
        
        try:
            return self.client.create_issue(project_id, data)
        except Exception as e:
            logger.error(f"Failed to create test case in GitLab: {e}")
            raise e

    async def execute_test_case(self, project_id: int, issue_iid: int, result: str, executor: str) -> bool:
        """执行用例，更新 GitLab 标签并记录 Note。"""
        try:
            # 1. 更新标签
            issue = self.client.get_project_issue(project_id, issue_iid)
            old_labels = issue.get('labels', [])
            new_labels = [l for l in old_labels if not l.startswith('status::')]
            new_labels.append(f"status::{result}")
            
            self.client.update_issue(project_id, issue_iid, {'labels': ','.join(new_labels)})
            
            # 2. 添加 Note
            note_body = f"🤖 **测试执行记录**\n- **执行结果**: {result.upper()}\n- **执行人**: {executor}\n- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.client.add_issue_note(project_id, issue_iid, note_body)
            
            return True
        except Exception as e:
            logger.error(f"Failed to execute test case #{issue_iid}: {e}")
            return False

    async def list_requirements(self, project_id: int, current_user: Any, db: Session) -> List[schemas.RequirementSummary]:
        """列出项目中的需求 (type::requirement)。"""
        try:
            issues = list(self.client.get_project_issues(project_id))
            reqs = []
            for issue_data in issues:
                labels = issue_data.get('labels', [])
                if 'type::requirement' in labels:
                    review_state = next((l.split('::')[1] for l in labels if l.startswith('review-state::')), 'draft')
                    reqs.append(schemas.RequirementSummary(
                        iid=issue_data['iid'],
                        title=issue_data['title'],
                        state=issue_data['state'],
                        review_state=review_state
                    ))
            return reqs
        except Exception as e:
            logger.error(f"Failed to list requirements: {e}")
            raise e

    async def get_requirement_detail(self, project_id: int, iid: int) -> Optional[schemas.RequirementDetail]:
        """获取需求详情及其关联的测试用例。"""
        try:
            issue_data = self.client.get_project_issue(project_id, iid)
            labels = issue_data.get('labels', [])
            if 'type::requirement' not in labels:
                return None
            
            review_state = next((l.split('::')[1] for l in labels if l.startswith('review-state::')), 'draft')
            
            # 查找关联的测试用例
            # 简化逻辑：遍历项目内所有 Issue，寻找描述中包含关联该需求 ID 的用例
            # 实际生产中应使用数据库查询或 GitLab API 的 linked issues（如果 CE 支持）
            all_issues = list(self.client.get_project_issues(project_id))
            linked_test_cases = []
            for other_issue in all_issues:
                if 'type::test' in other_issue.get('labels', []):
                    desc = other_issue.get('description', '')
                    if f"关联需求]: # {iid}" in desc:
                        parsed = GitLabTestParser.parse_description(desc)
                        linked_test_cases.append(schemas.TestCase(
                            id=other_issue['id'],
                            iid=other_issue['iid'],
                            title=other_issue['title'],
                            priority=parsed['priority'],
                            test_type=parsed['test_type'],
                            requirement_id=str(iid),
                            pre_conditions=parsed['pre_conditions'].split('\n') if parsed['pre_conditions'] else [],
                            steps=[schemas.TestStep(step_number=s['step_number'], action=s['action'], expected_result=s['expected']) for s in parsed['test_steps']],
                            result=self._determine_result_from_labels(other_issue.get('labels', [])),
                            web_url=other_issue['web_url']
                        ))
            
            return schemas.RequirementDetail(
                id=issue_data['id'],
                iid=issue_data['iid'],
                title=issue_data['title'],
                description=issue_data.get('description'),
                state=issue_data['state'],
                review_state=review_state,
                test_cases=linked_test_cases
            )
        except Exception as e:
            logger.error(f"Failed to get requirement detail #{iid}: {e}")
            raise e
            
    async def create_requirement(self, project_id: int, title: str, priority: str, category: str, 
                                 business_value: str, acceptance_criteria: List[str], creator_name: str) -> Dict:
        """创建需求。"""
        description = f"## 🏷️ 需求背景\n{business_value}\n\n"
        description += f"## ✅ 验收标准 (AC)\n"
        for ac in acceptance_criteria:
            description += f"- [ ] {ac}\n"
        description += f"\n-- **创建人**: {creator_name} **优先级**: {priority} **类型**: {category}"
        
        labels = f"type::requirement,priority::{priority},category::{category},review-state::draft"
        data = {
            'title': title,
            'description': description,
            'labels': labels
        }
        return self.client.create_issue(project_id, data)

    async def create_defect(self, project_id: int, title: str, severity: str, priority: str, 
                            category: str, env: str, steps: str, expected: str, actual: str, 
                            reporter_name: str, related_test_case_iid: Optional[int] = None) -> Dict:
        """创建缺陷。"""
        description = f"## 🐞 缺陷描述\n- **严重程度**: {severity}\n- **优先级**: {priority}\n- **环境**: {env}\n\n"
        description += f"## 🔄 复现步骤\n{steps}\n\n"
        description += f"## 🎯 预期结果\n{expected}\n\n"
        description += f"## ❌ 实际结果\n{actual}\n\n"
        if related_test_case_iid:
            description += f"- **关联测试用例**: # {related_test_case_iid}\n"
        description += f"\n-- **报告人**: {reporter_name}"
        
        labels = f"type::bug,severity::{severity},priority::{priority}"
        data = {
            'title': title,
            'description': description,
            'labels': labels
        }
        return self.client.create_issue(project_id, data)

    async def batch_import_test_cases(self, project_id: int, items: List[Dict]) -> Dict:
        """批量导入用例。"""
        results = []
        for item in items:
            try:
                res = await self.create_test_case(
                    project_id=project_id,
                    title=item['title'],
                    priority=item['priority'],
                    test_type=item['test_type'],
                    pre_conditions=item['pre_conditions'],
                    steps=item['steps'],
                    requirement_id=item.get('requirement_id'),
                    creator="Batch Importer"
                )
                results.append(res['iid'])
            except Exception as e:
                logger.error(f"Batch import item failed: {e}")
        return {'status': 'success', 'imported_count': len(results), 'iids': results}

    async def clone_test_cases_from_project(self, source_project_id: int, target_project_id: int) -> Dict:
        """跨项目克隆用例。"""
        # 1. 获取源项目所有用例
        issues = list(self.client.get_project_issues(source_project_id))
        cloned_count = 0
        for issue in issues:
            if 'type::test' in issue.get('labels', []):
                parsed = GitLabTestParser.parse_description(issue.get('description', ''))
                # 创建新 Issue 到目标项目
                await self.create_test_case(
                    project_id=target_project_id,
                    title=issue['title'],
                    priority=parsed['priority'],
                    test_type=parsed['test_type'],
                    pre_conditions=parsed['pre_conditions'].split('\n') if parsed['pre_conditions'] else [],
                    steps=parsed['test_steps'],
                    creator=f"Cloned from P{source_project_id}"
                )
                cloned_count += 1
        return {'status': 'success', 'cloned_count': cloned_count}

    async def generate_steps_from_requirement(self, project_id: int, requirement_iid: int) -> Dict:
        """[AI Placeholder] 根据关联需求的验收标准自动生成测试步骤。"""
        # 实际应通过 AI 模块实现，这里先实现一个逻辑占位
        issue = self.client.get_project_issue(project_id, requirement_iid)
        desc = issue.get('description', '')
        # 简单模拟从 AC 提取步骤
        steps = []
        if '## ✅ 验收标准' in desc:
            ac_content = desc.split('## ✅ 验收标准')[1].split('---')[0].strip()
            for i, line in enumerate(ac_content.split('\n')):
                if line.strip().startswith('- [ ]'):
                    ac_item = line.replace('- [ ]', '').strip()
                    steps.append({'step_number': i+1, 'action': f"验证 {ac_item}", 'expected': f"{ac_item} 表现正常"})
        
        if not steps:
            steps = [{'step_number': 1, 'action': "打开页面并检查基础功能", 'expected': "功能可用"}]
            
        return {'title': f"Verify: {issue['title']}", 'steps': steps}

    def generate_test_code_from_case(self, test_case: schemas.TestCase) -> str:
        """根据测试用例生成代码。"""
        code = f"# Automated Test for Case #{test_case.iid}: {test_case.title}\n"
        code += "import unittest\n\n"
        code += f"class Test{test_case.iid}(unittest.TestCase):\n"
        code += "    def test_flow(self):\n"
        for step in test_case.steps:
            code += f"        # Step {step.step_number}: {step.action}\n"
            code += f"        # Expect: {step.expected_result}\n"
            code += "        pass\n\n"
        return code

    async def run_semantic_deduplication(self, project_id: int, type: str) -> List[Dict]:
        """[AI Placeholder] 语义查重。"""
        return []

    async def analyze_defect_root_cause(self, project_id: int, iid: int) -> Dict:
        """[AI Placeholder] RCA 分析。"""
        return {"analysis": "根据日志初步判定为数据库连接超时导致的 NullPointerException。", "suggestion": "优化连接池配置，增加失败重试。"}

    async def generate_quality_report(self, project_id: int) -> str:
        """生成质量报告 Markdown。"""
        return f"# Quality Report for Project {project_id}\n\nGenerated at: {datetime.now()}"

    async def reject_ticket(self, project_id: int, ticket_iid: int, reason: str, actor_name: str) -> bool:
        """拒绝并关闭工单。"""
        try:
            # 1. 添加拒绝理由评论
            note_body = f"❌ **工单已被拒绝**\n- **理由**: {reason}\n- **操作人**: {actor_name}\n- **状态**: 已关闭"
            self.client.add_issue_note(project_id, ticket_iid, note_body)
            
            # 2. 关闭 Issue
            self.client.update_issue(project_id, ticket_iid, {'state_event': 'close'})
            
            return True
        except Exception as e:
            logger.error(f"Failed to reject ticket #{ticket_iid}: {e}")
            return False

    async def get_mr_summary_stats(self, project_id: int) -> Dict:
        """获取合并请求统计信息。"""
        try:
            mrs = list(self.client.get_project_merge_requests(project_id))
            total = len(mrs)
            merged = sum((1 for mr in mrs if mr['state'] == 'merged'))
            opened = sum((1 for mr in mrs if mr['state'] == 'opened'))
            closed = sum((1 for mr in mrs if mr['state'] == 'closed'))
            
            # 简单计算平均评审时长 (如果是 merged 的)
            durations = []
            for mr in mrs:
                if mr['state'] == 'merged' and mr.get('merged_at') and mr.get('created_at'):
                    start = datetime.fromisoformat(mr['created_at'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(mr['merged_at'].replace('Z', '+00:00'))
                    durations.append((end - start).total_seconds() / 3600.0)
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_count': total,
                'merged_count': merged,
                'opened_count': opened,
                'closed_count': closed,
                'avg_merge_time': avg_duration
            }
        except Exception as e:
            logger.error(f"Failed to get MR summary: {e}")
            return {'total_count': 0, 'merged_count': 0, 'opened_count': 0, 'closed_count': 0, 'avg_merge_time': 0}

    async def get_test_case_detail(self, project_id: int, iid: int) -> Optional[schemas.TestCase]:
        """获取单个用例详情。"""
        try:
            issue_data = self.client.get_project_issue(project_id, iid)
            if 'type::test' not in issue_data.get('labels', []):
                return None
            parsed = GitLabTestParser.parse_description(issue_data.get('description', ''))
            return schemas.TestCase(
                id=issue_data['id'],
                iid=issue_data['iid'],
                title=issue_data['title'],
                priority=parsed['priority'],
                test_type=parsed['test_type'],
                requirement_id=str(GitLabTestParser.extract_requirement_id(issue_data.get('description', '')) or ''),
                pre_conditions=parsed['pre_conditions'].split('\n') if parsed['pre_conditions'] else [],
                steps=[schemas.TestStep(step_number=s['step_number'], action=s['action'], expected_result=s['expected']) for s in parsed['test_steps']],
                result=self._determine_result_from_labels(issue_data.get('labels', [])),
                web_url=issue_data['web_url']
            )
        except Exception:
            return None
