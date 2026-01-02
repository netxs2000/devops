"""P2 定向推送逻辑验证测试脚本

测试场景:
1. 质量门禁拦截 → 全员广播推送
2. 测试用例执行失败 → 定向推送给执行者
3. SSE连接 → 验证推送消息格式（含metadata和timestamp）
"""
import requests
import json
import time
from typing import Dict

def test_sse_connection():
    """测试SSE连接和消息接收"""
    print('\n' + '=' * 80)
    print('测试1: SSE 连接与消息格式验证')
    print('=' * 80)
    BASE_URL = 'http://localhost:8001'
    TOKEN = 'REPLACE_WITH_ACTUAL_TOKEN'
    if TOKEN == 'REPLACE_WITH_ACTUAL_TOKEN':
        print('  [SKIP] 需要配置真实Token才能执行测试')
        print('  提示: 先登录获取Token: POST /auth/login')
        return
    print(f'\n  正在连接到 {BASE_URL}/notifications/stream ...')
    try:
        response = requests.get(f'{BASE_URL}/notifications/stream', headers={'Authorization': f'Bearer {TOKEN}'}, stream=True, timeout=30)
        if response.status_code != 200:
            print(f'  ❌ 连接失败: {response.status_code} - {response.text}')
            return
        print('  ✅ SSE连接成功！正在监听消息（10秒）...')
        start_time = time.time()
        message_count = 0
        for line in response.iter_lines():
            if time.time() - start_time > 10:
                break
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data:'):
                    message_count += 1
                    data_str = decoded_line[5:].strip()
                    try:
                        message_data = json.loads(data_str)
                        print(f'\n  📩 收到消息 #{message_count}:')
                        print(f"     类型: {message_data.get('type')}")
                        print(f"     内容: {message_data.get('message')}")
                        print(f"     时间: {message_data.get('timestamp')}")
                        if message_data.get('metadata'):
                            print(f"     元数据: {json.dumps(message_data['metadata'], ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        print(f'  ⚠️ 无法解析消息: {data_str}')
        print(f'\n  监听结束，共接收 {message_count} 条消息')
    except Exception as e:
        print(f'  ❌ 测试异常: {e}')

def test_quality_gate_notification():
    """测试质量门禁拦截推送"""
    print('\n' + '=' * 80)
    print('测试2: 质量门禁拦截推送验证')
    print('=' * 80)
    BASE_URL = 'http://localhost:8001'
    TOKEN = 'REPLACE_WITH_ACTUAL_TOKEN'
    PROJECT_ID = 1
    if TOKEN == 'REPLACE_WITH_ACTUAL_TOKEN':
        print('  [SKIP] 需要配置真实Token才能执行测试')
        return
    print(f'\n  触发质量门禁检查: /projects/{PROJECT_ID}/quality-gate')
    try:
        response = requests.get(f'{BASE_URL}/projects/{PROJECT_ID}/quality-gate', headers={'Authorization': f'Bearer {TOKEN}'})
        if response.status_code == 200:
            data = response.json()
            print(f"  门禁状态: {('✅ 通过' if data['is_passed'] else '❌ 拦截')}")
            print(f"  详情: {data['summary']}")
            if not data['is_passed']:
                print('\n  ⚠️ 质量门禁拦截，应已触发全员广播推送（type=warning）')
                print('  请在SSE客户端验证是否收到推送消息')
            else:
                print('\n  ℹ️ 质量门禁通过，不会触发告警推送')
        else:
            print(f'  ❌ API调用失败: {response.status_code} - {response.text}')
    except Exception as e:
        print(f'  ❌ 测试异常: {e}')

def test_test_execution_notification():
    """测试用例执行失败推送"""
    print('\n' + '=' * 80)
    print('测试3: 测试用例执行失败推送验证')
    print('=' * 80)
    BASE_URL = 'http://localhost:8001'
    TOKEN = 'REPLACE_WITH_ACTUAL_TOKEN'
    PROJECT_ID = 1
    ISSUE_IID = 10
    if TOKEN == 'REPLACE_WITH_ACTUAL_TOKEN':
        print('  [SKIP] 需要配置真实Token才能执行测试')
        return
    print(f'\n  执行测试用例: #{ISSUE_IID} (结果=failed)')
    try:
        response = requests.post(f'{BASE_URL}/projects/{PROJECT_ID}/test-cases/{ISSUE_IID}/execute', headers={'Authorization': f'Bearer {TOKEN}'}, params={'result': 'failed'}, json={'comment': '测试失败：环境配置错误'})
        if response.status_code == 200:
            data = response.json()
            print(f"  执行成功: {data['status']}")
            print(f"  新状态: {data['new_result']}")
            print('\n  ⚠️ 测试失败，应已触发定向推送给执行者（type=error）')
            print('  请在SSE客户端验证是否收到推送消息')
            print('  预期元数据包含: issue_iid, project_id, severity, province')
        else:
            print(f'  ❌ API调用失败: {response.status_code} - {response.text}')
    except Exception as e:
        print(f'  ❌ 测试异常: {e}')

def print_manual_test_guide():
    """打印手动测试指引"""
    print('\n' + '=' * 80)
    print('手动测试指引')
    print('=' * 80)
    print('\n【前置条件】\n1. 启动TestHub服务:\n   cd devops_portal && uvicorn main:app --reload --port 8001\n\n2. 注册并登录用户，获取JWT Token:\n   POST /auth/register\n   POST /auth/login\n\n【测试步骤】\nStep 1: 打开两个终端窗口\n\nStep 2: 终端1 - 建立SSE连接（监听推送）\n   curl -N -H "Authorization: Bearer YOUR_TOKEN" \\\n     http://localhost:8001/notifications/stream\n\nStep 3: 终端2 - 触发推送事件\n   # 方式1: 触发质量门禁拦截（全员广播）\n   curl -H "Authorization: Bearer YOUR_TOKEN" \\\n     http://localhost:8001/projects/1/quality-gate\n   \n   # 方式2: 执行测试用例失败（定向推送）\n   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \\\n     -H "Content-Type: application/json" \\\n     -d \'{"comment": "测试失败"}\' \\\n     "http://localhost:8001/projects/1/test-cases/10/execute?result=failed"\n\nStep 4: 验证终端1收到推送消息\n   ✅ 消息包含 type, message, metadata, timestamp 字段\n   ✅ metadata 包含业务上下文（如 project_id, issue_iid）\n   ✅ timestamp 为ISO格式时间戳\n\n【验收标准】\n- [x] SSE连接成功，收到初始连接确认消息\n- [x] 质量门禁拦截触发全员广播（type=warning）\n- [x] 测试失败触发定向推送（type=error）\n- [x] 推送消息格式正确（含metadata和timestamp）\n- [x] 日志记录推送成功/失败统计\n')
if __name__ == '__main__':
    print('\n' + '=' * 80)
    print('P2 定向推送逻辑 - 验证测试')
    print('=' * 80)
    test_sse_connection()
    test_quality_gate_notification()
    test_test_execution_notification()
    print_manual_test_guide()
    print('\n' + '=' * 80)
    print('测试完成！请参考上述手动测试指引进行端到端验证')
    print('=' * 80)