"""P1 部门级数据隔离 - 验证测试脚本

验证场景:
1. 全国权限用户（province='nationwide'）能看到所有省份数据
2. 省份权限用户（province='guangdong'）只能看到广东省数据
3. 未设置province的用户默认为nationwide权限
"""
import requests
import json
from typing import Dict, Any

def test_province_data_isolation():
    """测试省份数据隔离功能"""
    BASE_URL = 'http://localhost:8001'
    PROJECT_ID = 1
    test_users = {'nationwide_admin': {'description': '全国权限管理员', 'expected_provinces': ['nationwide', 'guangdong', 'beijing', 'shanghai'], 'token': 'REPLACE_WITH_ACTUAL_TOKEN'}, 'guangdong_user': {'description': '广东省份用户', 'expected_provinces': ['guangdong'], 'token': 'REPLACE_WITH_ACTUAL_TOKEN'}}
    print('=' * 80)
    print('P1 部门级数据隔离 - 验证测试')
    print('=' * 80)
    for user_type, user_config in test_users.items():
        print(f"\n【测试场景】: {user_config['description']}")
        print(f"预期可见省份: {user_config['expected_provinces']}")
        token = user_config['token']
        if token == 'REPLACE_WITH_ACTUAL_TOKEN':
            print('  [SKIP] 需要配置真实Token才能执行测试')
            continue
        print(f'\n  测试API: /projects/{PROJECT_ID}/province-quality')
        try:
            response = requests.get(f'{BASE_URL}/projects/{PROJECT_ID}/province-quality', headers={'Authorization': f'Bearer {token}'})
            if response.status_code == 200:
                data = response.json()
                provinces = [item['province'] for item in data]
                print(f'    返回的省份: {provinces}')
                print(f"    数据隔离验证: {('✅ PASS' if set(provinces).issubset(set(user_config['expected_provinces'])) else '❌ FAIL')}")
            else:
                print(f'    ❌ API调用失败: {response.status_code} - {response.text}')
        except Exception as e:
            print(f'    ❌ 请求异常: {e}')
        print(f'\n  测试API: /projects/{PROJECT_ID}/province-benchmarking')
        try:
            response = requests.get(f'{BASE_URL}/projects/{PROJECT_ID}/province-benchmarking', headers={'Authorization': f'Bearer {token}'})
            if response.status_code == 200:
                data = response.json()
                provinces = [item['province'] for item in data]
                print(f'    返回的省份: {provinces}')
                print(f"    数据隔离验证: {('✅ PASS' if set(provinces).issubset(set(user_config['expected_provinces'])) else '❌ FAIL')}")
                for item in data:
                    print(f"      - {item['province']}: {item['bug_count']} bugs, 解决率 {item['resolution_rate']}%")
            else:
                print(f'    ❌ API调用失败: {response.status_code} - {response.text}')
        except Exception as e:
            print(f'    ❌ 请求异常: {e}')
    print('\n' + '=' * 80)
    print('测试完成！')
    print('\n【手动验证步骤】:')
    print('1. 启动DevOpsPortal服务: cd devops_portal && uvicorn main:app --reload --port 8001')
    print("2. 注册两个测试用户（一个province='nationwide'，一个province='guangdong'）")
    print('3. 登录获取Token并替换本脚本中的 REPLACE_WITH_ACTUAL_TOKEN')
    print('4. 重新运行本脚本: python scripts/test_province_isolation.py')
    print('=' * 80)
if __name__ == '__main__':
    test_province_data_isolation()