"""Jenkins 插件验证脚本

测试 JenkinsClient 和 JenkinsWorker 的核心逻辑。
由于没有真实的 Jenkins 环境，此处主要验证代码逻辑和模型关联。
"""
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_mock_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.plugins.jenkins.client import JenkinsClient
from devops_collector.plugins.jenkins.worker import JenkinsWorker
from devops_collector.plugins.jenkins.models import JenkinsJob, JenkinsBuild
from devops_collector.models.base_models import Base

class TestJenkinsPlugin(unittest.TestCase):
    def setUp(self):
        # 模拟数据库会话
        self.session = MagicMock()
        self.client = MagicMock(spec=JenkinsClient)
        self.worker = JenkinsWorker(self.session, self.client)

    def test_sync_all_jobs(self):
        """测试同步所有 Job 逻辑。"""
        # 准备模拟数据
        mock_jobs = [
            {'name': 'job1', 'fullName': 'job1', 'url': 'http://j/job1', 'color': 'blue'},
            {'name': 'job2', 'fullName': 'folder/job2', 'url': 'http://j/folder/job2', 'color': 'red'}
        ]
        self.client.get_jobs.return_value = mock_jobs
        
        # 模拟数据库查询返回空 (即所有 job 都是新创建)
        self.session.query().filter_by().first.return_value = None

        count = self.worker.sync_all_jobs()
        
        self.assertEqual(count, 2)
        self.assertEqual(self.session.add.call_count, 2)
        # 验证是否创建了正确的模型对象
        added_job = self.session.add.call_args_list[0][0][0]
        self.assertIsInstance(added_job, JenkinsJob)
        self.assertEqual(added_job.name, 'job1')

    def test_sync_job_builds(self):
        """测试同步 Job 构建逻辑。"""
        # 准备模拟 Job
        mock_job = JenkinsJob(id=1, full_name='job1', name='job1')
        self.session.query().filter_by().first.side_effect = [mock_job, None] # 第一次查 job, 第二次查 build

        # 准备模拟构建数据
        mock_builds = [{'number': 1, 'url': 'http://j/job1/1'}]
        self.client.get_builds.return_value = mock_builds
        
        mock_build_detail = {
            'number': 1,
            'url': 'http://j/job1/1',
            'result': 'SUCCESS',
            'duration': 1000,
            'timestamp': 1600000000000,
            'building': False,
            'actions': [{'_class': 'hudson.model.CauseAction', 'causes': [{'userName': 'admin'}]}]
        }
        self.client.get_build_details.return_value = mock_build_detail

        count = self.worker.sync_job_builds('job1', limit=1)
        
        self.assertEqual(count, 1)
        self.session.add.assert_called()
        added_build = self.session.add.call_args[0][0]
        self.assertIsInstance(added_build, JenkinsBuild)
        self.assertEqual(added_build.result, 'SUCCESS')
        self.assertEqual(added_build.trigger_user, 'admin')

if __name__ == '__main__':
    unittest.main()
