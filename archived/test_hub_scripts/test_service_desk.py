"""Service Desk 功能测试脚本

用于验证 Service Desk 的 Bug 提交、需求提交和工单追踪功能。
"""
import requests
import json
from datetime import datetime
BASE_URL = 'http://localhost:8000'
PROJECT_ID = 1

def test_submit_bug():
    """测试提交 Bug"""
    print('\n' + '=' * 60)
    print('测试 1: 提交缺陷报告')
    print('=' * 60)
    url = f'{BASE_URL}/service-desk/submit-bug'
    params = {'project_id': PROJECT_ID}
    data = {'requester_name': '张三', 'requester_email': 'zhangsan@example.com', 'title': '登录页面无法正常显示', 'severity': 'S2', 'priority': 'P2', 'province': '广东', 'environment': 'production', 'steps_to_repro': '1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮', 'actual_result': '页面显示空白，无法登录', 'expected_result': '应该正常跳转到主页', 'attachments': ['https://example.com/screenshot1.png']}
    try:
        response = requests.post(url, params=params, json=data)
        result = response.json()
        if response.status_code == 200:
            print(f'✅ 提交成功！')
            print(f"   追踪码: {result['tracking_code']}")
            print(f"   GitLab Issue: #{result['gitlab_issue_iid']}")
            print(f"   Issue URL: {result['gitlab_issue_url']}")
            return result['tracking_code']
        else:
            print(f"❌ 提交失败: {result.get('detail', '未知错误')}")
            return None
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return None

def test_submit_requirement():
    """测试提交需求"""
    print('\n' + '=' * 60)
    print('测试 2: 提交需求')
    print('=' * 60)
    url = f'{BASE_URL}/service-desk/submit-requirement'
    params = {'project_id': PROJECT_ID}
    data = {'requester_name': '李四', 'requester_email': 'lisi@example.com', 'title': '增加数据导出功能', 'description': '希望能够将报表数据导出为 Excel 格式，方便离线分析。\n\n具体需求：\n1. 支持导出当前筛选条件下的数据\n2. 支持自定义导出字段\n3. 支持批量导出', 'req_type': 'feature', 'priority': 'P2', 'province': 'nationwide', 'expected_delivery': '2025-02-01'}
    try:
        response = requests.post(url, params=params, json=data)
        result = response.json()
        if response.status_code == 200:
            print(f'✅ 提交成功！')
            print(f"   追踪码: {result['tracking_code']}")
            print(f"   GitLab Issue: #{result['gitlab_issue_iid']}")
            print(f"   Issue URL: {result['gitlab_issue_url']}")
            return result['tracking_code']
        else:
            print(f"❌ 提交失败: {result.get('detail', '未知错误')}")
            return None
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return None

def test_track_ticket(tracking_code):
    """测试追踪工单"""
    print('\n' + '=' * 60)
    print(f'测试 3: 追踪工单 - {tracking_code}')
    print('=' * 60)
    url = f'{BASE_URL}/service-desk/track/{tracking_code}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            ticket = response.json()
            print(f'✅ 查询成功！')
            print(f"   工单类型: {ticket['ticket_type']}")
            print(f"   状态: {ticket['status']}")
            print(f"   提交人: {ticket.get('requester_name', 'N/A')}")
            print(f"   邮箱: {ticket['requester_email']}")
            print(f"   创建时间: {ticket['created_at']}")
            print(f"   GitLab Issue IID: #{ticket.get('gitlab_issue_iid', 'N/A')}")
        elif response.status_code == 404:
            print(f'❌ 工单不存在')
        else:
            result = response.json()
            print(f"❌ 查询失败: {result.get('detail', '未知错误')}")
    except Exception as e:
        print(f'❌ 请求异常: {e}')

def test_list_tickets():
    """测试获取工单列表"""
    print('\n' + '=' * 60)
    print('测试 4: 获取工单列表')
    print('=' * 60)
    url = f'{BASE_URL}/service-desk/tickets'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            tickets = response.json()
            print(f'✅ 查询成功！共 {len(tickets)} 个工单')
            for i, ticket in enumerate(tickets[:5], 1):
                print(f"\n   [{i}] {ticket['tracking_code']}")
                print(f"       类型: {ticket['ticket_type']} | 状态: {ticket['status']}")
                print(f"       提交人: {ticket.get('requester_name', 'N/A')}")
        else:
            result = response.json()
            print(f"❌ 查询失败: {result.get('detail', '未知错误')}")
    except Exception as e:
        print(f'❌ 请求异常: {e}')

def test_parameter_validation():
    """测试参数验证"""
    print('\n' + '=' * 60)
    print('测试 5: 参数验证')
    print('=' * 60)
    url = f'{BASE_URL}/service-desk/submit-bug'
    params = {'project_id': PROJECT_ID}
    data = {'requester_name': '测试用户', 'requester_email': 'test@example.com', 'title': '测试', 'severity': 'INVALID', 'priority': 'P2', 'province': 'nationwide', 'environment': 'test', 'steps_to_repro': '测试', 'actual_result': '测试', 'expected_result': '测试'}
    try:
        response = requests.post(url, params=params, json=data)
        result = response.json()
        if response.status_code == 400:
            print(f'✅ 参数验证正常工作')
            print(f"   错误信息: {result['detail']}")
        else:
            print(f'❌ 参数验证未生效（应该返回 400 错误）')
    except Exception as e:
        print(f'❌ 请求异常: {e}')

def main():
    """主测试流程"""
    print('\n' + '=' * 60)
    print('Service Desk 功能测试')
    print('=' * 60)
    bug_tracking_code = test_submit_bug()
    req_tracking_code = test_submit_requirement()
    if bug_tracking_code:
        test_track_ticket(bug_tracking_code)
    if req_tracking_code:
        test_track_ticket(req_tracking_code)
    test_list_tickets()
    test_parameter_validation()
    print('\n' + '=' * 60)
    print('✅ 所有测试完成！')
    print('=' * 60)
    print('\n📌 下一步操作：')
    print('   1. 在浏览器中打开: http://localhost:8000/static/service_desk.html')
    print('   2. 测试前端界面的各项功能')
    print('   3. 检查 service_desk_tickets.json 文件中的持久化数据')
    print()
if __name__ == '__main__':
    main()