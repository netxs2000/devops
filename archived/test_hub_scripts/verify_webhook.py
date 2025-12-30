# -*- coding: utf-8 -*-
import requests
import json
import os
import sys

# Set output encoding to UTF-8 for console consistency
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_simulation():
    print("Starting Webhook simulation verification...")
    
    # 1. Pipeline failure payload
    project_id = 999
    payload = {
        "object_kind": "pipeline",
        "object_attributes": {
            "id": 12345,
            "ref": "main",
            "status": "failed",
            "sha": "a1b2c3d4e5f6g7h8",
            "finished_at": "2023-10-27 10:00:00"
        },
        "project": {
            "id": project_id,
            "name": "Demo Project"
        }
    }
    
    # 2. Simulate sending Webhook request
    url = "http://127.0.0.1:8000/webhook"
    headers = {
        "Content-Type": "application/json",
        "X-Gitlab-Event": "Pipeline Hook"
    }
    
    print(f"Sending Pipeline (Failed) Webhook to {url}...")
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"Webhook response status: {resp.status_code}")
        print(f"Response content: {resp.json()}")
        
        # 3. Verify the status interface
        status_url = f"http://127.0.0.1:8000/projects/{project_id}/pipeline-status"
        print(f"Checking dashboard status sync: {status_url}")
        status_resp = requests.get(status_url, timeout=5)
        result_data = status_resp.json()
        print(f"Sync result: {json.dumps(result_data, indent=2, ensure_ascii=False)}")
        
        if result_data.get("status") == "failed":
            print("\nVerification successful! The dashboard has real-time perceived the pipeline failure status.")
        else:
            print("\nVerification failed: Status not updated correctly.")
            
    except Exception as e:
        print(f"Simulation error: {e}")
        print("Note: Ensure devops_portal/main.py is running.")

if __name__ == "__main__":
    run_simulation()
