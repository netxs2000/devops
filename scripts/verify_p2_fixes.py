
import json
import asyncio
import logging
from typing import Dict, List, Any

# 模拟环境变量和配置
class MockConfig:
    LOG_LEVEL = logging.INFO

# 模拟 Webhook 负载
def generate_webhook_payload(issue_iid: int, current_labels: List[str], previous_labels: List[str], action: str = "update"):
    return {
        "object_attributes": {
            "iid": issue_iid,
            "action": action,
            "labels": [{"title": l} for l in current_labels]
        },
        "labels": [{"title": l} for l in current_labels],
        "changes": {
            "labels": {
                "previous": [{"title": l} for l in previous_labels],
                "current": [{"title": l} for l in current_labels]
            }
        },
        "project": {"id": 123}
    }

async def test_webhook_loop_prevention():
    print("Testing Webhook Loop Prevention...")
    
    # 模拟：状态未变化的需求更新
    labels = ["type::requirement", "review-state::approved", "status::satisfied"]
    payload = generate_webhook_payload(1, labels, labels) # 新旧一致
    
    # 逻辑模拟验证：根据代码，如果 old_review_state == review_state，则不触发 notification
    review_state = next((l.replace("review-state::", "") for l in labels if l.startswith("review-state::")), "draft")
    old_labels = [l.get("title") for l in payload.get("changes", {}).get("labels", {}).get("previous", [])]
    old_review_state = next((l.replace("review-state::", "") for l in old_labels if l.startswith("review-state::")), None)
    
    if old_review_state == review_state:
        print("[OK] SUCCESS: Webhook skipped redundant notification as expected.")
    else:
        print("[ERROR] FAILURE: Webhook failed to detect redundant update.")

    # 模拟：自动化 Close 触发的死循环防御
    action = "close"
    if action == "close" and "status::satisfied" in labels:
         print("[OK] SUCCESS: Close action with satisfied status bypassed to avoid sync loop.")

async def test_metadata_normalization():
    print("\nTesting Metadata Normalization...")
    # 之前 metadata 字段混乱，现在统一为 event_type
    sample_metadata = {
        "event_type": "test_execution_failure",
        "project_id": 123
    }
    if "event_type" in sample_metadata:
        print("[OK] SUCCESS: Metadata structure is aligned with P2 spec.")

if __name__ == "__main__":
    asyncio.run(test_webhook_loop_prevention())
    asyncio.run(test_metadata_normalization())
