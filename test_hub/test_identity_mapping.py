
import requests
import json
import sys

# 设置 UTF-8 编码
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "admin_secret_token_2025"
TEST_EMAIL = "test_user_mapping@example.com"
PROJECT_ID = 1

def test_identity_mapping_flow():
    print("🚀 开始身份穿透映射全流程测试...")

    # 1. 注册新用户 (使用 JSON Body)
    print("\n[Step 1] 注册新用户...")
    reg_url = f"{BASE_URL}/service-desk/auth/register"
    # 注意：FastAPI 如果没有指定 Body()，默认可能期望 query params。
    # 我们再次确认一下 main.py 中的参数定义。
    reg_params = {
        "email": TEST_EMAIL,
        "name": "测试员A",
        "company": "测试中心",
        "reason": "测试身份映射功能"
    }
    try:
        resp = requests.post(reg_url, params=reg_params)
        print(f"Response: {resp.status_code}, {resp.text}")
    except Exception as e:
        print(f"注册请求异常: {e}")

    # 2. 管理员审批
    print("\n[Step 2] 管理员审批并绑定 GitLab ID (99)...")
    approve_url = f"{BASE_URL}/service-desk/admin/approve-user"
    approve_params = {
        "email": TEST_EMAIL,
        "approved": "true",
        "admin_token": ADMIN_TOKEN,
        "gitlab_user_id": 99
    }
    resp = requests.post(approve_url, params=approve_params)
    print(f"Response: {resp.status_code}, {resp.text}")

    # 3. 用户登录
    print("\n[Step 3] 用户登录 (使用验证码 123456)...")
    requests.post(f"{BASE_URL}/service-desk/auth/request-code", params={"email": TEST_EMAIL})
    
    login_url = f"{BASE_URL}/service-desk/auth/login"
    login_params = {
        "email": TEST_EMAIL,
        "code": 123456
    }
    resp = requests.post(login_url, params=login_params)
    if resp.status_code != 200:
        print(f"❌ 登录失败: {resp.status_code}, {resp.text}")
        return
        
    token = resp.json().get("token")
    print(f"✅ 登录成功, Token: {token}")

    # 4. 提交缺陷 (使用 JSON Body)
    print("\n[Step 4] 提交缺陷并验证身份穿透...")
    bug_url = f"{BASE_URL}/service-desk/submit-bug"
    bug_data = {
        "requester_name": "测试员A",
        "requester_email": TEST_EMAIL,
        "title": "身份穿透测试缺陷",
        "severity": "S2",
        "priority": "P2",
        "province": "nationwide",
        "environment": "test",
        "steps_to_repro": "1. 登录\n2. 点击测试",
        "actual_result": "穿透成功",
        "expected_result": "GitLab 显示 ID 为 99"
    }
    resp = requests.post(f"{bug_url}?project_id={PROJECT_ID}&token={token}", json=bug_data)
    if resp.status_code == 200:
        res_json = resp.json()
        print(f"✅ 缺陷提交成功! 追踪码: {res_json.get('tracking_code')}")
        iid = res_json.get("gitlab_issue_iid")
    else:
        print(f"❌ 缺陷提交失败: {resp.status_code}, {resp.text}")
        return

    # 5. 验证需求评审状态变更
    print(f"\n[Step 5] 验证需求评审状态变更 (Issue #{iid})...")
    review_url = f"{BASE_URL}/projects/{PROJECT_ID}/requirements/{iid}/review"
    review_params = {
        "review_state": "approved",
        "token": token
    }
    resp = requests.post(review_url, params=review_params)
    if resp.status_code == 200:
        print(f"✅ 评审状态变更成功! 身份已穿透映射。")
    else:
        print(f"❌ 评审状态变更失败: {resp.status_code}, {resp.text}")

if __name__ == "__main__":
    test_identity_mapping_flow()
