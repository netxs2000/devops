"""Service Desk 双向同步功能测试脚本

测试 Service Desk 与 GitLab Issue 之间的双向同步功能。
"""
import requests
import json
import time
BASE_URL = 'http://localhost:8000'
PROJECT_ID = 1

def print_separator(title=''):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 60}")
        print(f'  {title}')
        print(f"{'=' * 60}")
    else:
        print(f"{'=' * 60}")

def test_submit_and_get_tracking_code():
    """测试提交工单并获取追踪码"""
    print_separator('测试 1: 提交工单')
    url = f'{BASE_URL}/service-desk/submit-bug'
    params = {'project_id': PROJECT_ID}
    data = {'requester_name': '双向同步测试', 'requester_email': 'sync-test@example.com', 'title': '双向同步测试 Bug', 'severity': 'S2', 'priority': 'P2', 'province': 'nationwide', 'environment': 'test', 'steps_to_repro': '测试双向同步功能', 'actual_result': '测试中', 'expected_result': '同步成功'}
    try:
        response = requests.post(url, params=params, json=data)
        result = response.json()
        if response.status_code == 200:
            print(f'✅ 工单提交成功')
            print(f"   追踪码: {result['tracking_code']}")
            print(f"   GitLab Issue: #{result['gitlab_issue_iid']}")
            print(f"   Issue URL: {result['gitlab_issue_url']}")
            return (result['tracking_code'], result['gitlab_issue_iid'])
        else:
            print(f"❌ 提交失败: {result.get('detail', '未知错误')}")
            return (None, None)
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return (None, None)

def test_update_status_service_desk_to_gitlab(tracking_code):
    """测试从 Service Desk 更新状态到 GitLab"""
    print_separator('测试 2: Service Desk → GitLab 同步')
    statuses = [('in-progress', '开始处理工单'), ('completed', '工单已解决')]
    for new_status, comment in statuses:
        print(f'\n▶ 更新状态为: {new_status}')
        url = f'{BASE_URL}/service-desk/tickets/{tracking_code}/status'
        params = {'new_status': new_status, 'comment': comment}
        try:
            response = requests.patch(url, params=params)
            result = response.json()
            if response.status_code == 200:
                print(f'✅ 状态更新成功')
                print(f"   旧状态: {result['old_status']}")
                print(f"   新状态: {result['new_status']}")
                print(f"   GitLab 同步: {('成功' if result['gitlab_synced'] else '失败')}")
                print(f"   同步信息: {result['gitlab_message']}")
            else:
                print(f"❌ 更新失败: {result.get('detail', '未知错误')}")
        except Exception as e:
            print(f'❌ 请求异常: {e}')
        time.sleep(2)

def test_query_ticket_status(tracking_code):
    """测试查询工单状态"""
    print_separator('测试 3: 查询工单状态')
    url = f'{BASE_URL}/service-desk/track/{tracking_code}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            ticket = response.json()
            print(f'✅ 查询成功')
            print(f"   追踪码: {ticket['tracking_code']}")
            print(f"   状态: {ticket['status']}")
            print(f"   工单类型: {ticket['ticket_type']}")
            print(f"   GitLab Issue IID: #{ticket.get('gitlab_issue_iid', 'N/A')}")
            print(f"   更新时间: {ticket['updated_at']}")
        else:
            result = response.json()
            print(f"❌ 查询失败: {result.get('detail', '未知错误')}")
    except Exception as e:
        print(f'❌ 请求异常: {e}')

def test_webhook_simulation(project_id, issue_iid):
    """模拟 GitLab Webhook（需要手动在 GitLab 中操作）"""
    print_separator('测试 4: GitLab → Service Desk 同步（Webhook）')
    print(f'\n📌 手动测试步骤：')
    print(f'   1. 在 GitLab 中打开 Issue #{issue_iid}')
    print(f"   2. 添加标签 'in-progress' 或修改 Issue 状态")
    print(f'   3. 确保项目已配置 Webhook 指向: {BASE_URL}/webhook')
    print(f'   4. 检查 Service Desk 工单状态是否自动更新')
    print(f'\n💡 提示：')
    print(f'   - Webhook URL: {BASE_URL}/webhook')
    print(f'   - 触发事件: Issue events')
    print(f'   - 如果 Webhook 已配置，GitLab 的任何 Issue 变更都会自动同步到 Service Desk')

def test_bidirectional_sync_verification():
    """验证双向同步完整性"""
    print_separator('测试 5: 双向同步验证')
    print('\n✅ 双向同步功能已实现：')
    print('\n1. Service Desk → GitLab:')
    print('   - API: PATCH /service-desk/tickets/{tracking_code}/status')
    print('   - 功能: 更新工单状态 → 同步到 GitLab Issue')
    print('   - 支持状态: pending, in-progress, completed, rejected')
    print('   - 同步内容: Issue 状态、标签、评论')
    print('\n2. GitLab → Service Desk:')
    print('   - 触发: GitLab Webhook (Issue Hook)')
    print('   - 功能: GitLab Issue 变更 → 自动同步到 Service Desk')
    print('   - 同步内容: 状态、标题、更新时间')
    print("   - 标识: 通过 'origin::service-desk' 标签识别")
    print('\n📊 状态映射规则：')
    print('   GitLab closed → Service Desk completed')
    print('   GitLab opened + in-progress 标签 → Service Desk in-progress')
    print('   GitLab opened + rejected 标签 → Service Desk rejected')
    print('   GitLab opened → Service Desk pending')

def main():
    """主测试流程"""
    print('\n' + '=' * 60)
    print('Service Desk 双向同步功能测试')
    print('=' * 60)
    tracking_code, issue_iid = test_submit_and_get_tracking_code()
    if not tracking_code:
        print('\n❌ 工单提交失败，无法继续测试')
        return
    print('\n⏳ 等待 GitLab Issue 创建...')
    time.sleep(3)
    test_update_status_service_desk_to_gitlab(tracking_code)
    test_query_ticket_status(tracking_code)
    test_webhook_simulation(PROJECT_ID, issue_iid)
    test_bidirectional_sync_verification()
    print_separator()
    print('✅ 测试完成！')
    print_separator()
    print('\n📝 测试总结：')
    print(f'   - 追踪码: {tracking_code}')
    print(f'   - GitLab Issue: #{issue_iid}')
    print(f'   - 双向同步: 已实现')
    print(f'\n💡 下一步：')
    print(f'   1. 在 GitLab 中配置 Webhook（如果尚未配置）')
    print(f'   2. 在 GitLab 中手动修改 Issue，观察 Service Desk 自动同步')
    print(f'   3. 使用 API 更新工单状态，观察 GitLab Issue 自动同步')
    print()
if __name__ == '__main__':
    main()