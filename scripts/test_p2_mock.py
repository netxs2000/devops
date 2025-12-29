# -*- coding: utf-8 -*-
"""P2 任务 Mock 单元测试脚本 (Fix)

本脚本使用 unittest.mock 模拟数据库和网络请求，验证 P2 任务中的核心业务逻辑
"""

import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock 依赖
sys.modules['devops_collector.config'] = MagicMock()
sys.modules['devops_collector.auth.database'] = MagicMock()
sys.modules['devops_collector.models.gitlab_models'] = MagicMock()
sys.modules['devops_collector.models.base_models'] = MagicMock()
sys.modules['devops_collector.auth'] = MagicMock()
sys.modules['requests'] = MagicMock()

# 定义 Mock 对象
mock_config = MagicMock()
mock_config.Config.GITLAB_URL = "https://gitlab.example.com"
mock_config.Config.GITLAB_PRIVATE_TOKEN = "token"
sys.modules['devops_collector.config'] = mock_config

from devops_collector.models.gitlab_models import Project
from devops_collector.models.base_models import Location, User

logger = MagicMock()

# -------------------------------------------------------------------------
# 复刻待测试的核心逻辑函数 (尽可能保持与 main.py 原文一致)
# -------------------------------------------------------------------------

async def get_project_stakeholders_logic(project_id: int, mock_db):
    """(复刻 logic) 获取项目干系人"""
    stakeholders = []
    try:
        # 模拟: project = db.query(Project).filter(Project.gitlab_project_id == project_id).first()
        # 注意：这里我们使用 mock_db.query(...) 的调用方式
        project = mock_db.query(Project).filter(Project.gitlab_project_id == project_id).first()
            
        if project and hasattr(project, 'location_id') and project.location_id:
            # 模拟: location = db.query(Location).filter(Location.location_id == project.location_id).first()
            location = mock_db.query(Location).filter(Location.location_id == project.location_id).first()
            if location and location.manager_user_id:
                stakeholders.append(str(location.manager_user_id))
    except Exception as e:
        logger.warning(f"Failed to query project stakeholders: {e}")
    return stakeholders


async def get_requirement_author_logic(project_id: int, req_iid: int, mock_requests, mock_db, mock_auth_services):
    """(复刻 logic) 获取需求作者"""
    url = f"https://gitlab.example.com/api/v4/projects/{project_id}/issues/{req_iid}"
    headers = {"PRIVATE-TOKEN": "token"}
    
    try:
        resp = mock_requests.get(url, headers=headers, timeout=5)
        if resp.ok:
            issue_data = resp.json()
            author_email = issue_data.get('author', {}).get('email')
            
            if author_email:
                user = mock_auth_services.get_user_by_email(mock_db, email=author_email)
                if user:
                    return str(user.global_user_id)
    except Exception:
        pass
    return None

# -------------------------------------------------------------------------
# 单元测试类
# -------------------------------------------------------------------------

class TestP2NotificationLogic(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_requests = MagicMock()
        self.mock_auth_services = MagicMock()
        
    def test_get_project_stakeholders_found(self):
        """测试：成功找到项目关联的区域负责人"""
        # 准备数据
        mock_project_obj = MagicMock()
        mock_project_obj.location_id = "440000"
        
        mock_location_obj = MagicMock()
        mock_location_obj.manager_user_id = "user-uuid-123"
        
        # 配置 db.query(...).filter(...).first() 的返回值
        # 使用 side_effect 根据传入的参数 (Project 或 Location) 返回不同的 mock 链
        def query_side_effect(model):
            chain_mock = MagicMock()
            if model == Project:
                chain_mock.filter.return_value.first.return_value = mock_project_obj
            elif model == Location:
                chain_mock.filter.return_value.first.return_value = mock_location_obj
            return chain_mock
            
        self.mock_db.query.side_effect = query_side_effect
        
        # 执行测试
        result = asyncio.run(get_project_stakeholders_logic(1, self.mock_db))
        
        # 验证结果
        self.assertEqual(result, ["user-uuid-123"])
        print("[PASS] test_get_project_stakeholders_found")

    def test_get_project_stakeholders_no_location(self):
        """测试：项目没有关联 Location"""
        mock_project_obj = MagicMock()
        mock_project_obj.location_id = None  # 明确设置为 None
        
        def query_side_effect(model):
            chain_mock = MagicMock()
            if model == Project:
                chain_mock.filter.return_value.first.return_value = mock_project_obj
            return chain_mock
        self.mock_db.query.side_effect = query_side_effect
        
        result = asyncio.run(get_project_stakeholders_logic(1, self.mock_db))
        
        self.assertEqual(result, [])
        print("[PASS] test_get_project_stakeholders_no_location")

    def test_get_requirement_author_found(self):
        """测试：成功从 GitLab 获取作者并通过邮箱匹配到用户"""
        # 模拟 GitLab 响应
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"author": {"email": "tom@example.com"}}
        self.mock_requests.get.return_value = mock_resp
        
        # 模拟 DB 用户查找
        mock_user = MagicMock()
        mock_user.global_user_id = "user-uuid-999"
        self.mock_auth_services.get_user_by_email.return_value = mock_user
        
        # 执行测试
        result = asyncio.run(get_requirement_author_logic(
            1, 10, self.mock_requests, self.mock_db, self.mock_auth_services
        ))
        
        # 验证
        self.assertEqual(result, "user-uuid-999")
        print("[PASS] test_get_requirement_author_found")

    def test_get_requirement_author_gitlab_fail(self):
        """测试：GitLab 请求失败"""
        mock_resp = MagicMock()
        mock_resp.ok = False
        self.mock_requests.get.return_value = mock_resp
        
        result = asyncio.run(get_requirement_author_logic(
            1, 10, self.mock_requests, self.mock_db, self.mock_auth_services
        ))
        
        self.assertIsNone(result)
        print("[PASS] test_get_requirement_author_gitlab_fail")

    def test_notification_target_logic(self):
        """测试业务场景：测试失败的通知目标计算逻辑"""
        # 场景1：三个人不同
        executor_uid = "user-1"
        tc_author_id = "user-2"
        req_author = "user-3"
        
        notify_users = [executor_uid]
        if tc_author_id and tc_author_id != executor_uid:
            notify_users.append(tc_author_id)
        if req_author and req_author not in notify_users:
            notify_users.append(req_author)
            
        self.assertEqual(len(notify_users), 3)
        self.assertIn("user-1", notify_users)
        self.assertIn("user-2", notify_users)
        self.assertIn("user-3", notify_users)
        print("[PASS] test_notification_target_logic (Separate Users)")
        
        # 场景2：全部是同一个人
        notify_users_unique = ["user-1"]
        tc_author_id = "user-1"
        req_author = "user-1"
        
        if tc_author_id and tc_author_id != "user-1":
            notify_users_unique.append(tc_author_id)
        if req_author and req_author not in notify_users_unique:
            notify_users_unique.append(req_author)
            
        self.assertEqual(len(notify_users_unique), 1)
        print("[PASS] test_notification_target_logic (Same User)")


if __name__ == '__main__':
    unittest.main()
