"""GitLab 测试管理核心业务服务层。

该模块封装了“测试管理模块”的所有核心业务逻辑，包括：
1. 测试用例管理 (CRUD, 导入/导出, 克隆)
2. 需求跟踪与覆盖率分析
3. 缺陷提报与根因分析
4. AI 驱动的测试用例生成

遵循“非侵入式二级开发”原则，底层完全依赖 GitLab Issues 进行存储。
"""

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.models.base_models import (
    ProjectMaster,
    ProjectProductRelation,
    TraceabilityLink,
)
from devops_collector.models.test_management import GTMTestCase
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.gitlab.models import GitLabProject
from devops_collector.plugins.gitlab.parser import GitLabTestParser
from devops_collector.plugins.zentao.models import ZenTaoIssue, ZenTaoProduct
from devops_portal import schemas


logger = logging.getLogger(__name__)


class TestManagementService:
    """GitLab 测试管理业务逻辑服务。

    负责处理测试用例、需求和缺陷的生命周期管理，并提供高质量的质量看板数据。
    """

    __test__ = False

    def __init__(self, session: Session, client: GitLabClient):
        """初始化测试管理服务。

        Args:
            session (Session): 数据库会话。
            client (GitLabClient): GitLab API 客户端。
        """
        self.session = session
        self.client = client

    async def get_test_cases(self, db: Session, project_id: int, current_user: Any) -> list[schemas.TestCase]:
        """获取并解析 GitLab 项目中的所有测试用例。"""
        try:
            # 获取项目信息：优先获取 MDM 主项目名称，若未绑定则显示 GitLab 项目名
            project = db.query(GitLabProject).filter(GitLabProject.id == project_id).first()
            project_name = f"P{project_id}"
            if project:
                project_name = project.mdm_project.project_name if project.mdm_project else project.name

            # 获取 Issue 列表
            issues = list(self.client.get_project_issues(project_id))
            return self._parse_issues_to_test_cases(issues, project_name=project_name)
        except Exception as e:
            logger.error(f"Failed to get test cases for project {project_id}: {e}")
            raise e

    def _parse_issues_to_test_cases(
        self, issues: list[dict], project_name: str | None = None
    ) -> list[schemas.TestCase]:
        """将 GitLab Issue 数据解析为测试用例模型。"""
        test_cases = []
        for issue_data in issues:
            labels = issue_data.get("labels", [])
            if "type::test" in labels:
                parsed = GitLabTestParser.parse_description(issue_data.get("description", ""))
                # 转换结果
                tc = schemas.TestCase(
                    id=issue_data["id"],
                    iid=issue_data["iid"],
                    title=issue_data["title"],
                    priority=parsed["priority"],
                    test_type=parsed["test_type"],
                    requirement_id=str(
                        GitLabTestParser.extract_requirement_id(issue_data.get("description", "")) or ""
                    ),
                    pre_conditions=parsed["pre_conditions"].split("\n") if parsed["pre_conditions"] else [],
                    steps=[
                        schemas.TestStep(
                            step_number=s["step_number"], action=s["action"], expected_result=s["expected"]
                        )
                        for s in parsed["test_steps"]
                    ],
                    result=self._determine_result_from_labels(labels),
                    web_url=issue_data["web_url"],
                    project_name=project_name,
                )
                test_cases.append(tc)
        return test_cases

    async def get_aggregated_test_cases(
        self, db: Session, current_user: Any, product_id: str | None = None, org_id: str | None = None
    ) -> list[schemas.TestCase]:
        """按产品或组织聚合获取多个项目下的测试用例。"""
        # 1. 查找目标项目列表
        project_ids = []

        if product_id:
            # 查找关联到该产品的所有项目
            relations = db.query(ProjectProductRelation).filter(ProjectProductRelation.product_id == product_id).all()
            mdm_ids = [r.project_id for r in relations]
            git_projects = db.query(GitLabProject).filter(GitLabProject.mdm_project_id.in_(mdm_ids)).all()
            project_ids = [p.id for p in git_projects]

        elif org_id:
            # 查找该部门下的所有项目
            mdm_projects = db.query(ProjectMaster).filter(ProjectMaster.org_id == org_id).all()
            mdm_ids = [p.project_id for p in mdm_projects]
            git_projects = db.query(GitLabProject).filter(GitLabProject.mdm_project_id.in_(mdm_ids)).all()
            project_ids = [p.id for p in git_projects]

        if not project_ids:
            return []

        # 2. 并行或循环获取各项目的用例
        # 注：GitLab API 访问受限，目前采用顺序循环，后期可优化为并发执行
        all_test_cases = []
        for pid in project_ids:
            try:
                cases = await self.get_test_cases(db, pid, current_user)
                all_test_cases.extend(cases)
            except Exception as e:
                logger.warning(f"Failed to fetch aggregated cases for project {pid}: {e}")
                continue

        return all_test_cases

    async def get_aggregated_requirements(
        self, db: Session, current_user: Any, product_id: str | None = None, org_id: str | None = None
    ) -> list[schemas.TraceabilityMatrixItem]:
        """按产品或组织聚合获取多个项目下的需求及其追溯信息。"""

        # 1. 查找目标 ZenTao 产品列表
        zt_product_ids = set()

        if product_id:
            # 通过 GitLab 项目关联反查
            relations = db.query(ProjectProductRelation).filter(ProjectProductRelation.product_id == product_id).all()
            mdm_ids = [r.project_id for r in relations]
            git_projects = db.query(GitLabProject).filter(GitLabProject.mdm_project_id.in_(mdm_ids)).all()
            gp_ids = [p.id for p in git_projects]

            if gp_ids:
                products_via_git = db.query(ZenTaoProduct.id).filter(ZenTaoProduct.gitlab_project_id.in_(gp_ids)).all()
                zt_product_ids.update([p[0] for p in products_via_git])

            # 直接匹配 ZenTao 产品代码
            # ZenTaoProduct usually doesn't store 'code' matching MDM product_id perfectly, but let's try.
            # If MDM Product ID is 'PRD-001', ZenTao might use name or something else.
            # But the user specifically asked for MDM Product filtering.
            # Assuming 'code' field on ZenTaoProduct matches if available.
            products_via_code = db.query(ZenTaoProduct.id).filter(ZenTaoProduct.code == product_id).all()
            zt_product_ids.update([p[0] for p in products_via_code])

        elif org_id:
            # 通过组织 -> 项目 -> GitLab -> ZenTao
            mdm_projects = db.query(ProjectMaster).filter(ProjectMaster.org_id == org_id).all()
            mdm_ids = [p.project_id for p in mdm_projects]
            git_projects = db.query(GitLabProject).filter(GitLabProject.mdm_project_id.in_(mdm_ids)).all()
            gp_ids = [p.id for p in git_projects]

            if gp_ids:
                products_via_git = db.query(ZenTaoProduct.id).filter(ZenTaoProduct.gitlab_project_id.in_(gp_ids)).all()
                zt_product_ids.update([p[0] for p in products_via_git])

        if not zt_product_ids:
            return []

        # 2. 获取需求 (Story/Feature)
        issues = (
            db.query(ZenTaoIssue)
            .filter(
                ZenTaoIssue.product_id.in_(zt_product_ids), ZenTaoIssue.type.in_(["story", "feature", "requirement"])
            )
            .all()
        )

        # 3. 预加载当前范围内的 Test Cases (避免 N+1 查询)
        # 获取涉及的 GitLab 项目 ID
        relevant_gitlab_project_ids = []
        if gp_ids:
            relevant_gitlab_project_ids = gp_ids
        else:
            # Fallback if we only found by Code
            pass

        gtm_cases = []
        if relevant_gitlab_project_ids:
            gtm_cases = db.query(GTMTestCase).filter(GTMTestCase.project_id.in_(relevant_gitlab_project_ids)).all()

        # 建立用例与需求的内存映射 (基于 #ID 文本匹配)
        req_case_map = {str(i.id): [] for i in issues}

        for case in gtm_cases:
            # 简单匹配: 检查 Title 或 Description 中是否包含 #ReqID
            # 优化: 可以使用正则提取所有 #ID，然后匹配
            text_to_search = (case.title or "") + " " + (case.description or "")
            # Pattern: # + digits
            found_ids = re.findall(r"#(\d+)", text_to_search)
            for fid in found_ids:
                if fid in req_case_map:
                    req_case_map[fid].append(case)

        results = []
        for issue in issues:
            issue_id_str = str(issue.id)

            # 4. 获取关联用例 (从内存映射)
            linked_cases = req_case_map.get(issue_id_str, [])
            api_cases = [
                schemas.TestCase(
                    global_issue_id=c.id,
                    gitlab_issue_iid=c.iid,
                    title=c.title,
                    result="passed" if c.execution_count > 0 else "pending",  # 简化逻辑
                    project_name=c.project.name if c.project else "Unknown",  # 需要确保 relationship loaded
                )
                for c in linked_cases
            ]

            # 5. 获取关联缺陷 (Defects)
            # 策略: 查找关联到了上述 Test Cases 的 Bug，或者直接关联了 Requirement 的 Bug
            # 简化: 目前只查找 TraceabilityLink 中 target_type='bug' 的

            # 6. 获取代码变更 (TraceabilityLink)
            links = db.query(TraceabilityLink).filter(TraceabilityLink.source_id == issue_id_str).all()

            mrs = []
            commits = []
            defects = []

            for l in links:
                if l.target_type == "merge_request":
                    mrs.append(
                        {"id": l.target_id, "iid": l.target_id, "title": f"MR !{l.target_id}", "state": "merged"}
                    )
                elif l.target_type == "commit":
                    commits.append({"short_id": l.target_id[:8], "title": f"Commit {l.target_id[:8]}"})
                elif l.target_type == "bug":  # 假设 TraceabilityMixin 也同步了 Bug 链接
                    defects.append(
                        schemas.BugDetail(
                            iid=int(l.target_id) if l.target_id.isdigit() else 0,
                            title=f"Bug #{l.target_id}",
                            state="opened",
                            created_at=datetime.now(),
                            author="Unknown",
                            web_url="",
                            labels=[],
                        )
                    )

            req_summary = schemas.RequirementSummary(
                iid=issue.id,
                title=issue.title,
                state=issue.status or "open",
                review_state="approved" if issue.status == "active" else "draft",
            )

            results.append(
                schemas.TraceabilityMatrixItem(
                    requirement=req_summary, test_cases=api_cases, defects=defects, merge_requests=mrs, commits=commits
                )
            )

        return results

    def _determine_result_from_labels(self, labels: list[str]) -> str:
        """根据标签确定执行结果。"""
        if "status::passed" in labels:
            return "passed"
        if "status::failed" in labels:
            return "failed"
        if "status::blocked" in labels:
            return "blocked"
        return "pending"

    async def create_test_case(
        self,
        project_id: int,
        title: str,
        priority: str,
        test_type: str,
        pre_conditions: list[str],
        steps: list[dict],
        requirement_id: str | None = None,
        product_id: str | None = None,
        org_id: str | None = None,
        creator: str = "System",
    ) -> dict:
        # 构建符合 TestCase.md 模板规范的 Markdown 描述
        description = f"# 🧪 测试用例: {title}\n\n"
        description += "---\n\n"

        description += "## ℹ️ 基本信息\n"
        description += f"- **用例优先级**: [{priority}]\n"
        description += f"- **测试类型**: [{test_type}]\n"
        if requirement_id:
            description += f"- **关联需求**: # {requirement_id}\n"
        if product_id:
            description += f"- **归属业务产品**: {product_id}\n"
        if org_id:
            description += f"- **所属产品线/部门**: {org_id}\n"
        description += f"- **创建者**: {creator}\n\n"

        description += "---\n\n"
        description += "## 🛠️ 前置条件\n"
        if pre_conditions:
            for pre in pre_conditions:
                description += f"- [ ] {pre}\n"
        else:
            description += "- [ ] 无\n"

        description += "\n---\n\n"
        description += "## 📝 测试步骤\n"
        for i, step in enumerate(steps):
            num = i + 1
            action = step.get("action", "无")
            description += f"{num}. **操作描述**: {action}\n"

        description += "\n---\n\n"
        description += "## ✅ 预期结果\n"
        for i, step in enumerate(steps):
            num = i + 1
            expected = step.get("expected", "无")
            description += f"{num}. **反馈**: {expected}\n"

        description += "\n---\n\n"
        description += "## 🚀 执行记录 (Execution Result)\n"
        description += "> **操作说明**: 测试执行完成后，请在下方勾选结论，并**复制对应指令到评论区执行**。\n\n"
        description += '- [ ] **✅ 通过 (Pass)**: `/label ~"test-result::passed" /close` \n'
        description += "  - (说明: 验证通过，自动标记并关闭该用例)\n"
        description += '- [ ] **❌ 失败 (Fail)**: `/label ~"test-result::failed"` \n'
        description += "  - (说明: 发现缺陷，请同步创建 Bug 并关联本用例 #)\n"
        description += '- [ ] **⚠️ 阻塞 (Blocked)**: `/label ~"test-result::blocked"` \n'
        description += "  - (说明: 环境或前置功能问题导致无法执行)\n\n"
        description += "---\n\n"
        description += "## 📎 测试附件\n[在此上传或粘贴执行截图]\n\n"

        labels = "type::test,status::todo"
        if product_id:
            labels += f",product::{product_id}"
        if org_id:
            labels += f",org::{org_id}"

        data = {"title": title, "description": description, "labels": labels}

        try:
            return self.client.create_issue(project_id, data)
        except Exception as e:
            logger.error(f"Failed to create test case in GitLab: {e}")
            raise e

    async def execute_test_case(
        self, project_id: int, issue_iid: int, result: str, executor: str, report: schemas.ExecutionReport | None = None
    ) -> bool:
        """执行用例，更新 GitLab 标签并记录 Note。"""
        try:
            # 1. 更新标签
            issue = self.client.get_project_issue(project_id, issue_iid)
            old_labels = issue.get("labels", [])
            new_labels = [l for l in old_labels if not l.startswith("status::")]
            new_labels.append(f"status::{result}")

            self.client.update_issue(project_id, issue_iid, {"labels": ",".join(new_labels)})

            # 2. 添加 Note
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            note_body = "🤖 **测试执行记录**\n"
            note_body += f"- **执行结果**: {result.upper()}\n"
            note_body += f"- **执行人**: {executor}\n"
            note_body += f"- **时间**: {timestamp}\n"

            if report:
                if report.environment:
                    note_body += f"- **测试环境**: `{report.environment}`\n"
                if report.comment:
                    note_body += f"\n--- \n**📋 执行备注**:\n{report.comment}\n"

            self.client.add_issue_note(project_id, issue_iid, note_body)

            return True
        except Exception as e:
            logger.error(f"Failed to execute test case #{issue_iid}: {e}")
            return False

    async def list_requirements(
        self, project_id: int, current_user: Any, db: Session
    ) -> list[schemas.RequirementSummary]:
        """列出项目中的需求 (type::requirement)。"""
        try:
            issues = list(self.client.get_project_issues(project_id))
            reqs = []
            for issue_data in issues:
                labels = issue_data.get("labels", [])
                if "type::requirement" in labels:
                    review_state = next((l.split("::")[1] for l in labels if l.startswith("review-state::")), "draft")
                    reqs.append(
                        schemas.RequirementSummary(
                            iid=issue_data["iid"],
                            title=issue_data["title"],
                            state=issue_data["state"],
                            review_state=review_state,
                        )
                    )
            return reqs
        except Exception as e:
            logger.error(f"Failed to list requirements: {e}")
            raise e

    async def get_requirement_detail(self, project_id: int, iid: int) -> schemas.RequirementDetail | None:
        """获取需求详情及其关联的测试用例。"""
        try:
            issue_data = self.client.get_project_issue(project_id, iid)
            labels = issue_data.get("labels", [])
            if "type::requirement" not in labels:
                return None

            review_state = next((l.split("::")[1] for l in labels if l.startswith("review-state::")), "draft")

            # 查找关联的测试用例
            # 简化逻辑：遍历项目内所有 Issue，寻找描述中包含关联该需求 ID 的用例
            # 实际生产中应使用数据库查询或 GitLab API 的 linked issues（如果 CE 支持）
            all_issues = list(self.client.get_project_issues(project_id))
            linked_test_cases = []
            for other_issue in all_issues:
                if "type::test" in other_issue.get("labels", []):
                    desc = other_issue.get("description", "")
                    if f"关联需求]: # {iid}" in desc:
                        parsed = GitLabTestParser.parse_description(desc)
                        linked_test_cases.append(
                            schemas.TestCase(
                                id=other_issue["id"],
                                iid=other_issue["iid"],
                                title=other_issue["title"],
                                priority=parsed["priority"],
                                test_type=parsed["test_type"],
                                requirement_id=str(iid),
                                pre_conditions=parsed["pre_conditions"].split("\n") if parsed["pre_conditions"] else [],
                                steps=[
                                    schemas.TestStep(
                                        step_number=s["step_number"], action=s["action"], expected_result=s["expected"]
                                    )
                                    for s in parsed["test_steps"]
                                ],
                                result=self._determine_result_from_labels(other_issue.get("labels", [])),
                                web_url=other_issue["web_url"],
                            )
                        )

            return schemas.RequirementDetail(
                id=issue_data["id"],
                iid=issue_data["iid"],
                title=issue_data["title"],
                description=issue_data.get("description"),
                state=issue_data["state"],
                review_state=review_state,
                test_cases=linked_test_cases,
            )
        except Exception as e:
            logger.error(f"Failed to get requirement detail #{iid}: {e}")
            raise e

    async def create_requirement(
        self,
        project_id: int,
        title: str,
        priority: str,
        category: str,
        business_value: str,
        acceptance_criteria: list[str],
        creator_name: str,
    ) -> dict:
        """创建需求。"""
        description = f"## 🏷️ 需求背景\n{business_value}\n\n"
        description += "## ✅ 验收标准 (AC)\n"
        for ac in acceptance_criteria:
            description += f"- [ ] {ac}\n"
        description += f"\n-- **创建人**: {creator_name} **优先级**: {priority} **类型**: {category}"

        labels = f"type::requirement,priority::{priority},category::{category},review-state::draft"
        data = {"title": title, "description": description, "labels": labels}
        return self.client.create_issue(project_id, data)

    async def create_defect(
        self,
        project_id: int,
        title: str,
        severity: str,
        priority: str,
        category: str,
        env: str,
        steps: str,
        expected: str,
        actual: str,
        reporter_name: str,
        related_test_case_iid: int | None = None,
    ) -> dict:
        """创建缺陷。"""
        description = f"## 🐞 缺陷描述\n- **严重程度**: {severity}\n- **优先级**: {priority}\n- **环境**: {env}\n\n"
        description += f"## 🔄 复现步骤\n{steps}\n\n"
        description += f"## 🎯 预期结果\n{expected}\n\n"
        description += f"## ❌ 实际结果\n{actual}\n\n"
        if related_test_case_iid:
            description += f"- **关联测试用例**: # {related_test_case_iid}\n"
        description += f"\n-- **报告人**: {reporter_name}"

        labels = f"type::bug,severity::{severity},priority::{priority}"
        data = {"title": title, "description": description, "labels": labels}
        return self.client.create_issue(project_id, data)

    async def batch_import_test_cases(self, project_id: int, items: list[dict]) -> dict:
        """批量导入用例。"""
        results = []
        for item in items:
            try:
                res = await self.create_test_case(
                    project_id=project_id,
                    title=item["title"],
                    priority=item["priority"],
                    test_type=item["test_type"],
                    pre_conditions=item["pre_conditions"],
                    steps=item["steps"],
                    requirement_id=item.get("requirement_id"),
                    creator="Batch Importer",
                )
                results.append(res["iid"])
            except Exception as e:
                logger.error(f"Batch import item failed: {e}")
        return {"status": "success", "imported_count": len(results), "iids": results}

    async def clone_test_cases_from_project(self, source_project_id: int, target_project_id: int) -> dict:
        """跨项目克隆用例。"""
        # 1. 获取源项目所有用例
        issues = list(self.client.get_project_issues(source_project_id))
        cloned_count = 0
        for issue in issues:
            if "type::test" in issue.get("labels", []):
                parsed = GitLabTestParser.parse_description(issue.get("description", ""))
                # 创建新 Issue 到目标项目
                await self.create_test_case(
                    project_id=target_project_id,
                    title=issue["title"],
                    priority=parsed["priority"],
                    test_type=parsed["test_type"],
                    pre_conditions=parsed["pre_conditions"].split("\n") if parsed["pre_conditions"] else [],
                    steps=parsed["test_steps"],
                    creator=f"Cloned from P{source_project_id}",
                )
                cloned_count += 1
        return {"status": "success", "cloned_count": cloned_count}

    async def generate_steps_from_requirement(self, project_id: int, requirement_iid: int) -> dict:
        """[AI Placeholder] 根据关联需求的验收标准自动生成测试步骤。"""
        # 实际应通过 AI 模块实现，这里先实现一个逻辑占位
        issue = self.client.get_project_issue(project_id, requirement_iid)
        desc = issue.get("description", "")
        # 简单模拟从 AC 提取步骤
        steps = []
        if "## ✅ 验收标准" in desc:
            ac_content = desc.split("## ✅ 验收标准")[1].split("---")[0].strip()
            for i, line in enumerate(ac_content.split("\n")):
                if line.strip().startswith("- [ ]"):
                    ac_item = line.replace("- [ ]", "").strip()
                    steps.append({"step_number": i + 1, "action": f"验证 {ac_item}", "expected": f"{ac_item} 表现正常"})

        if not steps:
            steps = [{"step_number": 1, "action": "打开页面并检查基础功能", "expected": "功能可用"}]

        return {"title": f"Verify: {issue['title']}", "steps": steps}

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

    async def run_semantic_deduplication(self, project_id: int, type: str) -> list[dict]:
        """[AI Placeholder] 语义查重。"""
        return []

    async def analyze_defect_root_cause(self, project_id: int, iid: int) -> str:
        """[AI] 分析缺陷根因。"""
        # Placeholder implementation
        return "RCA Analysis pending implementation."

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
            self.client.update_issue(project_id, ticket_iid, {"state_event": "close"})

            return True
        except Exception as e:
            logger.error(f"Failed to reject ticket #{ticket_iid}: {e}")
            return False

    async def get_mr_summary_stats(self, project_id: int) -> dict:
        """获取合并请求统计信息。"""
        try:
            mrs = list(self.client.get_project_merge_requests(project_id))
            total = len(mrs)
            merged = sum(1 for mr in mrs if mr["state"] == "merged")
            opened = sum(1 for mr in mrs if mr["state"] == "opened")
            closed = sum(1 for mr in mrs if mr["state"] == "closed")

            # 简单计算平均评审时长 (如果是 merged 的)
            durations = []
            for mr in mrs:
                if mr["state"] == "merged" and mr.get("merged_at") and mr.get("created_at"):
                    start = datetime.fromisoformat(mr["created_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(mr["merged_at"].replace("Z", "+00:00"))
                    durations.append((end - start).total_seconds() / 3600.0)

            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                "total_count": total,
                "merged_count": merged,
                "opened_count": opened,
                "closed_count": closed,
                "avg_merge_time": avg_duration,
            }
        except Exception as e:
            logger.error(f"Failed to get MR summary: {e}")
            return {"total_count": 0, "merged_count": 0, "opened_count": 0, "closed_count": 0, "avg_merge_time": 0}

    async def get_test_case_detail(self, project_id: int, iid: int) -> schemas.TestCase | None:
        """获取单个用例详情。"""
        try:
            issue_data = self.client.get_project_issue(project_id, iid)
            if "type::test" not in issue_data.get("labels", []):
                return None
            parsed = GitLabTestParser.parse_description(issue_data.get("description", ""))
            return schemas.TestCase(
                id=issue_data["id"],
                iid=issue_data["iid"],
                title=issue_data["title"],
                priority=parsed["priority"],
                test_type=parsed["test_type"],
                requirement_id=str(GitLabTestParser.extract_requirement_id(issue_data.get("description", "")) or ""),
                pre_conditions=parsed["pre_conditions"].split("\n") if parsed["pre_conditions"] else [],
                steps=[
                    schemas.TestStep(step_number=s["step_number"], action=s["action"], expected_result=s["expected"])
                    for s in parsed["test_steps"]
                ],
                result=self._determine_result_from_labels(issue_data.get("labels", [])),
                web_url=issue_data["web_url"],
            )
        except Exception:
            return None
